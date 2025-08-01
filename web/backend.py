from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import asyncio
import httpx

from core.orchestrator import AgentOrchestrator, AgentRole
from core.telegram_bridge import TelegramSettings
from core.github_sync import GitHubSettings
from core.conversation_history import ConversationHistory


app = FastAPI(title="DevTeam Dashboard")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator: Optional[AgentOrchestrator] = None

# Agent ports mapping
AGENT_PORTS = {
    "backend": 8301,
    "frontend": 8302,
    "database": 8303,
    "qa": 8304,
    "ba": 8305,
    "teamlead": 8306
}


class CreateAgentRequest(BaseModel):
    role: AgentRole
    model: str = "claude-3-5-sonnet-20241022"
    github_repo: Optional[str] = None
    telegram_channel_id: Optional[str] = None


class TaskAssignRequest(BaseModel):
    agent_role: str
    task_title: str
    task_description: str
    github_issue_number: Optional[int] = None


class SystemConfig(BaseModel):
    telegram_bot_token: Optional[str] = None
    telegram_channel_id: Optional[str] = None
    github_token: Optional[str] = None
    github_repo: Optional[str] = None
    anthropic_api_key: str


async def check_agent_health(role: str, port: int) -> Dict[str, Any]:
    """Check if an agent is running on a given port"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:{port}/", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                
                # Get more detailed status if available
                try:
                    status_response = await client.get(f"http://localhost:{port}/status", timeout=2.0)
                    status_data = status_response.json() if status_response.status_code == 200 else {}
                except:
                    status_data = {}
                
                return {
                    "role": role,
                    "port": port,
                    "model": "claude-3-5-sonnet-20241022",
                    "current_task": status_data.get("current_task"),
                    "task_history_count": len(status_data.get("task_history", [])),
                    "last_activity": status_data.get("last_activity", "Unknown"),
                    "total_tokens_used": status_data.get("total_tokens_used", 0),
                    "health": "running",
                    "process": {
                        "pid": None,
                        "status": "running",
                        "uptime": None
                    }
                }
    except:
        pass
    
    return {
        "role": role,
        "port": port,
        "model": "claude-3-5-sonnet-20241022",
        "current_task": None,
        "task_history_count": 0,
        "last_activity": "Never",
        "total_tokens_used": 0,
        "health": "offline",
        "process": {
            "pid": None,
            "status": "stopped",
            "uptime": None
        }
    }


@app.on_event("startup")
async def startup_event():
    global orchestrator
    orchestrator = AgentOrchestrator()


@app.on_event("shutdown")
async def shutdown_event():
    if orchestrator:
        await orchestrator.shutdown()


@app.post("/api/system/initialize")
async def initialize_system(config: SystemConfig):
    """Initialize the system with configurations"""
    global orchestrator
    
    # Set environment variable for Anthropic API
    import os
    os.environ["ANTHROPIC_API_KEY"] = config.anthropic_api_key
    
    telegram_settings = None
    if config.telegram_bot_token and config.telegram_channel_id:
        telegram_settings = TelegramSettings(
            bot_token=config.telegram_bot_token,
            channel_id=config.telegram_channel_id,
            allowed_users=[]
        )
        
    github_settings = None
    if config.github_token and config.github_repo:
        github_settings = GitHubSettings(
            token=config.github_token,
            repo_name=config.github_repo.split("/")[-1],
            organization=config.github_repo.split("/")[-2] if "/" in config.github_repo else None
        )
        
    await orchestrator.initialize(telegram_settings, github_settings)
    
    return {"status": "initialized", "telegram": bool(telegram_settings), "github": bool(github_settings)}


@app.get("/api/agents")
async def get_agents():
    """Get all agents and their status - auto-discover running agents"""
    # Auto-discover agents running on their ports
    tasks = []
    for role, port in AGENT_PORTS.items():
        tasks.append(check_agent_health(role, port))
    
    agents_status = await asyncio.gather(*tasks)
    
    # Filter out offline agents if you want only running ones
    # return [agent for agent in agents_status if agent["health"] == "running"]
    
    # Or return all to show which are online/offline
    return agents_status


@app.post("/api/agents")
async def create_agent(request: CreateAgentRequest):
    """Create a new agent (compatibility endpoint)"""
    # Since agents are already running, just return success
    role = request.role.value if hasattr(request.role, 'value') else str(request.role)
    port = AGENT_PORTS.get(role.lower())
    
    if not port:
        raise HTTPException(status_code=400, detail=f"Unknown agent role: {role}")
    
    # Check if it's running
    status = await check_agent_health(role, port)
    if status["health"] == "running":
        return {"status": "already_running", "agent": status}
    else:
        return {"status": "not_running", "message": "Start agent using ./start-devteam.sh"}


@app.get("/api/agents/{role}")
async def get_agent_status(role: str):
    """Get status of a specific agent"""
    port = AGENT_PORTS.get(role.lower())
    if not port:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")
    
    return await check_agent_health(role, port)


@app.delete("/api/agents/{role}")
async def stop_agent(role: str):
    """Stop a specific agent (not implemented for standalone agents)"""
    raise HTTPException(
        status_code=501,
        detail="Agents are running as standalone services. Use ./stop-devteam.sh to stop them."
    )


@app.post("/api/agents/{role}/restart")
async def restart_agent(role: str):
    """Restart a specific agent (not implemented for standalone agents)"""
    raise HTTPException(
        status_code=501,
        detail="Agents are running as standalone services. Restart them manually."
    )


@app.post("/api/tasks/assign")
async def assign_task(request: TaskAssignRequest):
    """Assign a task to an agent"""
    port = AGENT_PORTS.get(request.agent_role.lower())
    if not port:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {request.agent_role}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:{port}/assign",
                json={
                    "id": f"task_{request.agent_role}_{asyncio.get_event_loop().time()}",
                    "title": request.task_title,
                    "description": request.task_description,
                    "github_issue_number": request.github_issue_number
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to assign task")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Agent not available: {str(e)}")


@app.post("/api/tasks/sync-github")
async def sync_github_tasks():
    """Sync tasks from GitHub (requires orchestrator)"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="System not initialized")
        
    await orchestrator.assign_github_tasks()
    return {"status": "synced"}


