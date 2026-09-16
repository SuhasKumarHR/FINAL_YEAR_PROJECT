import json
import os
import sys
import docker
from typing import Callable, Optional

WORKER_IMAGE = "rift-worker:latest"


def run_pipeline_in_container(
    repo_url: str, 
    team_name: str, 
    leader_name: str,
    retry_limit: int = 5,
    log_callback: Optional[Callable[[str, str, Optional[str]], None]] = None
) -> dict:
    """
    Spin up a worker container, run the pipeline, collect the result, and
    destroy the container.
    
    Args:
        repo_url: Git repository URL
        team_name: Team name
        leader_name: Leader name
        retry_limit: Maximum number of healing iterations (default: 5)
        log_callback: Optional synchronous function to emit logs via WebSocket
        
    Returns:
        dict with pipeline result (status, fixes, pr_link, etc.)
    """
    client = docker.from_env()
    container = None
    
    def emit_log(message: str, log_type: str = "info", stage: str = None):
        """Helper to emit logs both to console and websocket"""
        print(message, flush=True)
        if log_callback:
            try:
                log_callback(message, log_type, stage)
            except Exception as e:
                # Fail silently if socket emit fails
                print(f"[Warning] Failed to emit log via socket: {e}", flush=True)

    env_vars = {
        "REPO_URL": repo_url,
        "TEAM_NAME": team_name,
        "LEADER_NAME": leader_name,
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
        "MAX_RETRIES": str(retry_limit),
    }

    try:
        emit_log(f"📦 Creating container from image '{WORKER_IMAGE}'...", "info", "Stage 1: Prep")
        container = client.containers.run(
            image=WORKER_IMAGE,
            environment=env_vars,
            detach=True,
            mem_limit="1g",
        )

        emit_log(f"✅ Container started: {container.short_id}", "success", "Stage 2: Analysis")
        emit_log("📡 Streaming container logs...", "info")

        # Stream logs directly — this blocks until container exits
        for line in container.logs(stream=True, follow=True, stdout=True, stderr=True):
            decoded = line.decode('utf-8', errors='replace').strip()
            if decoded:
                emit_log(decoded, "info")

        emit_log("✨ Container execution completed", "success")

        # Container has exited by now
        exit_result = container.wait(timeout=30)
        exit_code = exit_result.get("StatusCode", -1)
        emit_log(f"Container exited with code: {exit_code}", "info" if exit_code == 0 else "warning")

        # Get stdout-only for JSON parsing
        stdout_logs = container.logs(stdout=True, stderr=False).decode("utf-8").strip()

        if not stdout_logs:
            raise RuntimeError(f"Worker container produced no output (exit code: {exit_code})")

        last_line = stdout_logs.strip().split("\n")[-1]

        try:
            result = json.loads(last_line)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse worker output as JSON: {e}\n"
                f"Raw output (last 500 chars): {stdout_logs[-500:]}"
            )

        if exit_code != 0 and result.get("status") != "FAILED":
            result["status"] = "FAILED"
            result.setdefault("error", f"Container exited with code {exit_code}")

        status = result.get('status')
        emit_log(
            f"🎉 Pipeline finished with status: {status}", 
            "success" if status == "SUCCESS" else "error",
            "Stage 4: Git Ops" if status == "SUCCESS" else "Failed"
        )
        return result

    except docker.errors.ImageNotFound:
        raise RuntimeError(
            f"Worker image '{WORKER_IMAGE}' not found. "
            f"Build it with: docker build -f Dockerfile.worker -t {WORKER_IMAGE} ."
        )
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"Container execution failed: {e}")

    finally:
        if container is not None:
            try:
                emit_log(f"🧹 Removing container {container.short_id}...", "info")
                container.remove(force=True)
                emit_log("✅ Container removed successfully", "success")
            except Exception as cleanup_err:
                emit_log(f"⚠️ WARNING: Failed to remove container: {cleanup_err}", "warning")