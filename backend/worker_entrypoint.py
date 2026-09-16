"""
Worker Entrypoint — runs inside the Docker container.

Reads pipeline parameters from environment variables, executes the full
agent pipeline (prep → analyze → heal → git), and prints a single JSON
result to stdout.
"""

import json
import os
import sys
import time

from repo_prep_agent import RepoPrepAgent
from analysis_agent import AnalysisAgent
from healing_agent import HealingAgent
from git_agent import GitAgent

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))


def main():
    repo_url = os.environ.get("REPO_URL")
    team_name = os.environ.get("TEAM_NAME", "").strip()
    leader_name = os.environ.get("LEADER_NAME", "").strip()

    if not repo_url or not team_name or not leader_name:
        _fail("Missing required env vars: REPO_URL, TEAM_NAME, LEADER_NAME")

    if not os.getenv("GEMINI_API_KEY") or not os.getenv("GITHUB_TOKEN"):
        _fail("Missing API keys: GEMINI_API_KEY or GITHUB_TOKEN not set.")

    start_time = time.time()

    # --- STAGE 1: PREP ---
    prep_agent = RepoPrepAgent(repo_url, team_name, leader_name)
    prep_result = prep_agent.execute()

    if prep_result["status"] == "FAILED":
        _fail(f"Stage 1 (Prep) failed: {prep_result.get('error')}")

    repo_path = prep_result["repo_path"]
    environment = prep_result["environment"]
    target_branch = prep_result["branch_name"]

    # --- STAGE 2 & 3: HEALING LOOP ---
    iteration = 0
    all_fixes = []
    final_success = False
    total_failures = 0
    last_error = None

    while iteration < MAX_RETRIES:
        iteration += 1

        # Analyze
        analysis_agent = AnalysisAgent(repo_path, environment)
        analysis_result = analysis_agent.execute()

        if analysis_result["status"] == "PASSED":
            final_success = True
            break
        
        # Count failures detected in this iteration
        total_failures += 1

        # Heal
        healing_agent = HealingAgent(repo_path, analysis_result)
        heal_result = healing_agent.execute()

        if heal_result["status"] == "SUCCESS":
            new_fixes = heal_result.get("applied_fixes", [])
            all_fixes.extend(new_fixes)
        else:
            last_error = heal_result.get("error", "Healing failed")
            break

    # --- STAGE 4: GIT & PR ---
    pr_link = "N/A"

    if final_success and all_fixes:
        git_agent = GitAgent(
            repo_path=repo_path,
            repo_url=repo_url,
            branch_name=target_branch,
            team_name=team_name,
            leader_name=leader_name,
        )

        git_result = git_agent.execute(fixes=all_fixes)

        if git_result["status"] == "SUCCESS":
            if git_result.get("pr_url"):
                pr_link = git_result["pr_url"]
        else:
            _fail(f"Stage 4 (Git) failed: {git_result.get('error')}")

    elapsed = (time.time() - start_time) / 60

    result = {
        "status": "SUCCESS" if final_success else "FAILED",
        "total_time_minutes": round(elapsed, 2),
        "fixes_applied": len(all_fixes),
        "branch": target_branch,
        "pr_link": pr_link,
        "speed_bonus_eligible": elapsed < 5,
        "fixes": all_fixes,
        "iterations_used": iteration,
        "total_failures": total_failures if total_failures > 0 else len(all_fixes),
        "commits_count": len(all_fixes) if all_fixes else 1,
    }

    if result["status"] == "FAILED":
        result["error"] = last_error or "Pipeline failed inside container"

    # Print as JSON on a single line to stdout — the host will parse this
    print(json.dumps(result))
    sys.exit(0)


def _fail(message: str):
    """Print a failure JSON and exit with code 1."""
    result = {"status": "FAILED", "error": message}
    print(json.dumps(result))
    sys.exit(1)


if __name__ == "__main__":
    main()
