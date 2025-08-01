#!/usr/bin/env python3
"""Run an agent with workspace capabilities"""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.api import AgentAPI
from core.claude_agent import ClaudeAgent, AgentSettings, AgentRole
from config.settings import settings

# Get agent role from environment
role = os.environ.get("AGENT_ROLE", "backend").lower()

# Load workspace configuration
workspace_config_path = project_root / "config" / "agent_workspace.json"
if workspace_config_path.exists():
    with open(workspace_config_path) as f:
        workspace_config = json.load(f)
else:
    workspace_config = {}

# Create agent settings with workspace info
agent_config = workspace_config.get("agents", {}).get(role, {})
workspace_path = agent_config.get("working_directory", "/Users/maxim/dev/agent-workspace/devteam")

# Set up agent context
agent_context = {
    "workspace_path": workspace_path,
    "capabilities": agent_config.get("capabilities", []),
    "file_patterns": agent_config.get("file_patterns", ["*"]),
    "git_config": workspace_config.get("workspace", {}).get("git_config", {}),
    "git_workflow": workspace_config.get("git_workflow", {})
}

print(f"🤖 Starting {role} agent with workspace: {workspace_path}")

# Create enhanced agent settings
agent_settings = AgentSettings(
    role=AgentRole[role.upper()],
    anthropic_api_key=settings.anthropic_api_key,
    model=settings.default_model,
    port=settings.get_agent_port(role),
    telegram_channel_id=settings.telegram_channel_id,
    github_repo=settings.github_repo,
    claude_file=f"claude/{role}_workspace.md",  # Use workspace-aware Claude file
    _env_file=None
)

# Update the Claude prompt to include workspace information
claude_prompt_addition = f"""
## Workspace Configuration

You have access to a Git repository at: {workspace_path}

Your capabilities include: {', '.join(agent_config.get('capabilities', []))}

You can work with these file types: {', '.join(agent_config.get('file_patterns', ['*']))}

### Git Workflow:
- Create feature branches using pattern: {workspace_config.get('git_workflow', {}).get('feature_branch_pattern', 'feature/{task}')}
- Always commit your changes with clear messages
- Push changes to origin
- Create pull requests when tasks are complete

### Working Directory:
Your primary working directory is: {workspace_path}

When users ask you to make changes, you should:
1. Navigate to the appropriate directory
2. Create or modify files as requested
3. Test your changes if applicable
4. Commit and push your changes
5. Report back on what you've done

IMPORTANT: Always use absolute paths starting with {workspace_path} when working with files.
"""

# Create agent and API
agent = ClaudeAgent(agent_settings)

# Enhance the agent's system prompt
original_prompt = agent.system_prompt
agent._system_prompt = original_prompt + "\n\n" + claude_prompt_addition

# Store workspace context as agent attribute (not in state)
agent.workspace_context = agent_context

api = AgentAPI(agent)
app = api.app

if __name__ == "__main__":
    import uvicorn
    port = settings.get_agent_port(role)
    uvicorn.run(app, host="0.0.0.0", port=port)