@app.get("/api/agents/{role}/logs")
async def get_agent_logs(role: str, limit: int = 50):
    """Get agent logs"""
    import os
    log_file = f"logs/{role}.log"
    
    if not os.path.exists(log_file):
        return {"logs": []}
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            return {"logs": lines[-limit:]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")


@app.get("/api/agents/{role}/history")
async def get_agent_conversation_history(role: str, hours: int = 24):
    """Get conversation history for a specific agent"""
    conversation_history = ConversationHistory()
    history = conversation_history.load_agent_history(role)
    
    if not history:
        return {"history": [], "summary": f"No conversation history for {role}"}
    
    # Get recent context
    recent_context = conversation_history.get_recent_context(role, hours)
    task_context = conversation_history.get_task_context(role)
    
    return {
        "history": history[-20:],  # Last 20 messages
        "recent_context": recent_context,
        "task_context": task_context,
        "total_messages": len(history)
    }


@app.get("/api/conversation-summary")
async def get_all_agents_conversation_summary():
    """Get conversation summary for all agents"""
    conversation_history = ConversationHistory()
    return conversation_history.get_all_agents_summary()


@app.get("/api/claude/{role}")
async def get_claude_prompt(role: str):
    """Get claude.md content for a specific role"""
    claude_file = Path(f"claude/{role}.md")
    
    if not claude_file.exists():
        # Try to generate it
        try:
            import subprocess
            subprocess.run(["python", "scripts/generate_claude.py"], check=True)
        except:
            pass
    
    if claude_file.exists():
        return {"content": claude_file.read_text()}
    else:
        raise HTTPException(status_code=404, detail=f"Claude prompt not found for role: {role}")


@app.put("/api/claude/{role}")
async def update_claude_prompt(role: str, data: Dict[str, str]):
    """Update claude.md content for a specific role"""
    claude_file = Path(f"claude/{role}.md")
    claude_file.parent.mkdir(exist_ok=True)
    
    claude_file.write_text(data["content"])
    return {"status": "updated"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send agent status updates every 5 seconds
            agents_status = await get_agents()
            await websocket.send_json({
                "type": "agents_update",
                "data": agents_status
            })
            
            await asyncio.sleep(5)
            
    except Exception:
        pass
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)