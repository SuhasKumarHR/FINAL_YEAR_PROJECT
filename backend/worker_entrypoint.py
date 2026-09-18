"""
Worker Entrypoint — runs inside the Docker container.

Reads pipeline parameters from environment variables, executes the full
agent pipeline (prep → analyze → KNN classify → heal → git), and prints
a single JSON result to stdout.
"""

import json
import os
import sys
import time

from repo_prep_agent import RepoPrepAgent
from analysis_agent import AnalysisAgent
from healing_agent import HealingAgent
from git_agent import GitAgent
from failure_classifier import FailureClassifier


MAX_RETRIES = int(os.getenv("MAX_RETRIES", "50"))


def main():
    repo_url = os.environ.get("REPO_URL")
    team_name = os.environ.get("TEAM_NAME", "").strip()
    leader_name = os.environ.get("LEADER_NAME", "").strip()

    if not repo_url or not team_name or not leader_name:
        _fail("Missing required env vars: REPO_URL, TEAM_NAME, LEADER_NAME")

    if not os.getenv("GEMINI_API_KEY") or not os.getenv("GITHUB_TOKEN"):
        _fail("Missing API keys: GEMINI_API_KEY or GITHUB_TOKEN not set.")

    start_time = time.time()

    # ---------------------------------------------------------
    # KNN FAILURE CLASSIFIER
    # ---------------------------------------------------------
    try:
        classifier = FailureClassifier(n_neighbors=3)
        print("[SUCCESS] KNN Failure Classifier initialized.")
    except Exception as e:
        _fail(f"KNN classifier initialization failed: {e}")

    # ---------------------------------------------------------
    # STAGE 1: PREP
    # ---------------------------------------------------------
    prep_agent = RepoPrepAgent(
        repo_url,
        team_name,
        leader_name
    )

    prep_result = prep_agent.execute()

    if prep_result["status"] == "FAILED":
        _fail(
            f"Stage 1 (Prep) failed: "
            f"{prep_result.get('error')}"
        )

    repo_path = prep_result["repo_path"]
    environment = prep_result["environment"]
    target_branch = prep_result["branch_name"]

    # ---------------------------------------------------------
    # STAGE 2 & 3: ANALYSIS + KNN + HEALING LOOP
    # ---------------------------------------------------------
    iteration = 0
    all_fixes = []
    final_success = False
    total_failures = 0
    last_error = None

    while iteration < MAX_RETRIES:
        iteration += 1

        print(
            f"\n========== ITERATION {iteration} "
            f"/ {MAX_RETRIES} =========="
        )

        # -----------------------------------------------------
        # ANALYZE
        # -----------------------------------------------------
        analysis_agent = AnalysisAgent(
            repo_path,
            environment
        )

        analysis_result = analysis_agent.execute()

        # -----------------------------------------------------
        # ANALYSIS PASSED
        # -----------------------------------------------------
        if analysis_result["status"] == "PASSED":
            print(
                "[SUCCESS] Analysis passed. "
                "No healing required."
            )
            final_success = True
            break

        # -----------------------------------------------------
        # ANALYSIS FAILED
        # -----------------------------------------------------
        total_failures += 1

        print("[ERROR] Analysis failed.")

        # -----------------------------------------------------
        # BUILD ERROR TEXT FOR KNN
        # -----------------------------------------------------
        error_text = (
            str(analysis_result.get("stderr", ""))
            + "\n"
            + str(analysis_result.get("stdout", ""))
            + "\n"
            + str(analysis_result.get("error", ""))
        )

        if not error_text.strip():
            error_text = str(analysis_result)

        # -----------------------------------------------------
        # KNN FAILURE CLASSIFICATION
        # -----------------------------------------------------
        try:
            classification = classifier.classify_with_confidence(
                error_text
            )

            failure_category = str(
                classification["category"]
            )

            failure_confidence = float(
                classification["confidence"]
            )

            print(
                f"[KNN] Failure Category: "
                f"{failure_category}"
            )

            print(
                f"[KNN] Confidence: "
                f"{failure_confidence}"
            )

        except Exception as e:
            print(
                f"[WARN] KNN classification failed: {e}"
            )

            failure_category = "UNKNOWN"
            failure_confidence = 0.0

        # -----------------------------------------------------
        # HEAL
        # -----------------------------------------------------
        healing_agent = HealingAgent(
            repo_path,
            analysis_result
        )

        heal_result = healing_agent.execute(
            failure_category=failure_category,
            failure_confidence=failure_confidence
        )

        if heal_result["status"] == "SUCCESS":

            new_fixes = heal_result.get(
                "fixes",
                []
            )

            all_fixes.extend(new_fixes)

            print(
                f"[SUCCESS] Healing iteration "
                f"{iteration} applied "
                f"{len(new_fixes)} fix(es)."
            )

        else:
            last_error = heal_result.get(
                "error",
                "Healing failed"
            )

            print(
                f"[ERROR] Healing failed: "
                f"{last_error}"
            )

            break

    # ---------------------------------------------------------
    # STAGE 4: GIT & PR
    # ---------------------------------------------------------
    pr_link = "N/A"

    if final_success and all_fixes:

        git_agent = GitAgent(
            repo_path=repo_path,
            repo_url=repo_url,
            branch_name=target_branch,
            team_name=team_name,
            leader_name=leader_name,
        )

        git_result = git_agent.execute(
            fixes=all_fixes
        )

        if git_result["status"] == "SUCCESS":

            if git_result.get("pr_url"):
                pr_link = git_result["pr_url"]

        else:
            _fail(
                f"Stage 4 (Git) failed: "
                f"{git_result.get('error')}"
            )

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------
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
        "total_failures": total_failures,
        "commits_count": len(all_fixes) if all_fixes else 1,
    }

    if result["status"] == "FAILED":
        result["error"] = (
            last_error
            or "Pipeline failed inside container"
        )

    print(json.dumps(result))
    sys.exit(0)


def _fail(message: str):
    """Print a failure JSON and exit with code 1."""

    result = {
        "status": "FAILED",
        "error": message
    }

    print(json.dumps(result))
    sys.exit(1)


if __name__ == "__main__":
    main()