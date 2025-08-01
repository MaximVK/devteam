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
from core.git_helper import GitHelper
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
git_config = workspace_config.get("workspace", {}).get("git_config", {})
git_workflow = workspace_config.get("git_workflow", {})

agent_context = {
    "workspace_path": workspace_path,
    "capabilities": agent_config.get("capabilities", []),
    "file_patterns": agent_config.get("file_patterns", ["*"]),
    "git_config": git_config,
    "git_workflow": git_workflow
}

# Initialize git helper
git_helper = GitHelper(workspace_path, git_config)

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
- Create feature branches using pattern: {git_workflow.get('feature_branch_pattern', 'agent/{role}/{task_id}')}
- Always commit your changes with clear messages
- Push changes to origin automatically: {git_workflow.get('auto_push', True)}
- Create pull requests when tasks are complete: {git_workflow.get('create_pull_requests', True)}

### Working Directory:
Your primary working directory is: {workspace_path}

### Git Helper Commands Available:
You have access to a git_helper object with these methods:
- git_helper.create_feature_branch(agent_role, task_id, task_title) - Create a new branch for your work
- git_helper.commit_changes(task_title, description, agent_role, task_id) - Commit your changes
- git_helper.push_branch(branch_name) - Push branch to remote
- git_helper.get_current_branch() - Get current branch name
- git_helper.get_branch_status() - Get detailed git status
- git_helper.create_github_pr(branch_name, title, description, changes, test_plan, agent_role) - Create PR

### Important Note About File Access:
As an AI agent, you cannot directly access or modify files in the workspace. You can only:
1. Describe what changes need to be made
2. Provide code snippets and examples
3. Explain implementation approaches
4. Review and analyze code when provided to you

When a user asks you to make changes:
1. Ask them to show you the current code/files you need to work with
2. Analyze the code and provide specific changes
3. Give clear instructions on what to modify
4. Provide complete code snippets that can be copy-pasted

### Your Workspace Information:
- Your designated working directory is: {workspace_path}
- You can work with these file types: {', '.join(agent_config.get('file_patterns', ['*']))}
- Your role capabilities: {', '.join(agent_config.get('capabilities', []))}

### Git Workflow (Conceptual):
When you need to make changes, guide the user through:
1. Creating a feature branch: `git checkout -b agent/{role}/feature-name`
2. Making the necessary code changes
3. Committing with clear messages: `git commit -m "Description of changes"`
4. Pushing the branch: `git push -u origin branch-name`
5. Creating a pull request with detailed description

### How to Respond to Code Change Requests:
1. If you need to see existing code, ask: "Please show me the current [filename] so I can make the appropriate changes"
2. When providing changes, use clear markdown code blocks with the language specified
3. Explain what each change does and why it's necessary
4. Provide complete, working code that can be directly used
5. Include any necessary imports or dependencies

IMPORTANT: 
- Always ask to see the current code before suggesting changes
- Provide complete, working code snippets
- Explain your changes clearly
- Your working directory context is: {workspace_path}
"""

# Create agent and API
agent = ClaudeAgent(agent_settings)

# Enhance the agent's system prompt
original_prompt = agent.system_prompt
agent._system_prompt = original_prompt + "\n\n" + claude_prompt_addition

# Store workspace context and git helper as agent attributes
agent.workspace_context = agent_context
agent.git_helper = git_helper

api = AgentAPI(agent)
app = api.app

if __name__ == "__main__":
    import uvicorn
    port = settings.get_agent_port(role)
    uvicorn.run(app, host="0.0.0.0", port=port)