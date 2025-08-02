#!/usr/bin/env python3
"""Run an agent using the new workspace structure"""

import os
import sys
import argparse
from pathlib import Path
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.api import AgentAPI
from core.claude_agent import ClaudeAgent, AgentSettings, AgentRole
from core.workspace_config import WorkspaceConfig
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run an agent with workspace configuration")
    parser.add_argument("role", help="Agent role (backend, frontend, database, qa, ba, teamlead)")
    parser.add_argument("--workspace", help="Workspace directory", 
                       default=str(Path.home() / "devteam-workspace"))
    args = parser.parse_args()
    
    role = args.role.lower()
    
    # Load workspace configuration
    config = WorkspaceConfig.load(Path(args.workspace))
    if not config:
        logger.error(f"No workspace configuration found at {args.workspace}")
        logger.error("Please initialize the workspace first using the web interface")
        sys.exit(1)
    
    # Check if agent workspace exists
    agent_repo_path = config.get_agent_repo_path(role)
    if not agent_repo_path.exists():
        logger.error(f"Agent workspace not found at {agent_repo_path}")
        logger.error(f"Please create the {role} agent workspace first")
        sys.exit(1)
    
    # Check for CLAUDE.md
    claude_md_path = agent_repo_path / "CLAUDE.md"
    if not claude_md_path.exists():
        logger.error(f"CLAUDE.md not found at {claude_md_path}")
        sys.exit(1)
    
    # Load CLAUDE.md content
    claude_content = claude_md_path.read_text()
    logger.info(f"Loaded CLAUDE.md for {role} agent")
    
    # Create agent settings
    agent_settings = AgentSettings(
        role=AgentRole[role.upper()],
        anthropic_api_key=config.tokens.anthropic_api_key,
        model=settings.default_model,
        port=settings.get_agent_port(role),
        telegram_channel_id=config.tokens.telegram_channel_id,
        github_repo=config.git_config.repository_url,
        claude_file="",  # We'll set the prompt directly
        _env_file=None
    )
    
    # Add workspace context to prompt
    workspace_context = f"""
## Your Workspace Configuration

- Working Directory: {agent_repo_path}
- Repository: {config.git_config.repository_url}
- Base Branch: {config.git_config.base_branch}
- Your Role: {role}

## Important Notes

1. You are working in your own isolated workspace
2. Create feature branches from {config.git_config.base_branch}
3. Your changes are isolated until you push them
4. Coordinate with other agents through GitHub PRs and Telegram

## Git Configuration

Your git is configured with:
- User: {config.git_config.user_name}
- Email: {config.git_config.user_email}
"""
    
    # Create agent
    agent = ClaudeAgent(agent_settings)
    
    # Set the complete system prompt
    agent._system_prompt = claude_content + "\n\n" + workspace_context
    
    # Store workspace info
    agent.workspace_path = agent_repo_path
    agent.workspace_config = config
    
    # Create API
    api = AgentAPI(agent)
    app = api.app
    
    logger.info(f"🤖 Starting {role} agent with workspace: {agent_repo_path}")
    logger.info(f"📡 Agent API will be available at: http://localhost:{agent_settings.port}")
    
    # Run the agent
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=agent_settings.port)


if __name__ == "__main__":
    main()