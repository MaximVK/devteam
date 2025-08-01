#!/usr/bin/env python3
"""Enhanced agent with tool capabilities for file system access"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core.claude_agent import ClaudeAgent, AgentSettings, AgentRole
from core.agent_tools import AgentTools
from core.git_helper import GitHelper
from config.settings import settings
import uvicorn


class ToolRequest(BaseModel):
    tool: str
    parameters: Dict[str, Any]


class ToolResponse(BaseModel):
    success: bool
    result: Any
    error: Optional[str] = None


class ToolEnabledAgent:
    """Agent with file system tools"""
    
    def __init__(self, agent: ClaudeAgent, workspace_path: str, git_config: Dict[str, Any]):
        self.agent = agent
        self.tools = AgentTools(workspace_path)
        self.git_helper = GitHelper(workspace_path, git_config)
        self.workspace_path = workspace_path
        
    async def process_with_tools(self, message: str) -> str:
        """Process message and handle tool requests"""
        # First, get the agent's response
        response = await self.agent.process_message(message)
        
        # Check if the response contains tool requests
        # For now, we'll use a simple format: TOOL:toolname:params
        if "TOOL:" in response:
            tool_results = []
            lines = response.split('\n')
            
            for line in lines:
                if line.startswith("TOOL:"):
                    try:
                        _, tool_name, params_str = line.split(":", 2)
                        params = json.loads(params_str)
                        result = await self.execute_tool(tool_name, params)
                        tool_results.append(f"Result of {tool_name}: {result}")
                    except Exception as e:
                        tool_results.append(f"Error executing {tool_name}: {str(e)}")
            
            # Append tool results to response
            if tool_results:
                response += "\n\n--- Tool Results ---\n" + "\n".join(tool_results)
                
        return response
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool with given parameters"""
        try:
            if tool_name == "read_file":
                return self.tools.read_file(params["path"])
            elif tool_name == "write_file":
                return self.tools.write_file(params["path"], params["content"])
            elif tool_name == "list_files":
                return self.tools.list_files(params.get("directory", "."))
            elif tool_name == "execute_command":
                return self.tools.execute_command(params["command"], params.get("cwd"))
            elif tool_name == "search_files":
                return self.tools.search_files(params["pattern"], params.get("file_pattern", "*"))
            elif tool_name == "get_file_info":
                return self.tools.get_file_info(params["path"])
            elif tool_name == "create_branch":
                return self.git_helper.create_feature_branch(
                    self.agent.settings.role.value,
                    params.get("task_id", "task"),
                    params.get("task_title")
                )
            elif tool_name == "commit_changes":
                return self.git_helper.commit_changes(
                    params["title"],
                    params["description"],
                    self.agent.settings.role.value,
                    params.get("task_id", "task")
                )
            elif tool_name == "push_branch":
                return self.git_helper.push_branch(params["branch_name"])
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        except Exception as e:
            return {"error": str(e)}


# Create enhanced API
app = FastAPI()


@app.post("/ask")
async def ask_agent(request: Dict[str, Any]):
    """Process a message with tool support"""
    message = request.get("message", "")
    context = request.get("context", {})
    
    # Get the tool-enabled agent from app state
    tool_agent = app.state.tool_agent
    
    response = await tool_agent.process_with_tools(message)
    
    return {"response": response}


@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, request: ToolRequest):
    """Direct tool execution endpoint"""
    tool_agent = app.state.tool_agent
    
    try:
        result = await tool_agent.execute_tool(tool_name, request.parameters)
        return ToolResponse(success=True, result=result)
    except Exception as e:
        return ToolResponse(success=False, result=None, error=str(e))


@app.get("/")
async def root():
    """Health check"""
    return {"status": "running", "agent": app.state.agent_role, "tools": "enabled"}


if __name__ == "__main__":
    # Get configuration from environment
    role = os.environ.get("AGENT_ROLE", "backend").lower()
    
    # Load workspace configuration
    workspace_config_path = project_root / "config" / "agent_workspace.json"
    with open(workspace_config_path) as f:
        workspace_config = json.load(f)
    
    agent_config = workspace_config.get("agents", {}).get(role, {})
    workspace_path = agent_config.get("working_directory", "/Users/maxim/dev/agent-workspace/devteam")
    git_config = workspace_config.get("workspace", {}).get("git_config", {})
    
    # Create agent
    agent_settings = AgentSettings(
        role=AgentRole[role.upper()],
        anthropic_api_key=settings.anthropic_api_key,
        model=settings.default_model,
        port=settings.get_agent_port(role),
        telegram_channel_id=settings.telegram_channel_id,
        github_repo=settings.github_repo,
        _env_file=None
    )
    
    agent = ClaudeAgent(agent_settings)
    
    # Create tool-enabled agent
    tool_agent = ToolEnabledAgent(agent, workspace_path, git_config)
    
    # Store in app state
    app.state.tool_agent = tool_agent
    app.state.agent_role = role
    
    # Run the API
    port = settings.get_agent_port(role)
    uvicorn.run(app, host="0.0.0.0", port=port)