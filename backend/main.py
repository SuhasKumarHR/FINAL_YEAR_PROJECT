import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import socketio
from container_manager import run_pipeline_in_container

# Load environment variables
load_dotenv()

app = FastAPI(title="Rift Autonomous DevOps Agent", version="1.0.0")

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Wrap FastAPI app with Socket.IO
socket_app = socketio.ASGIApp(sio, app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    repo_url: HttpUrl
    team_name: str
    leader_name: str


class RunResponse(BaseModel):
    status: str
    total_time_minutes: float
    fixes_applied: int
    branch: str
    pr_link: str
    speed_bonus_eligible: bool
    fixes: list[dict]


@app.post("/run", response_model=RunResponse)
def run_pipeline(request: RunRequest):
    # PRE-FLIGHT CHECKS
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("GITHUB_TOKEN"):
        raise HTTPException(
            status_code=500,
            detail="Missing API keys: GEMINI_API_KEY or GITHUB_TOKEN not set.",
        )

    repo_url = str(request.repo_url)
    team_name = request.team_name.strip()
    leader_name = request.leader_name.strip()

    try:
        result = run_pipeline_in_container(repo_url, team_name, leader_name)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result.get("status") == "FAILED":
        error_msg = result.get("error", "Pipeline failed inside container")
        raise HTTPException(status_code=500, detail=error_msg)

    return RunResponse(
        status=result.get("status", "UNKNOWN"),
        total_time_minutes=result.get("total_time_minutes", 0),
        fixes_applied=result.get("fixes_applied", 0),
        branch=result.get("branch", "N/A"),
        pr_link=result.get("pr_link", "N/A"),
        speed_bonus_eligible=result.get("speed_bonus_eligible", False),
        fixes=result.get("fixes", []),
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio.emit('log', {
        'message': '🔌 Connected to RIFT Agent backend',
        'type': 'info'
    }, room=sid)


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")


@sio.event
async def start_agent(sid, data):
    """Handle agent start request via WebSocket"""
    print(f"[Socket] Received start_agent from {sid}: {data}")
    
    repo_url = data.get('repo_url')
    team_name = data.get('team_name')
    leader_name = data.get('leader_name')
    retry_limit = data.get('retry_limit', 5)  # Default to 5 if not provided
    
    if not repo_url or not team_name or not leader_name:
        await sio.emit('error_fatal', {
            'message': 'Missing required fields'
        }, room=sid)
        return
    
    # Pre-flight checks
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("GITHUB_TOKEN"):
        await sio.emit('error_fatal', {
            'message': 'Missing API keys: GEMINI_API_KEY or GITHUB_TOKEN not set.'
        }, room=sid)
        return
    
    # Create a callback function to emit logs
    async def log_callback(message: str, log_type: str = "info", stage: str = None):
        payload = {'message': message, 'type': log_type}
        if stage:
            payload['stage'] = stage
        await sio.emit('log', payload, room=sid)
    
    # Run pipeline in background
    asyncio.create_task(run_agent_pipeline(sid, repo_url, team_name, leader_name, retry_limit, log_callback))


async def run_agent_pipeline(sid: str, repo_url: str, team_name: str, leader_name: str, retry_limit: int, log_callback):
    """Run the pipeline and emit results"""
    try:
        await log_callback("🚀 Initializing Autonomous DevOps Agent...", "info", "Initializing")
        
        # Create a synchronous wrapper for the callback that can be called from thread
        loop = asyncio.get_event_loop()
        
        def sync_log_callback(message: str, log_type: str = "info", stage: str = None):
            """Thread-safe synchronous wrapper for async log callback"""
            payload = {'message': message, 'type': log_type}
            if stage:
                payload['stage'] = stage
            # Schedule the emit on the main event loop from the worker thread
            asyncio.run_coroutine_threadsafe(
                sio.emit('log', payload, room=sid),
                loop
            )
        
        # Run the pipeline in a thread pool to avoid blocking
        result = await loop.run_in_executor(
            None, 
            run_pipeline_in_container, 
            repo_url, 
            team_name, 
            leader_name,
            retry_limit,
            sync_log_callback
        )
        
        if result.get("status") == "FAILED":
            await sio.emit('error_fatal', {
                'message': result.get('error', 'Pipeline failed inside container')
            }, room=sid)
        else:
            # Send completion event
            await sio.emit('completed', {
                'status': result.get('status', 'UNKNOWN'),
                'total_time': result.get('total_time_minutes', 0),
                'pr_link': result.get('pr_link', 'N/A'),
                'branch': result.get('branch', 'N/A'),
                'fixes': result.get('fixes', []),
                'iterations_used': result.get('iterations_used', 1),
                'total_failures': result.get('total_failures', 0),
                'commits_count': result.get('commits_count', 1),
            }, room=sid)
        
    except Exception as e:
        await sio.emit('error_fatal', {
            'message': f'Pipeline error: {str(e)}'
        }, room=sid)


# Export the socket_app for uvicorn
# Run with: uvicorn main:socket_app --reload --host 0.0.0.0 --port 8000
app = socket_app