from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import asyncio

from core.orchestrator import AgentOrchestrator, AgentRole
from core.telegram_bridge import TelegramSettings
from core.github_sync import GitHubSettings


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


class CreateAgentRequest(BaseModel):
    role: AgentRole
    model: str = "claude-3-sonnet-20240229"
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
    """Get all agents and their status"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="System not initialized")
        
    return await orchestrator.get_all_agents_status()


@app.post("/api/agents")
async def create_agent(request: CreateAgentRequest):
    """Create a new agent"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="System not initialized")
        
    try:
        agent = await orchestrator.create_agent(
            role=request.role,
            model=request.model,
            github_repo=request.github_repo,
            telegram_channel_id=request.telegram_channel_id
        )
        return {"status": "created", "agent": agent.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/agents/{role}")
async def get_agent_status(role: str):
    """Get status of a specific agent"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="System not initialized")
        
    status = await orchestrator.get_agent_status(role)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
        
    return status


@app.post("/api/agents/{role}/restart")
async def restart_agent(role: str):
    """Restart an agent"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="System not initialized")
        
    try:
        await orchestrator.restart_agent(role)
        return {"status": "restarted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/agents/{role}")
async def stop_agent(role: str):
    """Stop and remove an agent"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="System not initialized")
        
    try:
        await orchestrator.stop_agent(role)
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/tasks/assign")
async def assign_task(request: TaskAssignRequest):
    """Manually assign a task to an agent"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="System not initialized")
        
    if request.agent_role not in orchestrator.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    agent = orchestrator.agents[request.agent_role]
    
    # Send task to agent
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:{agent.port}/assign",
            json={
                "id": f"manual-{asyncio.get_event_loop().time()}",
                "title": request.task_title,
                "description": request.task_description,
                "github_issue_number": request.github_issue_number
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to assign task")
            
    return {"status": "assigned", "response": response.json()}


@app.post("/api/tasks/sync-github")
async def sync_github_tasks():
    """Sync and assign GitHub tasks to agents"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="System not initialized")
        
    if not orchestrator.github_sync:
        raise HTTPException(status_code=400, detail="GitHub not configured")
        
    await orchestrator.assign_github_tasks()
    return {"status": "synced"}


@app.get("/api/agents/{role}/logs")
async def get_agent_logs(role: str, limit: int = 50):
    """Get agent message history"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="System not initialized")
        
    if role not in orchestrator.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    agent = orchestrator.agents[role]
    
    # Fetch logs from agent
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:{agent.port}/history")
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch logs")
            
        data = response.json()
        return {
            "message_history": data.get("message_history", [])[-limit:],
            "task_history": data.get("task_history", [])
        }


@app.get("/api/claude/{role}")
async def get_claude_prompt(role: str):
    """Get CLAUDE.md content for a role"""
    claude_file = Path("config") / f"claude-{role}.md"
    
    if not claude_file.exists():
        raise HTTPException(status_code=404, detail="CLAUDE.md file not found")
        
    return {"content": claude_file.read_text()}


@app.put("/api/claude/{role}")
async def update_claude_prompt(role: str, content: Dict[str, str]):
    """Update CLAUDE.md content for a role"""
    claude_file = Path("config") / f"claude-{role}.md"
    
    try:
        claude_file.write_text(content["content"])
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send agent status updates every 5 seconds
            if orchestrator:
                agents_status = await orchestrator.get_all_agents_status()
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