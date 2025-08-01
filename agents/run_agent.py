#!/usr/bin/env python3
"""Run a single agent with the specified role"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.api import AgentAPI
from core.claude_agent import ClaudeAgent, AgentSettings, AgentRole
from config.settings import settings

# Get agent role from environment
role = os.environ.get("AGENT_ROLE", "backend").lower()

# Create agent settings - pass only required fields
agent_settings = AgentSettings(
    role=AgentRole[role.upper()],
    anthropic_api_key=settings.anthropic_api_key,
    model=settings.default_model,
    port=settings.get_agent_port(role),
    telegram_channel_id=settings.telegram_channel_id,
    github_repo=settings.github_repo,
    # Disable env loading to avoid conflicts
    _env_file=None
)

# Create agent and API
agent = ClaudeAgent(agent_settings)
api = AgentAPI(agent)
app = api.app

if __name__ == "__main__":
    import uvicorn
    port = settings.get_agent_port(role)
    uvicorn.run(app, host="0.0.0.0", port=port)