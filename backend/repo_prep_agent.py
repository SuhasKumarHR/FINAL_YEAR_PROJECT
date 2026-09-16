import os
import shutil
import subprocess
import re
from pathlib import Path

from git import Repo
from language_detector import detect_project_language


class RepoPrepAgent:
    """
    Agent 1: Repository Preparation Agent

    Responsibilities:
    1. Clone the repository into a temporary directory.
    2. Detect the project environment.
    3. Support Python, JavaScript, TypeScript and Java.
    4. Install dependencies if configuration files exist.
    5. Generate the mandatory branch name.
    """

    def __init__(self, repo_url, team_name, leader_name):
        self.repo_url = repo_url

        # Sanitize names
        self.team_name = self._sanitize_name(team_name)
        self.leader_name = self._sanitize_name(leader_name)

        self.target_dir = os.path.join(os.getcwd(), "temp")

    # ---------------------------------------------------------
    # NAME SANITIZATION
    # ---------------------------------------------------------

    def _sanitize_name(self, name):
        """
        Sanitize name according to naming rules:

        1. Convert to UPPERCASE
        2. Replace spaces with underscores
        3. Remove special characters
        4. Remove multiple consecutive underscores
        5. Remove leading/trailing underscores
        """

        name = name.upper()

        # Replace spaces with underscores
        name = name.replace(" ", "_")

        # Remove special characters
        name = re.sub(r"[^A-Z0-9_]", "", name)

        # Remove multiple underscores
        name = re.sub(r"_+", "_", name)

        # Remove leading/trailing underscores
        name = name.strip("_")

        return name

    # ---------------------------------------------------------
    # MAIN EXECUTION
    # ---------------------------------------------------------

    def execute(self):

        print("\n--- [AGENT START]: RepoPrepAgent ---")

        # Clone repository
        if not self._clone_repo():
            return {
                "status": "FAILED",
                "error": "Cloning failed"
            }

        # Detect and prepare environment
        env_info = self._setup_environment()

        # Branch naming convention
        branch_name = (
            f"{self.team_name}_{self.leader_name}_AI_Fix"
        )

        print(
            f"[LOG] Generated branch name: {branch_name}"
        )

        print(
            f"[SUCCESS] Environment detected: {env_info}"
        )

        print(
            "--- [AGENT COMPLETED] ---\n"
        )

        return {
            "status": "SUCCESS",
            "repo_path": self.target_dir,
            "environment": env_info,
            "branch_name": branch_name
        }

    # ---------------------------------------------------------
    # CLONE REPOSITORY
    # ---------------------------------------------------------

    def _clone_repo(self):

        if os.path.exists(self.target_dir):

            print(
                f"[LOG] Cleaning existing directory: "
                f"{self.target_dir}"
            )

            try:
                shutil.rmtree(self.target_dir)
            except Exception as e:
                print(
                    f"[ERROR] Unable to clean directory: {str(e)}"
                )
                return False

        try:

            print(
                f"[LOG] Cloning {self.repo_url}..."
            )

            Repo.clone_from(
                self.repo_url,
                self.target_dir
            )

            print(
                "[SUCCESS] Repository cloned successfully."
            )

            return True

        except Exception as e:

            print(
                f"[ERROR] Clone failed: {str(e)}"
            )

            return False

    # ---------------------------------------------------------
    # CHECK TOOL
    # ---------------------------------------------------------

    def _is_tool_installed(self, name):

        return shutil.which(name) is not None

    # ---------------------------------------------------------
    # SETUP ENVIRONMENT
    # ---------------------------------------------------------

    def _setup_environment(self):
        """
        Detect the project language and install dependencies.

        Supported:
        - Python
        - JavaScript
        - TypeScript
        - Java
        """

        repo_path = Path(self.target_dir)

        files = set(
            os.listdir(self.target_dir)
        )

        # -----------------------------------------------------
        # USE CENTRAL LANGUAGE DETECTOR
        # -----------------------------------------------------

        detected_language = detect_project_language(
            self.target_dir
        )

        print(
            f"[LOG] Language detector result: "
            f"{detected_language}"
        )

        # =====================================================
        # 1. JAVA PROJECT
        # =====================================================

        if detected_language == "java":

            # -------------------------------------------------
            # Maven
            # -------------------------------------------------

            if "pom.xml" in files:

                print(
                    "[LOG] Detected Java Maven project."
                )

                if self._is_tool_installed("mvn"):

                    print(
                        "[LOG] Maven is installed."
                    )

                    return "java (maven)"

                else:

                    print(
                        "[WARN] Maven is not installed."
                    )

                    return "java (maven - tool missing)"

            # -------------------------------------------------
            # Gradle
            # -------------------------------------------------

            elif (
                "build.gradle" in files
                or "build.gradle.kts" in files
            ):

                print(
                    "[LOG] Detected Java Gradle project."
                )

                if (
                    self._is_tool_installed("gradle")
                    or (repo_path / "gradlew").exists()
                ):

                    print(
                        "[LOG] Gradle is available."
                    )

                    return "java (gradle)"

                else:

                    print(
                        "[WARN] Gradle is not installed."
                    )

                    return "java (gradle - tool missing)"

            # -------------------------------------------------
            # Simple Java project
            # -------------------------------------------------

            else:

                java_files = list(
                    repo_path.rglob("*.java")
                )

                print(
                    f"[LOG] Detected simple Java project."
                )

                print(
                    f"[LOG] Java files found: "
                    f"{len(java_files)}"
                )

                if self._is_tool_installed("javac"):

                    print(
                        "[LOG] Java compiler (javac) is installed."
                    )

                    return "java"

                else:

                    print(
                        "[WARN] javac is not installed."
                    )

                    return "java (compiler missing)"

        # =====================================================
        # 2. PYTHON PROJECT
        # =====================================================

        if detected_language == "python":

            # Formal Python project
            if "requirements.txt" in files:

                print(
                    "[LOG] Detected Python "
                    "(requirements.txt)."
                )

                print(
                    "[LOG] Installing Python dependencies..."
                )

                try:

                    subprocess.run(
                        [
                            "pip",
                            "install",
                            "-r",
                            "requirements.txt"
                        ],
                        cwd=self.target_dir,
                        check=True
                    )

                    print(
                        "[SUCCESS] Python dependencies installed."
                    )

                    return "python"

                except subprocess.CalledProcessError:

                    print(
                        "[ERROR] Python dependency installation failed."
                    )

                    return "python (failed install)"

            # Simple Python project
            else:

                python_files = list(
                    repo_path.rglob("*.py")
                )

                if python_files:

                    print(
                        "[LOG] Detected Simple Python Project."
                    )

                    print(
                        f"[LOG] Python files found: "
                        f"{len(python_files)}"
                    )

                    return "python_simple"

        # =====================================================
        # 3. JAVASCRIPT / TYPESCRIPT PROJECT
        # =====================================================

        if (
            detected_language == "javascript"
            or detected_language == "typescript"
        ):

            # Formal Node project
            if "package.json" in files:

                if detected_language == "typescript":

                    print(
                        "[LOG] Detected TypeScript "
                        "(package.json)."
                    )

                else:

                    print(
                        "[LOG] Detected JavaScript "
                        "(package.json)."
                    )

                # -------------------------------------------------
                # Bun
                # -------------------------------------------------

                if self._is_tool_installed("bun"):

                    print(
                        "[LOG] Bun detected."
                    )

                    print(
                        "[LOG] Running 'bun install'..."
                    )

                    subprocess.run(
                        ["bun", "install"],
                        cwd=self.target_dir,
                        check=False
                    )

                    if detected_language == "typescript":

                        return "typescript (bun)"

                    return "javascript (bun)"

                # -------------------------------------------------
                # npm
                # -------------------------------------------------

                else:

                    print(
                        "[LOG] npm detected."
                    )

                    print(
                        "[LOG] Running 'npm install'..."
                    )

                    subprocess.run(
                        ["npm", "install"],
                        cwd=self.target_dir,
                        check=False
                    )

                    if detected_language == "typescript":

                        return "typescript (npm)"

                    return "javascript (npm)"

            # -----------------------------------------------------
            # Simple JS/TS project
            # -----------------------------------------------------

            else:

                if detected_language == "typescript":

                    print(
                        "[LOG] Detected Simple TypeScript Project."
                    )

                    return "typescript_simple"

                else:

                    print(
                        "[LOG] Detected Simple JavaScript Project."
                    )

                    return "javascript_simple"

        # =====================================================
        # 4. UNKNOWN PROJECT
        # =====================================================

        print(
            "[WARN] No recognized code files found."
        )

        return "unknown"