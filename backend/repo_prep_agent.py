import os
import shutil
import subprocess
import re
from git import Repo

class RepoPrepAgent:
    """
    Agent 1: Repository Preparation Agent
    Responsibility: 
    1. Clone the repository into a temporary directory.
    2. Detect the environment (Python, JS/TS, or Simple Scripts).
    3. Install dependencies if config files exist.
    4. Generate the mandatory branch name.
    """
    
    def __init__(self, repo_url, team_name, leader_name):
        self.repo_url = repo_url
        # Sanitize names: UPPERCASE, replace spaces with underscores, remove special chars
        self.team_name = self._sanitize_name(team_name)
        self.leader_name = self._sanitize_name(leader_name)
        self.target_dir = os.path.join(os.getcwd(), "temp")
    
    def _sanitize_name(self, name):
        """
        Sanitize name according to naming rules:
        1. Convert to UPPERCASE
        2. Replace spaces with underscores
        3. Remove all special characters except underscores
        4. Remove multiple consecutive underscores
        """
        # Convert to uppercase
        name = name.upper()
        # Replace spaces with underscores
        name = name.replace(" ", "_")
        # Remove all characters except letters, numbers, and underscores
        name = re.sub(r'[^A-Z0-9_]', '', name)
        # Replace multiple consecutive underscores with single underscore
        name = re.sub(r'_+', '_', name)
        # Remove leading/trailing underscores
        name = name.strip('_')
        return name
        
    def execute(self):
        print(f"\n--- [AGENT START]: RepoPrepAgent ---")
        
        if not self._clone_repo():
            return {"status": "FAILED", "error": "Cloning failed"}

        env_info = self._setup_environment()
        
        # Branch naming convention: TEAMNAME_LEADERNAME_AI_Fix
        # All uppercase, underscores only, no special characters
        branch_name = f"{self.team_name}_{self.leader_name}_AI_Fix"
        print(f"[LOG] Generated branch name: {branch_name}")

        print(f"[SUCCESS] Environment detected: {env_info}")
        print(f"--- [AGENT COMPLETED] ---\n")
        
        return {
            "status": "SUCCESS",
            "repo_path": self.target_dir,
            "environment": env_info,
            "branch_name": branch_name
        }

    def _clone_repo(self):
        if os.path.exists(self.target_dir):
            print(f"[LOG] Cleaning existing directory: {self.target_dir}")
            shutil.rmtree(self.target_dir)
            
        try:
            print(f"[LOG] Cloning {self.repo_url}...")
            Repo.clone_from(self.repo_url, self.target_dir)
            return True
        except Exception as e:
            print(f"[ERROR] Clone failed: {str(e)}")
            return False

    def _is_tool_installed(self, name):
        return shutil.which(name) is not None

    def _setup_environment(self):
        """Detects tech stack, handles installs, or identifies simple file structures."""
        files = os.listdir(self.target_dir)
        
        # 1. Formal Python Project
        if "requirements.txt" in files:
            print("[LOG] Detected Python (requirements.txt). Installing...")
            try:
                subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=self.target_dir, check=True)
                return "python"
            except subprocess.CalledProcessError:
                return "python (failed install)"
        
        # 2. Formal JS/TS Project
        elif "package.json" in files:
            if self._is_tool_installed("bun"):
                print("[LOG] Detected JS (package.json). Running 'bun install'...")
                subprocess.run(["bun", "install"], cwd=self.target_dir, check=False)
                return "javascript (bun)"
            else:
                print("[LOG] Detected JS (package.json). Running 'npm install'...")
                subprocess.run(["npm", "install"], cwd=self.target_dir, check=False)
                return "javascript (npm)"

        # 3. Simple Project Detection (Fallback)
        # Scan for at least one .py or .js file to classify the repo
        has_python = any(f.endswith(".py") for f in os.listdir(self.target_dir))
        has_js = any(f.endswith(".js") for f in os.listdir(self.target_dir))

        if has_python:
            print("[LOG] Detected Simple Python Project (No requirements.txt).")
            return "python_simple"
        
        if has_js:
            print("[LOG] Detected Simple JavaScript Project (No package.json).")
            return "javascript_simple"
            
        print("[WARN] No recognized code files found.")
        return "unknown"