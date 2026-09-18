import os
import json
import re
import time
from pathlib import Path

from google import genai
from dotenv import load_dotenv


load_dotenv()


class HealingAgent:

    def __init__(self, repo_path, analysis_result):
        self.repo_path = repo_path
        self.analysis_result = analysis_result

        self.api_key = os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is missing."
            )

        self.client = genai.Client(
            api_key=self.api_key
        )

        self.model_id = "gemini-3-flash-preview"

    # =========================================================
    # MAIN EXECUTION
    # =========================================================

    def execute(
        self,
        failure_category="UNKNOWN",
        failure_confidence=0.0
    ):
        print(
            "--- [AGENT START]: HealingAgent ---"
        )

        try:

            # -------------------------------------------------
            # GET ANALYSIS OUTPUT
            # -------------------------------------------------

            stdout = self.analysis_result.get(
                "stdout",
                ""
            )

            stderr = self.analysis_result.get(
                "stderr",
                ""
            )

            error_value = self.analysis_result.get(
                "error",
                ""
            )

            error_text = (
                str(stdout)
                + "\n"
                + str(stderr)
                + "\n"
                + str(error_value)
            )

            if not error_text.strip():
                error_text = str(
                    self.analysis_result
                )

            print(
                "[INFO] Error logs received."
            )

            # -------------------------------------------------
            # KNN CLASSIFICATION INFORMATION
            # -------------------------------------------------

            print(
                f"[KNN] Failure Category: "
                f"{failure_category}"
            )

            print(
                f"[KNN] Confidence: "
                f"{failure_confidence}"
            )

            # -------------------------------------------------
            # FIND FAILING FILES
            # -------------------------------------------------

            failing_files = (
                self._identify_files_from_stderr(
                    error_text
                )
            )

            print(
                f"[INFO] Detected failing files: "
                f"{failing_files}"
            )

            # -------------------------------------------------
            # BUILD SOURCE CONTEXT
            # -------------------------------------------------

            file_context = []

            for file_path in failing_files:

                source_code = (
                    self._read_file_content(
                        file_path
                    )
                )

                if source_code is not None:

                    # Prevent extremely large prompts
                    if len(source_code) > 20000:

                        source_code = (
                            source_code[:20000]
                            + "\n\n[FILE TRUNCATED]"
                        )

                    file_context.append(
                        f"""
==================================================
FILE: {file_path}
==================================================

{source_code}
"""
                    )

            # -------------------------------------------------
            # IF NO FILE WAS IDENTIFIED
            # -------------------------------------------------

            if not file_context:

                print(
                    "[WARN] No source files could "
                    "be identified from the error."
                )

                return {
                    "status": "FAILED",
                    "error": (
                        "Could not identify the "
                        "source file responsible "
                        "for the error."
                    )
                }

            source_context = "\n".join(
                file_context
            )

            # -------------------------------------------------
            # GEMINI PROMPT
            # -------------------------------------------------

            prompt = f"""
You are an expert autonomous software debugging agent.

Your task is to analyze a build, compilation, syntax,
dependency, or runtime error and generate the minimum
safe source-code fix required to resolve the problem.

IMPORTANT RULES:

1. Analyze the error logs carefully.

2. Analyze the provided source code.

3. Identify the actual root cause.

4. Modify only the necessary source code.

5. Do not rewrite the entire project.

6. Do not invent files that were not provided.

7. Do not change project architecture unnecessarily.

8. Preserve existing functionality.

9. Return COMPLETE corrected source code for each file.

10. Return ONLY valid JSON.

11. Do not use Markdown code fences.

12. The file_path must be relative to the repository root.

13. Do not modify configuration files unless the error
    clearly requires a source-code change.

14. Do not make unrelated improvements.

15. Do not remove existing functionality just to make
    the validation pass.

SUPPORTED BUG TYPES:

- IMPORT
- LINTING
- INDENTATION
- SYNTAX
- LOGIC
- TYPE_ERROR
- COMPILATION
- DEPENDENCY
- BUILD
- TEST

==================================================
KNN FAILURE CLASSIFICATION
==================================================

Failure Category:
{failure_category}

KNN Confidence:
{failure_confidence}

The KNN classification is supporting information only.

Verify the classification against the actual error logs,
source code, and build output before generating the fix.

Do not blindly trust the KNN classification.

==================================================
ERROR LOGS
==================================================

{error_text}

==================================================
SOURCE FILES
==================================================

{source_context}

==================================================
REQUIRED JSON FORMAT
==================================================

Return either a JSON object or JSON array.

Example:

[
    {{
        "file_path": "src/example.py",
        "bug_type": "SYNTAX",
        "description": "Description of the problem",
        "fixed_code": "complete corrected source code",
        "commit_message": "fix: correct syntax error"
    }}
]

The fixed_code field MUST contain the COMPLETE corrected
source code of the file.

Do not return partial code.

Do not include Markdown.

Do not include explanations outside JSON.

==================================================
FINAL INSTRUCTION
==================================================

First determine the actual root cause using the error logs
and source code.

Use the KNN failure category as supporting information.

Generate only the minimum required repair.

Return valid JSON only.
"""

            print(
                "[INFO] Sending source code, error logs, "
                "and KNN classification to Gemini..."
            )

            # -------------------------------------------------
            # GEMINI REQUEST
            # -------------------------------------------------

            response = self._generate_gemini_response(
                prompt
            )

            # -------------------------------------------------
            # CHECK RESPONSE
            # -------------------------------------------------

            if not response:

                return {
                    "status": "FAILED",
                    "error": (
                        "Gemini returned no response."
                    )
                }

            if not hasattr(response, "text"):

                return {
                    "status": "FAILED",
                    "error": (
                        "Gemini response has no text."
                    )
                }

            if not response.text:

                return {
                    "status": "FAILED",
                    "error": (
                        "Gemini returned an empty response."
                    )
                }

            raw_response = response.text.strip()

            # -------------------------------------------------
            # REMOVE MARKDOWN FENCES
            # -------------------------------------------------

            if raw_response.startswith(
                "```json"
            ):
                raw_response = raw_response[7:]

            elif raw_response.startswith(
                "```"
            ):
                raw_response = raw_response[3:]

            if raw_response.endswith(
                "```"
            ):
                raw_response = raw_response[:-3]

            raw_response = raw_response.strip()

            # -------------------------------------------------
            # PARSE JSON
            # -------------------------------------------------

            try:

                fix_details = json.loads(
                    raw_response
                )

            except json.JSONDecodeError as e:

                print(
                    "[ERROR] Gemini returned "
                    "invalid JSON."
                )

                print(
                    f"[ERROR] JSON error: {e}"
                )

                print(
                    "[DEBUG] Gemini response:"
                )

                print(
                    raw_response
                )

                return {
                    "status": "FAILED",
                    "error": (
                        "Gemini returned invalid JSON."
                    )
                }

            # -------------------------------------------------
            # NORMALIZE RESPONSE
            # -------------------------------------------------

            if isinstance(
                fix_details,
                dict
            ):

                fixes = [
                    fix_details
                ]

            elif isinstance(
                fix_details,
                list
            ):

                fixes = fix_details

            else:

                return {
                    "status": "FAILED",
                    "error": (
                        "Invalid Gemini response "
                        "format."
                    )
                }

            # -------------------------------------------------
            # APPLY FIXES
            # -------------------------------------------------

            applied_fixes = []

            for fix in fixes:

                if not isinstance(
                    fix,
                    dict
                ):

                    print(
                        "[WARN] Gemini returned "
                        "an invalid fix object."
                    )

                    continue

                if not self._validate_fix_format(
                    fix
                ):

                    print(
                        "[WARN] Invalid fix format. "
                        "Skipping."
                    )

                    continue

                success = self._apply_fix(
                    fix
                )

                if success:

                    applied_fixes.append(
                        fix
                    )

            # -------------------------------------------------
            # FINAL RESULT
            # -------------------------------------------------

            if not applied_fixes:

                return {
                    "status": "FAILED",
                    "error": (
                        "Gemini generated no "
                        "valid applicable fixes."
                    )
                }

            print(
                f"[SUCCESS] Applied "
                f"{len(applied_fixes)} fix(es)."
            )

            print(
                "--- [AGENT COMPLETED]: "
                "HealingAgent ---"
            )

            return {
                "status": "SUCCESS",
                "fixes": applied_fixes,
                "fixes_count": len(
                    applied_fixes
                ),
                "failure_category": failure_category,
                "failure_confidence": failure_confidence
            }

        except Exception as e:

            error_message = (
                self._format_gemini_error(
                    str(e)
                )
            )

            print(
                f"[ERROR] Gemini Healing failed: "
                f"{error_message}"
            )

            return {
                "status": "FAILED",
                "error": error_message
            }

    # =========================================================
    # GEMINI API WITH RETRY
    # =========================================================

    def _generate_gemini_response(
        self,
        prompt
    ):

        max_attempts = 3

        for attempt in range(
            1,
            max_attempts + 1
        ):

            print(
                f"[INFO] Gemini API attempt "
                f"{attempt}/{max_attempts}..."
            )

            try:

                # IMPORTANT:
                # This calls Gemini API directly.
                # It MUST NOT call this function again.

                response = (
                    self.client.models.generate_content(
                        model=self.model_id,
                        contents=prompt,
                        config={
                            "response_mime_type":
                                "application/json"
                        }
                    )
                )

                print(
                    f"[SUCCESS] Gemini API response "
                    f"received on attempt {attempt}."
                )

                return response

            except Exception as e:

                error_message = str(e)

                print(
                    f"[WARN] Gemini API attempt "
                    f"{attempt} failed: "
                    f"{error_message}"
                )

                if attempt < max_attempts:

                    wait_time = attempt * 2

                    print(
                        f"[INFO] Retrying Gemini API "
                        f"in {wait_time} seconds..."
                    )

                    time.sleep(
                        wait_time
                    )

                else:

                    raise

    # =========================================================
    # IDENTIFY FAILING FILES
    # =========================================================

    def _identify_files_from_stderr(
        self,
        stderr
    ):

        files = []

        if not stderr:
            return files

        text = str(stderr)

        # -----------------------------------------------------
        # Python traceback
        # Example:
        # File "src/main.py", line 10
        # -----------------------------------------------------

        python_matches = re.findall(
            r'File\s+["\']([^"\']+)["\']',
            text
        )

        files.extend(
            python_matches
        )

        # -----------------------------------------------------
        # Custom error format
        # Example:
        # Error in src/main.py:
        # -----------------------------------------------------

        custom_matches = re.findall(
            r"Error in\s+(.+?):",
            text
        )

        files.extend(
            custom_matches
        )

        # -----------------------------------------------------
        # Java compiler
        # Example:
        # Main.java:12: error:
        # -----------------------------------------------------

        java_matches = re.findall(
            r'([A-Za-z0-9_./\\-]+\.java):\d+(?::\d+)?',
            text
        )

        files.extend(
            java_matches
        )

        # -----------------------------------------------------
        # Maven Java
        # Example:
        # /src/Main.java:[12,5]
        # -----------------------------------------------------

        maven_matches = re.findall(
            r'([A-Za-z0-9_./\\-]+\.java):\[\d+,\d+\]',
            text
        )

        files.extend(
            maven_matches
        )

        # -----------------------------------------------------
        # JavaScript / TypeScript
        # Examples:
        # frontend/app/page.tsx:10:5
        # src/index.js:12:4
        # -----------------------------------------------------

        js_ts_matches = re.findall(
            r'([A-Za-z0-9_./\\-]+\.(?:js|jsx|ts|tsx)):\d+(?::\d+)?',
            text
        )

        files.extend(
            js_ts_matches
        )

        # -----------------------------------------------------
        # Remove duplicates
        # -----------------------------------------------------

        unique_files = []

        for file_path in files:

            file_path = str(
                file_path
            ).strip()

            if not file_path:
                continue

            # Remove surrounding quotes
            file_path = (
                file_path
                .strip('"')
                .strip("'")
            )

            if file_path not in unique_files:

                unique_files.append(
                    file_path
                )

        return unique_files

    # =========================================================
    # READ SOURCE FILE
    # =========================================================

    def _read_file_content(
        self,
        file_path
    ):

        try:

            relative_path = (
                self._normalize_relative_path(
                    file_path
                )
            )

            if not relative_path:
                return None

            full_path = (
                Path(self.repo_path)
                / relative_path
            )

            repo_root = (
                Path(self.repo_path)
                .resolve()
            )

            full_path = (
                full_path
                .resolve()
            )

            # Security check:
            # Do not allow Gemini/error logs to
            # access files outside repository.

            try:

                full_path.relative_to(
                    repo_root
                )

            except ValueError:

                print(
                    f"[WARN] Ignoring unsafe "
                    f"file path: {file_path}"
                )

                return None

            if not full_path.exists():

                print(
                    f"[WARN] File not found: "
                    f"{relative_path}"
                )

                return None

            if not full_path.is_file():
                return None

            return full_path.read_text(
                encoding="utf-8",
                errors="ignore"
            )

        except Exception as e:

            print(
                f"[WARN] Could not read file "
                f"{file_path}: {e}"
            )

            return None

    # =========================================================
    # NORMALIZE FILE PATH
    # =========================================================

    def _normalize_relative_path(
        self,
        file_path
    ):

        if not file_path:
            return None

        path = str(
            file_path
        ).strip()

        path = (
            path
            .strip('"')
            .strip("'")
        )

        # Convert Windows separators
        path = path.replace(
            "\\",
            "/"
        )

        # Remove ./ prefix
        while path.startswith(
            "./"
        ):

            path = path[2:]

        # If absolute path points inside repo,
        # convert it to repository-relative path.

        try:

            candidate = Path(
                path
            )

            if candidate.is_absolute():

                repo_root = (
                    Path(self.repo_path)
                    .resolve()
                )

                candidate = (
                    candidate
                    .resolve()
                )

                try:

                    return candidate.relative_to(
                        repo_root
                    ).as_posix()

                except ValueError:

                    return None

        except Exception:
            pass

        return path

    # =========================================================
    # VALIDATE GEMINI FIX
    # =========================================================

    def _validate_fix_format(
        self,
        fix
    ):

        required_fields = [
            "file_path",
            "bug_type",
            "description",
            "fixed_code"
        ]

        for field in required_fields:

            if field not in fix:

                print(
                    f"[WARN] Missing field: "
                    f"{field}"
                )

                return False

        # commit_message is optional.
        # Generate a default value if Gemini
        # does not provide it.

        fix.setdefault(
            "commit_message",
            f"fix: {fix['bug_type']} in "
            f"{fix['file_path']}"
        )

        allowed_bug_types = {
            "IMPORT",
            "LINTING",
            "INDENTATION",
            "SYNTAX",
            "LOGIC",
            "TYPE_ERROR",
            "COMPILATION",
            "DEPENDENCY",
            "BUILD",
            "TEST"
        }

        bug_type = str(
            fix["bug_type"]
        ).upper()

        if bug_type not in allowed_bug_types:

            print(
                f"[WARN] Unsupported bug type: "
                f"{bug_type}"
            )

            return False

        if not isinstance(
            fix["fixed_code"],
            str
        ):

            print(
                "[WARN] fixed_code must "
                "be a string."
            )

            return False

        if not fix["fixed_code"].strip():

            print(
                "[WARN] fixed_code is empty."
            )

            return False

        if not str(
            fix["file_path"]
        ).strip():

            return False

        return True

    # =========================================================
    # APPLY GEMINI FIX
    # =========================================================

    def _apply_fix(
        self,
        fix_details
    ):

        try:

            relative_path = (
                self._normalize_relative_path(
                    fix_details["file_path"]
                )
            )

            if not relative_path:

                print(
                    "[ERROR] Invalid file path."
                )

                return False

            repo_root = (
                Path(self.repo_path)
                .resolve()
            )

            target_path = (
                repo_root
                / relative_path
            ).resolve()

            # -------------------------------------------------
            # SECURITY CHECK
            # -------------------------------------------------

            try:

                target_path.relative_to(
                    repo_root
                )

            except ValueError:

                print(
                    "[ERROR] Attempt to modify "
                    "file outside repository."
                )

                return False

            # -------------------------------------------------
            # FILE MUST ALREADY EXIST
            # -------------------------------------------------

            if not target_path.exists():

                print(
                    f"[ERROR] Cannot apply fix. "
                    f"File does not exist: "
                    f"{relative_path}"
                )

                return False

            if not target_path.is_file():
                return False

            # -------------------------------------------------
            # BACKUP ORIGINAL
            # -------------------------------------------------

            backup_path = (
                target_path.with_suffix(
                    target_path.suffix
                    + ".acr_backup"
                )
            )

            if not backup_path.exists():

                backup_path.write_text(
                    target_path.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    ),
                    encoding="utf-8"
                )

            # -------------------------------------------------
            # WRITE FIXED CODE
            # -------------------------------------------------

            target_path.write_text(
                fix_details["fixed_code"],
                encoding="utf-8"
            )

            print(
                f"[SUCCESS] Fix applied to: "
                f"{relative_path}"
            )

            return True

        except Exception as e:

            print(
                f"[ERROR] Failed to apply fix: "
                f"{e}"
            )

            return False

    # =========================================================
    # FORMAT GEMINI ERROR
    # =========================================================

    def _format_gemini_error(
        self,
        error_message
    ):

        message = str(
            error_message
        )

        if "503" in message:

            return (
                "Gemini service temporarily "
                "unavailable (503). "
                "Please retry."
            )

        if "429" in message:

            return (
                "Gemini API rate limit reached. "
                "Please retry later."
            )

        if "401" in message:

            return (
                "Gemini API authentication failed. "
                "Check GEMINI_API_KEY."
            )

        if "403" in message:

            return (
                "Gemini API access denied. "
                "Check API key permissions."
            )

        return message