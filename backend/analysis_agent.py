import subprocess
import shutil
from pathlib import Path


class AnalysisAgent:

    def __init__(self, repo_path, environment):
        self.repo_path = Path(repo_path)
        self.environment = environment

    # =========================================================
    # MAIN EXECUTION
    # =========================================================

    def execute(self):

        print("--- [AGENT START]: AnalysisAgent ---")

        print(
            f"[LOG] Analyzing environment: "
            f"{self.environment}"
        )

        # -----------------------------------------------------
        # FORMAL JAVASCRIPT / TYPESCRIPT PROJECT
        # -----------------------------------------------------

        if (
            (
                "javascript" in self.environment
                or "typescript" in self.environment
            )
            and "simple" not in self.environment
        ):

            result = self._check_js_build()

        # -----------------------------------------------------
        # FORMAL PYTHON PROJECT
        # -----------------------------------------------------

        elif self.environment == "python":

            result = (
                self._check_python_compilation()
            )

        # -----------------------------------------------------
        # JAVA MAVEN / GRADLE
        # -----------------------------------------------------

        elif self.environment in (
            "java (maven)",
            "java (gradle)"
        ):

            result = self._check_java_build()

        # -----------------------------------------------------
        # SIMPLE PYTHON
        # -----------------------------------------------------

        elif self.environment == "python_simple":

            result = self._check_simple_python()

        # -----------------------------------------------------
        # SIMPLE JAVASCRIPT
        # -----------------------------------------------------

        elif self.environment == "javascript_simple":

            result = self._check_simple_js()

        # -----------------------------------------------------
        # SIMPLE TYPESCRIPT
        # -----------------------------------------------------

        elif self.environment == "typescript_simple":

            result = self._check_simple_ts()

        # -----------------------------------------------------
        # SIMPLE JAVA
        # -----------------------------------------------------

        elif self.environment == "java":

            result = self._check_simple_java()

        # -----------------------------------------------------
        # UNKNOWN
        # -----------------------------------------------------

        else:

            result = {
                "status": "FAILED",
                "error": (
                    "Unknown or unsupported environment: "
                    f"{self.environment}"
                ),
                "stdout": "",
                "stderr": ""
            }

        print("--- [AGENT COMPLETED] ---")

        return result

    # =========================================================
    # FIND NODE PROJECT
    # =========================================================

    def _find_node_project(self):

        # -----------------------------------------------------
        # Check root package.json first
        # -----------------------------------------------------

        root_package = (
            self.repo_path / "package.json"
        )

        if root_package.exists():

            return self.repo_path

        # -----------------------------------------------------
        # Search nested package.json files
        # -----------------------------------------------------

        candidates = []

        for package_file in self.repo_path.rglob(
            "package.json"
        ):

            if not package_file.is_file():
                continue

            if "node_modules" in package_file.parts:
                continue

            if ".next" in package_file.parts:
                continue

            if "dist" in package_file.parts:
                continue

            if "build" in package_file.parts:
                continue

            candidates.append(
                package_file.parent
            )

        if not candidates:
            return None

        # -----------------------------------------------------
        # Prefer frontend
        # -----------------------------------------------------

        for candidate in candidates:

            if candidate.name.lower() in (
                "frontend",
                "client",
                "web",
                "app"
            ):

                return candidate

        # -----------------------------------------------------
        # Otherwise use first project
        # -----------------------------------------------------

        return candidates[0]

    # =========================================================
    # FORMAL JAVASCRIPT / TYPESCRIPT PROJECT
    # =========================================================

    def _check_js_build(self):

        print(
            "[INFO] Running JavaScript/TypeScript "
            "project build..."
        )

        project_root = (
            self._find_node_project()
        )

        if project_root is None:

            return {
                "status": "FAILED",
                "error": (
                    "No package.json found "
                    "in repository."
                ),
                "stdout": "",
                "stderr": ""
            }

        print(
            f"[INFO] Node project detected at: "
            f"{project_root}"
        )

        # -----------------------------------------------------
        # Install dependencies if needed
        # -----------------------------------------------------

        node_modules = (
            project_root / "node_modules"
        )

        if not node_modules.exists():

            print(
                "[INFO] Installing Node.js dependencies..."
            )

            try:

                install_process = subprocess.run(
                    [
                        "npm",
                        "install"
                    ],
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    timeout=180
                )

                if install_process.returncode != 0:

                    print(
                        "[ERROR] npm install failed."
                    )

                    return {
                        "status": "FAILED",
                        "error": (
                            "npm dependency installation "
                            "failed."
                        ),
                        "stdout": (
                            install_process.stdout
                        ),
                        "stderr": (
                            install_process.stderr
                        )
                    }

                print(
                    "[SUCCESS] npm install passed."
                )

            except subprocess.TimeoutExpired:

                return {
                    "status": "FAILED",
                    "error": (
                        "npm install timed out."
                    ),
                    "stdout": "",
                    "stderr": ""
                }

            except Exception as e:

                return {
                    "status": "FAILED",
                    "error": str(e),
                    "stdout": "",
                    "stderr": str(e)
                }

        # -----------------------------------------------------
        # Determine package manager
        # -----------------------------------------------------

        if shutil.which("bun"):

            command = [
                "bun",
                "run",
                "build"
            ]

        else:

            command = [
                "npm",
                "run",
                "build"
            ]

        print(
            "[INFO] Running project build..."
        )

        try:

            process = subprocess.run(
                command,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=180
            )

            if process.returncode == 0:

                print(
                    "[SUCCESS] Project build passed."
                )

                return {
                    "status": "PASSED",
                    "stdout": process.stdout,
                    "stderr": process.stderr
                }

            print(
                "[ERROR] Project build failed."
            )

            return {
                "status": "FAILED",
                "error": (
                    "Project build failed."
                ),
                "stdout": process.stdout,
                "stderr": process.stderr
            }

        except subprocess.TimeoutExpired:

            return {
                "status": "FAILED",
                "error": (
                    "Project build timed out "
                    "after 180 seconds."
                ),
                "stdout": "",
                "stderr": ""
            }

        except Exception as e:

            return {
                "status": "FAILED",
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }

    # =========================================================
    # FORMAL PYTHON PROJECT
    # =========================================================

    def _check_python_compilation(self):

        print(
            "[INFO] Running Python compilation check..."
        )

        try:

            process = subprocess.run(
                [
                    "python",
                    "-m",
                    "compileall",
                    "."
                ],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=120
            )

            if process.returncode == 0:

                print(
                    "[SUCCESS] Python compilation passed."
                )

                return {
                    "status": "PASSED",
                    "stdout": process.stdout,
                    "stderr": process.stderr
                }

            print(
                "[ERROR] Python compilation failed."
            )

            return {
                "status": "FAILED",
                "error": (
                    "Python compilation failed."
                ),
                "stdout": process.stdout,
                "stderr": process.stderr
            }

        except subprocess.TimeoutExpired:

            return {
                "status": "FAILED",
                "error": (
                    "Python compilation timed out."
                ),
                "stdout": "",
                "stderr": ""
            }

        except Exception as e:

            return {
                "status": "FAILED",
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }

    # =========================================================
    # SIMPLE PYTHON PROJECT
    # =========================================================

    def _check_simple_python(self):

        import py_compile
        import sys

        print(
            "[INFO] Running simple Python validation..."
        )

        python_files = []

        for file_path in self.repo_path.rglob(
            "*.py"
        ):

            if not file_path.is_file():
                continue

            parts = file_path.parts

            if "node_modules" in parts:
                continue

            if "venv" in parts:
                continue

            if ".venv" in parts:
                continue

            if "__pycache__" in parts:
                continue

            python_files.append(
                file_path
            )

        if not python_files:

            return {
                "status": "FAILED",
                "error": "No Python files found.",
                "stdout": "",
                "stderr": ""
            }

        print(
            f"[INFO] Found {len(python_files)} "
            f"Python file(s)."
        )

        # -----------------------------------------------------
        # Syntax
        # -----------------------------------------------------

        print(
            "[INFO] Checking Python syntax..."
        )

        for file_path in python_files:

            try:

                py_compile.compile(
                    str(file_path),
                    doraise=True
                )

            except py_compile.PyCompileError as e:

                print(
                    f"[ERROR] Syntax error detected: "
                    f"{file_path}"
                )

                return {
                    "status": "FAILED",
                    "error": (
                        "Python syntax error detected."
                    ),
                    "stdout": "",
                    "stderr": str(e)
                }

        print(
            "[SUCCESS] Python syntax check passed."
        )

        # -----------------------------------------------------
        # Find main.py
        # -----------------------------------------------------

        main_file = (
            self.repo_path / "main.py"
        )

        if not main_file.exists():

            print(
                "[INFO] main.py not found."
            )

            print(
                "[SUCCESS] Python validation passed."
            )

            return {
                "status": "PASSED",
                "stdout": (
                    "Python syntax validation passed."
                ),
                "stderr": ""
            }

        # -----------------------------------------------------
        # Execute main.py
        # -----------------------------------------------------

        print(
            "[INFO] Executing main.py..."
        )

        try:

            process = subprocess.run(
                [
                    sys.executable,
                    str(main_file)
                ],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=30
            )

        except subprocess.TimeoutExpired:

            print(
                "[ERROR] Python execution timed out."
            )

            return {
                "status": "FAILED",
                "error": (
                    "Python program execution "
                    "timed out after 30 seconds."
                ),
                "stdout": "",
                "stderr": (
                    "Execution timeout: main.py "
                    "did not finish within 30 seconds."
                )
            }

        except Exception as e:

            return {
                "status": "FAILED",
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }

        if process.returncode != 0:

            print(
                "[ERROR] Python runtime error detected."
            )

            print(
                process.stderr
            )

            return {
                "status": "FAILED",
                "error": (
                    "Python runtime execution failed."
                ),
                "stdout": process.stdout,
                "stderr": process.stderr
            }

        print(
            "[SUCCESS] main.py executed successfully."
        )

        return {
            "status": "PASSED",
            "stdout": process.stdout,
            "stderr": process.stderr
        }

    # =========================================================
    # SIMPLE JAVASCRIPT
    # =========================================================

    def _check_simple_js(self):

        print(
            "[INFO] Running simple JavaScript validation..."
        )

        js_files = []

        for extension in (
            "*.js",
            "*.jsx"
        ):

            for file_path in self.repo_path.rglob(
                extension
            ):

                if not file_path.is_file():
                    continue

                parts = file_path.parts

                if "node_modules" in parts:
                    continue

                if ".next" in parts:
                    continue

                if "dist" in parts:
                    continue

                if "build" in parts:
                    continue

                js_files.append(
                    file_path
                )

        if not js_files:

            return {
                "status": "FAILED",
                "error": "No JavaScript files found.",
                "stdout": "",
                "stderr": ""
            }

        for file_path in js_files:

            try:

                process = subprocess.run(
                    [
                        "node",
                        "--check",
                        str(file_path)
                    ],
                    cwd=str(self.repo_path),
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if process.returncode != 0:

                    print(
                        f"[ERROR] JavaScript syntax "
                        f"error: {file_path}"
                    )

                    return {
                        "status": "FAILED",
                        "error": (
                            "JavaScript syntax error."
                        ),
                        "stdout": process.stdout,
                        "stderr": process.stderr
                    }

            except Exception as e:

                return {
                    "status": "FAILED",
                    "error": str(e),
                    "stdout": "",
                    "stderr": str(e)
                }

        print(
            "[SUCCESS] JavaScript syntax "
            "validation passed."
        )

        return {
            "status": "PASSED",
            "stdout": (
                "JavaScript syntax validation passed."
            ),
            "stderr": ""
        }

    # =========================================================
    # SIMPLE TYPESCRIPT
    # =========================================================

    def _check_simple_ts(self):

        print(
            "[INFO] Running simple TypeScript validation..."
        )

        if not shutil.which("tsc"):

            return {
                "status": "FAILED",
                "error": (
                    "TypeScript compiler (tsc) "
                    "is not installed."
                ),
                "stdout": "",
                "stderr": ""
            }

        ts_files = []

        for extension in (
            "*.ts",
            "*.tsx"
        ):

            for file_path in self.repo_path.rglob(
                extension
            ):

                if not file_path.is_file():
                    continue

                parts = file_path.parts

                if "node_modules" in parts:
                    continue

                if ".next" in parts:
                    continue

                if "dist" in parts:
                    continue

                if "build" in parts:
                    continue

                if file_path.name.endswith(
                    ".d.ts"
                ):
                    continue

                ts_files.append(
                    file_path
                )

        if not ts_files:

            return {
                "status": "FAILED",
                "error": "No TypeScript files found.",
                "stdout": "",
                "stderr": ""
            }

        for file_path in ts_files:

            try:

                process = subprocess.run(
                    [
                        "tsc",
                        "--noEmit",
                        str(file_path)
                    ],
                    cwd=str(self.repo_path),
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if process.returncode != 0:

                    print(
                        f"[ERROR] TypeScript error: "
                        f"{file_path}"
                    )

                    return {
                        "status": "FAILED",
                        "error": (
                            "TypeScript validation failed."
                        ),
                        "stdout": process.stdout,
                        "stderr": process.stderr
                    }

            except Exception as e:

                return {
                    "status": "FAILED",
                    "error": str(e),
                    "stdout": "",
                    "stderr": str(e)
                }

        print(
            "[SUCCESS] TypeScript validation passed."
        )

        return {
            "status": "PASSED",
            "stdout": (
                "TypeScript validation passed."
            ),
            "stderr": ""
        }

    # =========================================================
    # JAVA BUILD
    # =========================================================

    def _check_java_build(self):

        print(
            "[INFO] Running Java project build..."
        )

        pom_file = (
            self.repo_path / "pom.xml"
        )

        gradle_file = (
            self.repo_path / "build.gradle"
        )

        gradle_kts_file = (
            self.repo_path / "build.gradle.kts"
        )

        try:

            if pom_file.exists():

                print(
                    "[INFO] Maven project detected."
                )

                process = subprocess.run(
                    [
                        "mvn",
                        "test"
                    ],
                    cwd=str(self.repo_path),
                    capture_output=True,
                    text=True,
                    timeout=180
                )

            elif (
                gradle_file.exists()
                or gradle_kts_file.exists()
            ):

                print(
                    "[INFO] Gradle project detected."
                )

                gradlew = (
                    self.repo_path / "gradlew"
                )

                if gradlew.exists():

                    command = [
                        str(gradlew),
                        "build"
                    ]

                elif shutil.which("gradle"):

                    command = [
                        "gradle",
                        "build"
                    ]

                else:

                    return {
                        "status": "FAILED",
                        "error": (
                            "Gradle project detected "
                            "but Gradle is unavailable."
                        ),
                        "stdout": "",
                        "stderr": ""
                    }

                process = subprocess.run(
                    command,
                    cwd=str(self.repo_path),
                    capture_output=True,
                    text=True,
                    timeout=180
                )

            else:

                return self._check_simple_java()

            if process.returncode == 0:

                print(
                    "[SUCCESS] Java build passed."
                )

                return {
                    "status": "PASSED",
                    "stdout": process.stdout,
                    "stderr": process.stderr
                }

            print(
                "[ERROR] Java build failed."
            )

            return {
                "status": "FAILED",
                "error": "Java build failed.",
                "stdout": process.stdout,
                "stderr": process.stderr
            }

        except subprocess.TimeoutExpired:

            return {
                "status": "FAILED",
                "error": (
                    "Java build timed out."
                ),
                "stdout": "",
                "stderr": ""
            }

        except Exception as e:

            return {
                "status": "FAILED",
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }

    # =========================================================
    # SIMPLE JAVA
    # =========================================================

    def _check_simple_java(self):

        print(
            "[INFO] Running simple Java validation..."
        )

        if not shutil.which("javac"):

            return {
                "status": "FAILED",
                "error": (
                    "Java compiler (javac) "
                    "is not installed."
                ),
                "stdout": "",
                "stderr": ""
            }

        java_files = []

        for file_path in self.repo_path.rglob(
            "*.java"
        ):

            if not file_path.is_file():
                continue

            parts = file_path.parts

            if "node_modules" in parts:
                continue

            if "target" in parts:
                continue

            if "build" in parts:
                continue

            java_files.append(
                file_path
            )

        if not java_files:

            return {
                "status": "FAILED",
                "error": "No Java files found.",
                "stdout": "",
                "stderr": ""
            }

        build_directory = (
            self.repo_path / ".java_build"
        )

        build_directory.mkdir(
            exist_ok=True
        )

        try:

            command = [
                "javac",
                "-d",
                str(build_directory)
            ]

            command.extend(
                [
                    str(file_path)
                    for file_path in java_files
                ]
            )

            process = subprocess.run(
                command,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=120
            )

            if process.returncode != 0:

                print(
                    "[ERROR] Java compilation failed."
                )

                return {
                    "status": "FAILED",
                    "error": (
                        "Java compilation failed."
                    ),
                    "stdout": process.stdout,
                    "stderr": process.stderr
                }

            print(
                "[SUCCESS] Java compilation passed."
            )

            return {
                "status": "PASSED",
                "stdout": process.stdout,
                "stderr": process.stderr
            }

        except subprocess.TimeoutExpired:

            return {
                "status": "FAILED",
                "error": (
                    "Java compilation timed out."
                ),
                "stdout": "",
                "stderr": ""
            }

        except Exception as e:

            return {
                "status": "FAILED",
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }