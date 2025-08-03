"""Agent configuration management"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from pathlib import Path
import json


class AgentPermissions(BaseModel):
    """Permissions and restrictions for an agent"""
    
    # File system access
    allowed_paths: List[str] = Field(
        default_factory=list,
        description="Additional paths the agent can access outside its workspace"
    )
    
    # Command execution
    allowed_commands: List[str] = Field(
        default_factory=lambda: [
            'git', 'ls', 'cat', 'grep', 'find', 'npm', 'yarn', 'python', 'node',
            'mkdir', 'touch', 'rm', 'cp', 'mv', 'pytest', 'jest', 'vitest'
        ],
        description="Commands the agent is allowed to execute"
    )
    
    # Additional permissions
    can_access_internet: bool = Field(
        default=False,
        description="Whether the agent can make HTTP requests"
    )
    
    can_install_packages: bool = Field(
        default=False,
        description="Whether the agent can install npm/pip packages"
    )
    
    can_modify_git_config: bool = Field(
        default=False,
        description="Whether the agent can modify git configuration"
    )
    
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum file size the agent can create/modify in MB"
    )
    
    max_command_output_lines: int = Field(
        default=1000,
        description="Maximum lines of output from command execution"
    )


class AgentSettings(BaseModel):
    """Configuration settings for an agent"""
    
    # Basic settings
    enabled: bool = Field(default=True, description="Whether the agent is enabled")
    
    auto_start: bool = Field(
        default=False,
        description="Whether to automatically start the agent with the project"
    )
    
    # Claude API settings
    model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Claude model to use"
    )
    
    max_tokens: int = Field(
        default=4096,
        description="Maximum tokens in Claude response"
    )
    
    temperature: float = Field(
        default=0.7,
        description="Temperature for Claude responses (0-1)"
    )
    
    # System prompt customization
    system_prompt_additions: str = Field(
        default="",
        description="Additional instructions to add to the system prompt"
    )
    
    # Resource limits
    memory_limit_mb: int = Field(
        default=512,
        description="Memory limit for the agent process in MB"
    )
    
    cpu_limit_percent: int = Field(
        default=50,
        description="CPU usage limit as percentage"
    )


class AgentConfiguration(BaseModel):
    """Complete configuration for an agent"""
    
    agent_id: str
    permissions: AgentPermissions = Field(default_factory=AgentPermissions)
    settings: AgentSettings = Field(default_factory=AgentSettings)
    
    # Custom tools
    custom_tools: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Custom tool configurations"
    )
    
    # Environment variables
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set for the agent"
    )
    
    @classmethod
    def load(cls, config_path: Path) -> Optional["AgentConfiguration"]:
        """Load configuration from file"""
        if not config_path.exists():
            return None
        
        try:
            with open(config_path) as f:
                data = json.load(f)
            return cls.model_validate(data)
        except Exception:
            return None
    
    def save(self, config_path: Path) -> None:
        """Save configuration to file"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2)
    
    @classmethod
    def get_default_for_role(cls, agent_id: str, role: str) -> "AgentConfiguration":
        """Get default configuration based on agent role"""
        config = cls(agent_id=agent_id)
        
        if role == "frontend":
            # Frontend agents need access to the main UI codebase
            config.permissions.allowed_paths = [
                "/Users/maxim/dev/experimental/devteam/web/frontend",
                "/Users/maxim/dev/experimental/devteam/web/frontend/src",
                "/Users/maxim/dev/experimental/devteam/web/frontend/public"
            ]
            config.permissions.allowed_commands.extend([
                "npm", "yarn", "vite", "eslint", "prettier"
            ])
            
        elif role == "backend":
            # Backend agents need access to API code
            config.permissions.allowed_paths = [
                "/Users/maxim/dev/experimental/devteam/web/backend",
                "/Users/maxim/dev/experimental/devteam/core",
                "/Users/maxim/dev/experimental/devteam/agents"
            ]
            config.permissions.allowed_commands.extend([
                "poetry", "uvicorn", "pytest", "black", "ruff"
            ])
            
        elif role == "qa":
            # QA agents need broader access for testing
            config.permissions.allowed_paths = [
                "/Users/maxim/dev/experimental/devteam/web",
                "/Users/maxim/dev/experimental/devteam/tests"
            ]
            config.permissions.allowed_commands.extend([
                "pytest", "coverage", "playwright", "cypress"
            ])
            
        elif role == "devops":
            # DevOps agents need access to configuration and scripts
            config.permissions.allowed_paths = [
                "/Users/maxim/dev/experimental/devteam",
                "/Users/maxim/dev/experimental/devteam/scripts",
                "/Users/maxim/dev/experimental/devteam/.github"
            ]
            config.permissions.allowed_commands.extend([
                "docker", "docker-compose", "kubectl", "terraform"
            ])
            config.permissions.can_modify_git_config = True
        
        return config