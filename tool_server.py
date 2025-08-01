#!/usr/bin/env python3
"""Tool server that provides file system access to agents via HTTP API"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.agent_tools import AgentTools
from core.git_helper import GitHelper

app = FastAPI(title="Agent Tool Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load workspace configuration
workspace_config_path = Path(__file__).parent / "config" / "agent_workspace.json"
with open(workspace_config_path) as f:
    workspace_config = json.load(f)

# Initialize tools for each agent's workspace
agent_tools = {}
agent_git_helpers = {}

for agent_name, agent_config in workspace_config.get("agents", {}).items():
    workspace_path = agent_config.get("working_directory", "/Users/maxim/dev/agent-workspace/devteam")
    agent_tools[agent_name] = AgentTools(workspace_path)
    agent_git_helpers[agent_name] = GitHelper(
        workspace_path, 
        workspace_config.get("workspace", {}).get("git_config", {})
    )


@app.get("/")
async def root():
    """Health check"""
    return {"status": "running", "service": "tool-server", "agents": list(agent_tools.keys())}


@app.post("/tools/{agent_name}/read_file")
async def read_file(agent_name: str, request: Dict[str, Any]):
    """Read a file"""
    if agent_name not in agent_tools:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not configured")
    
    try:
        content = agent_tools[agent_name].read_file(request["path"])
        return {"success": True, "content": content}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/tools/{agent_name}/write_file")
async def write_file(agent_name: str, request: Dict[str, Any]):
    """Write a file"""
    if agent_name not in agent_tools:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not configured")
    
    try:
        result = agent_tools[agent_name].write_file(request["path"], request["content"])
        return {"success": True, "message": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/tools/{agent_name}/list_files")
async def list_files(agent_name: str, request: Dict[str, Any]):
    """List files in a directory"""
    if agent_name not in agent_tools:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not configured")
    
    try:
        files = agent_tools[agent_name].list_files(request.get("directory", "."))
        return {"success": True, "files": files}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/tools/{agent_name}/execute")
async def execute_command(agent_name: str, request: Dict[str, Any]):
    """Execute a command"""
    if agent_name not in agent_tools:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not configured")
    
    try:
        result = agent_tools[agent_name].execute_command(
            request["command"], 
            request.get("cwd")
        )
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/tools/{agent_name}/search")
async def search_files(agent_name: str, request: Dict[str, Any]):
    """Search in files"""
    if agent_name not in agent_tools:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not configured")
    
    try:
        matches = agent_tools[agent_name].search_files(
            request["pattern"],
            request.get("file_pattern", "*")
        )
        return {"success": True, "matches": matches}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/tools/{agent_name}/git/create_branch")
async def create_branch(agent_name: str, request: Dict[str, Any]):
    """Create a git branch"""
    if agent_name not in agent_git_helpers:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not configured")
    
    try:
        branch_name = agent_git_helpers[agent_name].create_feature_branch(
            agent_name,
            request.get("task_id", "task"),
            request.get("task_title")
        )
        return {"success": True, "branch_name": branch_name}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/tools/{agent_name}/git/commit")
async def commit_changes(agent_name: str, request: Dict[str, Any]):
    """Commit changes"""
    if agent_name not in agent_git_helpers:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not configured")
    
    try:
        success = agent_git_helpers[agent_name].commit_changes(
            request["title"],
            request["description"],
            agent_name,
            request.get("task_id", "task")
        )
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/tools/{agent_name}/git/push")
async def push_branch(agent_name: str, request: Dict[str, Any]):
    """Push branch"""
    if agent_name not in agent_git_helpers:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not configured")
    
    try:
        success = agent_git_helpers[agent_name].push_branch(request["branch_name"])
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/tools/{agent_name}/git/status")
async def git_status(agent_name: str):
    """Get git status"""
    if agent_name not in agent_git_helpers:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not configured")
    
    try:
        status = agent_git_helpers[agent_name].get_branch_status()
        return {"success": True, "status": status}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print("🔧 Starting Tool Server on port 8500...")
    uvicorn.run(app, host="0.0.0.0", port=8500)