import subprocess
import os
import shutil
import glob

class AnalysisAgent:
    """
    Agent 2: Analysis Agent
    Responsibility: 
    1. Run build commands for complex projects.
    2. Run individual file syntax checks for simple projects.
    3. Capture stderr for the Healing Agent.
    """

    def __init__(self, repo_path, environment):
        self.repo_path = repo_path
        self.environment = environment

    def execute(self):
        print(f"--- [AGENT START]: AnalysisAgent ---")
        print(f"[LOG] Analyzing environment: {self.environment}")

        if "javascript" in self.environment and "simple" not in self.environment:
            result = self._check_js_build()
        elif "python" in self.environment and "simple" not in self.environment:
            result = self._check_python_compilation()
        elif "python_simple" in self.environment:
            result = self._check_simple_python()
        elif "javascript_simple" in self.environment:
            result = self._check_simple_js()
        else:
            result = {"status": "FAILED", "error": "Unknown or empty environment"}

        print(f"--- [AGENT COMPLETED] ---")
        return result

    def _is_tool_installed(self, name):
        return shutil.which(name) is not None

    def _check_js_build(self):
        """Runs build command for formal JS/TS projects."""
        cmd = ["bun", "run", "build"] if "bun" in self.environment and self._is_tool_installed("bun") else ["npm", "run", "build"]
        print(f"[LOG] Running Build: {' '.join(cmd)}")
        try:
            process = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, timeout=300)
            if process.returncode == 0:
                return {"status": "PASSED", "message": "Build successful"}
            else:
                return {"status": "FAILED", "error_type": "BUILD_ERROR", "stderr": process.stderr}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    def _check_python_compilation(self):
        """Checks for syntax errors in formal Python projects."""
        print("[LOG] Checking Python compilation...")
        try:
            process = subprocess.run(["python", "-m", "compileall", "."], cwd=self.repo_path, capture_output=True, text=True)
            if process.returncode != 1: # compileall usually returns 1 only on error
                return {"status": "PASSED", "message": "Compilation successful"}
            return {"status": "FAILED", "error_type": "SYNTAX_ERROR", "stderr": process.stdout} # compileall prints to stdout often
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    def _check_simple_python(self):
        """Iterates over all .py files and checks syntax individually."""
        print("[LOG] Analyzing individual Python files...")
        errors = ""
        failed = False
        
        py_files = glob.glob(os.path.join(self.repo_path, "**/*.py"), recursive=True)
        
        for file_path in py_files:
            try:
                # py_compile checks syntax without executing
                subprocess.run(["python", "-m", "py_compile", file_path], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                failed = True
                rel_path = os.path.relpath(file_path, self.repo_path)
                errors += f"Error in {rel_path}:\n{e.stderr.decode()}\n"

        if failed:
            return {"status": "FAILED", "error_type": "SYNTAX_ERROR", "stderr": errors}
        return {"status": "PASSED", "message": "All Python files valid"}

    def _check_simple_js(self):
        """Iterates over all .js files and checks syntax using Node."""
        print("[LOG] Analyzing individual JavaScript files...")
        errors = ""
        failed = False

        if not self._is_tool_installed("node"):
             return {"status": "FAILED", "error": "Node.js not installed for analysis"}

        js_files = glob.glob(os.path.join(self.repo_path, "**/*.js"), recursive=True)
        # Exclude node_modules just in case
        js_files = [f for f in js_files if "node_modules" not in f]

        for file_path in js_files:
            try:
                # node --check (-c) verifies syntax
                subprocess.run(["node", "-c", file_path], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                failed = True
                rel_path = os.path.relpath(file_path, self.repo_path)
                # Node -c usually prints syntax errors to stderr
                errors += f"Error in {rel_path}:\n{e.stderr.decode()}\n"

        if failed:
            return {"status": "FAILED", "error_type": "SYNTAX_ERROR", "stderr": errors}
        return {"status": "PASSED", "message": "All JS files valid"}