import os
import glob
import shutil
import subprocess


class AnalysisAgent:
    """
    Analyzes a repository based on the detected environment.

    Supported environments:
    - python
    - python_simple
    - javascript (npm/bun)
    - javascript_simple
    - typescript (npm/bun)
    - typescript_simple
    - java
    - java (maven)
    - java (gradle)
    """

    def __init__(self, repo_path: str, environment: str):
        self.repo_path = repo_path
        self.environment = environment

    # ============================================================
    # MAIN EXECUTION
    # ============================================================

    def execute(self):
        print("--- [AGENT START]: AnalysisAgent ---")
        print(f"[LOG] Repository: {self.repo_path}")
        print(f"[LOG] Analyzing environment: {self.environment}")

        try:
            # JavaScript / TypeScript projects using package manager
            if (
                ("javascript" in self.environment or "typescript" in self.environment)
                and "simple" not in self.environment
            ):
                result = self._check_js_build()

            # Python project with requirements / pyproject
            elif self.environment == "python":
                result = self._check_python_compilation()

            # Java Maven / Gradle projects
            elif self.environment in ("java (maven)", "java (gradle)"):
                result = self._check_java_build()

            # Simple Python project
            elif self.environment == "python_simple":
                result = self._check_simple_python()

            # Simple JavaScript project
            elif self.environment == "javascript_simple":
                result = self._check_simple_js()

            # Simple TypeScript project
            elif self.environment == "typescript_simple":
                result = self._check_simple_ts()

            # Simple Java project
            elif self.environment == "java":
                result = self._check_simple_java()

            else:
                result = {
                    "status": "FAILED",
                    "error": f"Unknown or unsupported environment: {self.environment}",
                    "stderr": f"Unsupported environment: {self.environment}",
                    "stdout": "",
                }

        except Exception as e:
            result = {
                "status": "FAILED",
                "error": str(e),
                "stderr": str(e),
                "stdout": "",
            }

        print("--- [AGENT COMPLETED] ---")
        print(f"[LOG] Analysis status: {result.get('status')}")

        return result

    # ============================================================
    # COMMON COMMAND RUNNER
    # ============================================================

    def _run_command(self, command):
        """
        Run a command inside the repository directory.
        """

        print(f"[LOG] Running command: {' '.join(command)}")

        try:
            process = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                shell=False,
            )

            return {
                "returncode": process.returncode,
                "stdout": process.stdout or "",
                "stderr": process.stderr or "",
            }

        except FileNotFoundError as e:
            return {
                "returncode": 1,
                "stdout": "",
                "stderr": str(e),
            }

        except Exception as e:
            return {
                "returncode": 1,
                "stdout": "",
                "stderr": str(e),
            }

    # ============================================================
    # TOOL CHECK
    # ============================================================

    def _is_tool_installed(self, tool):
        """
        Check whether a command-line tool is available.
        """

        return shutil.which(tool) is not None

    # ============================================================
    # PYTHON - FORMAL PROJECT
    # ============================================================

    def _check_python_compilation(self):
        """
        Compile Python files using Python's compileall module.
        """

        print("[LOG] Checking Python project compilation...")

        result = self._run_command(
            ["python", "-m", "compileall", "."]
        )

        if result["returncode"] == 0:
            return {
                "status": "PASSED",
                "message": "Python compilation successful.",
                "stdout": result["stdout"],
                "stderr": result["stderr"],
            }

        return {
            "status": "FAILED",
            "error": "Python compilation failed.",
            "stdout": result["stdout"],
            "stderr": result["stderr"] or result["stdout"],
        }

    # ============================================================
    # PYTHON - SIMPLE PROJECT
    # ============================================================

    def _check_simple_python(self):
        """
        Check Python files individually.

        This is useful for repositories without requirements.txt
        or a formal Python project structure.
        """

        print("[LOG] Checking simple Python project...")

        python_files = glob.glob(
            os.path.join(self.repo_path, "**", "*.py"),
            recursive=True,
        )

        python_files = [
            file_path
            for file_path in python_files
            if not self._is_ignored_path(file_path)
        ]

        if not python_files:
            return {
                "status": "FAILED",
                "error": "No Python files found.",
                "stdout": "",
                "stderr": "No Python files found in repository.",
            }

        errors = []

        for file_path in python_files:
            relative_path = os.path.relpath(
                file_path,
                self.repo_path,
            )

            print(f"[LOG] Checking Python file: {relative_path}")

            result = self._run_command(
                [
                    "python",
                    "-m",
                    "py_compile",
                    relative_path,
                ]
            )

            if result["returncode"] != 0:
                error_output = (
                    result["stderr"]
                    or result["stdout"]
                    or "Python compilation error."
                )

                errors.append(
                    f"Error in {relative_path}:\n{error_output}"
                )

        if errors:
            combined_error = "\n\n".join(errors)

            return {
                "status": "FAILED",
                "error": "Python syntax/compilation errors detected.",
                "stdout": "",
                "stderr": combined_error,
            }

        return {
            "status": "PASSED",
            "message": "All Python files passed syntax checks.",
            "stdout": "",
            "stderr": "",
        }

    # ============================================================
    # JAVASCRIPT / TYPESCRIPT - NPM/BUN PROJECT
    # ============================================================

    def _check_js_build(self):
        """
        Run the project's build command.

        Uses Bun when the environment indicates Bun.
        Otherwise uses npm.
        """

        print("[LOG] Checking JavaScript/TypeScript build...")

        use_bun = "bun" in self.environment

        if use_bun and self._is_tool_installed("bun"):
            command = ["bun", "run", "build"]
        else:
            command = ["npm", "run", "build"]

        result = self._run_command(command)

        combined_output = (
            result["stdout"]
            + "\n"
            + result["stderr"]
        ).strip()

        if result["returncode"] == 0:
            return {
                "status": "PASSED",
                "message": "JavaScript/TypeScript build successful.",
                "stdout": result["stdout"],
                "stderr": result["stderr"],
            }

        return {
            "status": "FAILED",
            "error": "JavaScript/TypeScript build failed.",
            "stdout": result["stdout"],
            "stderr": result["stderr"] or result["stdout"],
            "output": combined_output,
        }

    # ============================================================
    # JAVASCRIPT - SIMPLE PROJECT
    # ============================================================

    def _check_simple_js(self):
        """
        Check JavaScript and JSX files using Node.js syntax checking.
        """

        print("[LOG] Checking simple JavaScript project...")

        if not self._is_tool_installed("node"):
            return {
                "status": "FAILED",
                "error": "Node.js is not installed.",
                "stdout": "",
                "stderr": "Node.js is required for JavaScript analysis.",
            }

        js_files = []

        js_files.extend(
            glob.glob(
                os.path.join(self.repo_path, "**", "*.js"),
                recursive=True,
            )
        )

        js_files.extend(
            glob.glob(
                os.path.join(self.repo_path, "**", "*.jsx"),
                recursive=True,
            )
        )

        js_files = [
            file_path
            for file_path in js_files
            if not self._is_ignored_path(file_path)
        ]

        if not js_files:
            return {
                "status": "FAILED",
                "error": "No JavaScript files found.",
                "stdout": "",
                "stderr": "No .js or .jsx files found.",
            }

        errors = []

        for file_path in js_files:
            relative_path = os.path.relpath(
                file_path,
                self.repo_path,
            )

            print(f"[LOG] Checking JavaScript file: {relative_path}")

            result = self._run_command(
                [
                    "node",
                    "--check",
                    relative_path,
                ]
            )

            if result["returncode"] != 0:
                error_output = (
                    result["stderr"]
                    or result["stdout"]
                    or "JavaScript syntax error."
                )

                errors.append(
                    f"Error in {relative_path}:\n{error_output}"
                )

        if errors:
            return {
                "status": "FAILED",
                "error": "JavaScript syntax errors detected.",
                "stdout": "",
                "stderr": "\n\n".join(errors),
            }

        return {
            "status": "PASSED",
            "message": "All JavaScript files passed syntax checks.",
            "stdout": "",
            "stderr": "",
        }

    # ============================================================
    # TYPESCRIPT - SIMPLE PROJECT
    # ============================================================

    def _check_simple_ts(self):
        """
        Check TypeScript and TSX files.

        Uses tsc --noEmit so source files are checked without
        generating JavaScript output.
        """

        print("[LOG] Checking simple TypeScript project...")

        if not self._is_tool_installed("tsc"):
            return {
                "status": "FAILED",
                "error": "TypeScript compiler (tsc) is not installed.",
                "stdout": "",
                "stderr": (
                    "TypeScript compiler is required for simple "
                    "TypeScript projects."
                ),
            }

        ts_files = []

        ts_files.extend(
            glob.glob(
                os.path.join(self.repo_path, "**", "*.ts"),
                recursive=True,
            )
        )

        ts_files.extend(
            glob.glob(
                os.path.join(self.repo_path, "**", "*.tsx"),
                recursive=True,
            )
        )

        ts_files = [
            file_path
            for file_path in ts_files
            if not self._is_ignored_path(file_path)
            and not file_path.endswith(".d.ts")
        ]

        if not ts_files:
            return {
                "status": "FAILED",
                "error": "No TypeScript files found.",
                "stdout": "",
                "stderr": "No .ts or .tsx files found.",
            }

        errors = []

        for file_path in ts_files:
            relative_path = os.path.relpath(
                file_path,
                self.repo_path,
            )

            print(f"[LOG] Checking TypeScript file: {relative_path}")

            result = self._run_command(
                [
                    "tsc",
                    "--noEmit",
                    "--skipLibCheck",
                    relative_path,
                ]
            )

            if result["returncode"] != 0:
                error_output = (
                    result["stderr"]
                    or result["stdout"]
                    or "TypeScript compilation error."
                )

                errors.append(
                    f"Error in {relative_path}:\n{error_output}"
                )

        if errors:
            return {
                "status": "FAILED",
                "error": "TypeScript compilation errors detected.",
                "stdout": "",
                "stderr": "\n\n".join(errors),
            }

        return {
            "status": "PASSED",
            "message": "All TypeScript files passed compilation checks.",
            "stdout": "",
            "stderr": "",
        }

    # ============================================================
    # JAVA - MAVEN / GRADLE
    # ============================================================

    def _check_java_build(self):
        """
        Check Java project using Maven or Gradle.

        If no build tool configuration is available,
        fall back to javac compilation.
        """

        print("[LOG] Checking Java project...")

        pom_file = os.path.join(
            self.repo_path,
            "pom.xml",
        )

        gradle_file = os.path.join(
            self.repo_path,
            "build.gradle",
        )

        gradle_kts_file = os.path.join(
            self.repo_path,
            "build.gradle.kts",
        )

        # --------------------------------------------------------
        # Maven
        # --------------------------------------------------------

        if os.path.exists(pom_file):
            print("[LOG] Maven project detected.")

            if not self._is_tool_installed("mvn"):
                return {
                    "status": "FAILED",
                    "error": "Maven is not installed.",
                    "stdout": "",
                    "stderr": "Maven (mvn) is required for this project.",
                }

            result = self._run_command(
                ["mvn", "test", "-B"]
            )

            if result["returncode"] == 0:
                return {
                    "status": "PASSED",
                    "message": "Maven build/test successful.",
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                }

            return {
                "status": "FAILED",
                "error": "Maven build/test failed.",
                "stdout": result["stdout"],
                "stderr": result["stderr"] or result["stdout"],
            }

        # --------------------------------------------------------
        # Gradle
        # --------------------------------------------------------

        if os.path.exists(gradle_file) or os.path.exists(gradle_kts_file):

            print("[LOG] Gradle project detected.")

            gradlew = os.path.join(
                self.repo_path,
                "gradlew",
            )

            gradlew_bat = os.path.join(
                self.repo_path,
                "gradlew.bat",
            )

            if os.path.exists(gradlew_bat):
                command = ["gradlew.bat", "build"]
            elif os.path.exists(gradlew):
                command = ["./gradlew", "build"]
            elif self._is_tool_installed("gradle"):
                command = ["gradle", "build"]
            else:
                return {
                    "status": "FAILED",
                    "error": "Gradle is not installed and Gradle wrapper was not found.",
                    "stdout": "",
                    "stderr": "Gradle build tool is unavailable.",
                }

            result = self._run_command(command)

            if result["returncode"] == 0:
                return {
                    "status": "PASSED",
                    "message": "Gradle build successful.",
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                }

            return {
                "status": "FAILED",
                "error": "Gradle build failed.",
                "stdout": result["stdout"],
                "stderr": result["stderr"] or result["stdout"],
            }

        # --------------------------------------------------------
        # Plain Java
        # --------------------------------------------------------

        return self._compile_java_files()

    # ============================================================
    # JAVA - SIMPLE PROJECT
    # ============================================================

    def _check_simple_java(self):
        """
        Compile simple Java repositories using javac.
        """

        print("[LOG] Checking simple Java project...")

        return self._compile_java_files()

    # ============================================================
    # JAVA COMPILATION
    # ============================================================

    def _compile_java_files(self):
        """
        Compile all Java source files using javac.
        """

        print("[LOG] Compiling Java files...")

        if not self._is_tool_installed("javac"):
            return {
                "status": "FAILED",
                "error": "Java compiler (javac) is not installed.",
                "stdout": "",
                "stderr": "JDK is required for Java compilation.",
            }

        java_files = glob.glob(
            os.path.join(self.repo_path, "**", "*.java"),
            recursive=True,
        )

        java_files = [
            file_path
            for file_path in java_files
            if not self._is_ignored_path(file_path)
        ]

        if not java_files:
            return {
                "status": "FAILED",
                "error": "No Java files found.",
                "stdout": "",
                "stderr": "No .java files found.",
            }

        build_dir = os.path.join(
            self.repo_path,
            ".java_build",
        )

        os.makedirs(
            build_dir,
            exist_ok=True,
        )

        relative_java_files = [
            os.path.relpath(
                file_path,
                self.repo_path,
            )
            for file_path in java_files
        ]

        command = [
            "javac",
            "-d",
            ".java_build",
        ] + relative_java_files

        result = self._run_command(command)

        # Clean temporary Java compilation directory
        try:
            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)
        except Exception:
            pass

        if result["returncode"] == 0:
            return {
                "status": "PASSED",
                "message": "Java compilation successful.",
                "stdout": result["stdout"],
                "stderr": result["stderr"],
            }

        return {
            "status": "FAILED",
            "error": "Java compilation failed.",
            "stdout": result["stdout"],
            "stderr": result["stderr"] or result["stdout"],
        }

    # ============================================================
    # IGNORE UNNECESSARY DIRECTORIES
    # ============================================================

    def _is_ignored_path(self, file_path):
        """
        Prevent analysis of generated/dependency directories.
        """

        normalized = os.path.normpath(file_path)

        ignored_directories = {
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "env",
            ".env",
            "target",
            "build",
            "dist",
            ".java_build",
            ".next",
            ".gradle",
        }

        parts = normalized.split(os.sep)

        return any(
            directory in parts
            for directory in ignored_directories
        )