import os
import json
import re
from google import genai
from dotenv import load_dotenv

# Load API Key from environment
load_dotenv()

class HealingAgent:
    """
    Agent 3: Healing Agent (Context-Aware)
    Responsibility: 
    1. Parse error logs to identify failing files.
    2. Read the CONTENT of those files (Critical for accurate fixes).
    3. Send Code + Error to Gemini.
    4. Apply fixes.
    """

    def __init__(self, repo_path, error_data):
        self.repo_path = repo_path
        self.error_data = error_data
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("HealingAgent initialized without GEMINI_API_KEY.")
            
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-3-flash-preview"

    def _identify_files_from_stderr(self, stderr):
        """
        Scans the error log for filenames to read their content.
        Supports:
        1. Custom 'Error in file.py:' format from AnalysisAgent.
        2. Standard Python Traceback 'File "file.py", line X'.
        """
        # Set of relative file paths
        detected_files = set()
        
        # Pattern 1: AnalysisAgent custom format
        custom_matches = re.findall(r"Error in (.*?):", stderr)
        detected_files.update([m.strip() for m in custom_matches])
        
        # Pattern 2: Standard Python Tracebacks
        traceback_matches = re.findall(r'File ["\'](.*?)["\']', stderr)
        # Filter out system paths, keep only repo paths
        for path in traceback_matches:
            # Simple heuristic: if it looks like a relative path or inside repo
            if not path.startswith("/") or self.repo_path in path:
                # normalize to relative
                rel = os.path.relpath(path, start=self.repo_path) if os.path.isabs(path) else path
                detected_files.add(rel)

        return list(detected_files)

    def _read_file_content(self, rel_path):
        """Reads the content of a file to pass to the AI."""
        full_path = os.path.join(self.repo_path, rel_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                return "[Error reading file]"
        return "[File not found]"

    def execute(self):
        """Main healing workflow."""
        print(f"--- [AGENT START]: HealingAgent ---")
        
        stderr = self.error_data.get("stderr", "")
        if not stderr:
            return {"status": "FAILED", "error": "No error logs to analyze"}
        print("REC")
        # 1. Identify which files are broken
        failing_files = self._identify_files_from_stderr(stderr)
        
        if not failing_files:
            print("[WARN] Could not identify specific files from error log. Sending generic prompt.")
            # Fallback to generic if regex fails, but this is risky
        
        # 2. Build Context (File Name + Content)
        file_context_str = ""
        for f_path in failing_files:
            content = self._read_file_content(f_path)
            file_context_str += f"\n--- FILE: {f_path} ---\n{content}\n----------------\n"

        # 3. Construct Prompt with SOURCE CODE
        prompt = f"""
        You are an Autonomous DevOps Repair Agent. 
        
        THE SITUATION:
        The following files have errors. 
        
        SOURCE CODE (Do NOT hallucinate new files. Fix THESE files.):
        {file_context_str}

        ERROR LOGS:
        {stderr}

        TASK:
        Fix the errors in the provided source code.
        
        CRITICAL RULES:
        1. **PRESERVE INTEGRITY**: Do NOT rewrite the logic. Do NOT change variable names unless necessary.
        2. **STRICT JSON**: Return a valid JSON response.
        3. **FULL CODE**: The "fixed_code" field must contain the **COMPLETE** file content with fixes applied. No placeholders like `# ...`.
        4. **MULTIPLE FILES**: If multiple files are broken, return a LIST of fix objects.
        5. **BUG TYPE CLASSIFICATION** (Choose the MOST SPECIFIC type): 
           - IMPORT: Missing imports, incorrect import statements, wrong module names
           - LINTING: Unused imports, unused variables, missing docstrings, formatting issues, style violations
           - INDENTATION: Indentation errors, mixing tabs/spaces, incorrect nesting
           - SYNTAX: Missing colons, brackets, quotes, parentheses, invalid syntax structure
           - LOGIC: Wrong operators, incorrect conditions, missing return statements, algorithm errors
           - TYPE_ERROR: Type mismatches, wrong argument types, casting errors, attribute errors
        6. **EXACT LINE NUMBERS**: Identify the exact line number where the error occurs.
        7. **DESCRIPTIVE FIX**: The "explanation" should describe what was wrong and how it was fixed.
        
        Return JSON structure:
        {{
            "file_path": "src/utils.py",
            "explanation": "Unused import 'os' on line 15 - removed the import statement",
            "fixed_code": "import pytest\\n...",
            "bug_type": "LINTING",
            "line_number": 15,
            "commit_message": "LINTING error in src/utils.py line 15 → Fix: remove the import statement",
            "status": "Fixed"
        }}
        
        IMPORTANT: The commit_message format MUST be:
        "[BUG_TYPE] error in [file_path] line [line_number] → Fix: [brief description of fix]"
        
        Bug types must be EXACTLY one of: IMPORT, LINTING, INDENTATION, SYNTAX, LOGIC, TYPE_ERROR
        Status should be "Fixed" for successfully applied fixes.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            fix_data = json.loads(raw_text)
            
            fixes_to_apply = fix_data if isinstance(fix_data, list) else [fix_data]
            successful_fixes = []
            
            for fix in fixes_to_apply:
                # Validate and standardize the fix format
                fix = self._validate_fix_format(fix)
                if self._apply_fix(fix):
                    successful_fixes.append(fix)

            if not successful_fixes:
                return {"status": "FAILED", "error": "No fixes could be applied"}

            print(f"--- [AGENT COMPLETED] ---")
            return {
                "status": "SUCCESS",
                "applied_fixes": successful_fixes
            }

        except Exception as e:
            user_message = self._format_gemini_error(str(e))
            print(f"[ERROR] Gemini Healing failed: {user_message}")
            return {"status": "FAILED", "error": user_message}
        
    def _format_gemini_error(self, error_text: str) -> str:
        """Map Gemini API errors to user-friendly messages."""
        text_upper = error_text.upper()
        text_lower = error_text.lower()

        # High demand / temporary outage
        if "503" in text_upper or "UNAVAILABLE" in text_upper or "high demand" in text_lower:
            return (
                "Gemini is experiencing high demand (503 UNAVAILABLE). "
                "Please retry after a short wait."
            )

        if (
                    "429" in text_upper
                    or "RESOURCE_EXHAUSTED" in text_upper
                    or "quota" in text_lower
                    or "rate limit" in text_lower
                    or "exhaust" in text_lower
                ):
                    return (
                        "Gemini API quota exhausted or rate limited. "
                        "Check your API key quota/billing or wait before retrying."
            )

        return error_text
    
    def _validate_fix_format(self, fix):
        """
        Validates and standardizes the fix format to match judge expectations.
        Ensures the commit message follows the exact format:
        "[BUG_TYPE] error in [file_path] line [line_number] → Fix: [description]"
        """
        # Ensure required fields exist
        if "bug_type" not in fix:
            fix["bug_type"] = "SYNTAX"  # Default
        if "line_number" not in fix:
            fix["line_number"] = None
        if "status" not in fix:
            fix["status"] = "Fixed"
        
        # Validate bug_type is one of the allowed values
        allowed_types = ["IMPORT", "LINTING", "INDENTATION", "SYNTAX", "LOGIC", "TYPE_ERROR"]
        if fix["bug_type"] not in allowed_types:
            # Try to map common variations - check most specific first
            bug_type_upper = fix["bug_type"].upper()
            explanation = fix.get("explanation", "").lower()
            
            # Check for IMPORT errors (most specific)
            if "IMPORT" in bug_type_upper or "import" in explanation or "module" in explanation or "ModuleNotFoundError" in bug_type_upper:
                fix["bug_type"] = "IMPORT"
            # Check for INDENTATION errors
            elif "INDENT" in bug_type_upper or "indentation" in explanation or "IndentationError" in bug_type_upper:
                fix["bug_type"] = "INDENTATION"
            # Check for TYPE errors
            elif "TYPE" in bug_type_upper or "TypeError" in bug_type_upper or "AttributeError" in bug_type_upper:
                fix["bug_type"] = "TYPE_ERROR"
            # Check for LINTING (unused imports/variables)
            elif "LINT" in bug_type_upper or "unused" in explanation or "UNUSED" in bug_type_upper:
                fix["bug_type"] = "LINTING"
            # Check for LOGIC errors
            elif "LOGIC" in bug_type_upper or "operator" in explanation or "condition" in explanation:
                fix["bug_type"] = "LOGIC"
            # Check for SYNTAX errors
            elif "SYNTAX" in bug_type_upper or "COLON" in bug_type_upper or "BRACKET" in bug_type_upper or "SyntaxError" in bug_type_upper:
                fix["bug_type"] = "SYNTAX"
            else:
                fix["bug_type"] = "SYNTAX"  # Default fallback
        
        # Generate standardized commit message if missing or incorrect format
        if "commit_message" not in fix or "→" not in fix.get("commit_message", ""):
            file_path = fix.get("file_path", "unknown file")
            bug_type = fix["bug_type"]
            line_num = fix.get("line_number", "?")
            explanation = fix.get("explanation", "applied fix")
            
            # Extract brief fix description from explanation
            fix_desc = explanation
            if "Fix:" in explanation:
                fix_desc = explanation.split("Fix:")[-1].strip()
            elif "fix" in explanation.lower():
                # Extract the part after "fix"
                parts = explanation.lower().split("fix")
                if len(parts) > 1:
                    fix_desc = parts[-1].strip()
            
            # Standardize the commit message format
            fix["commit_message"] = f"{bug_type} error in {file_path} line {line_num} → Fix: {fix_desc}"
        
        return fix

    def _apply_fix(self, fix_details):
        if "file_path" not in fix_details or "fixed_code" not in fix_details:
            return False

        file_path = os.path.join(self.repo_path, fix_details["file_path"])
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fix_details["fixed_code"])
            
            # Log in the expected format
            bug_type = fix_details.get('bug_type', 'SYNTAX')
            file_rel = fix_details.get('file_path', 'unknown')
            line_num = fix_details.get('line_number', '?')
            commit_msg = fix_details.get('commit_message', f'{bug_type} error in {file_rel} line {line_num}')
            
            print(f"[LOG] ✓ {commit_msg}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to write fix to {file_path}: {e}")
            return False