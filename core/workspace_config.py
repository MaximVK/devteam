"""Workspace configuration management for multi-agent system"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
import json


class GitConfig(BaseModel):
    """Git configuration for workspace"""
    repository_url: str
    base_branch: str = "main-agents"
    user_name: str = "DevTeam Agents"
    user_email: str = "agents@devteam.local"


class TokenConfig(BaseModel):
    """API tokens and credentials"""
    anthropic_api_key: str
    github_token: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_channel_id: Optional[str] = None


class WorkspaceConfig(BaseModel):
    """Complete workspace configuration"""
    working_folder: Path
    git_config: GitConfig
    tokens: TokenConfig
    predefined_roles: List[str] = Field(
        default=["backend", "frontend", "database", "qa", "ba", "teamlead"]
    )
    active_agents: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator('working_folder', mode='before')
    def validate_path(cls, v):
        if isinstance(v, str):
            return Path(v)
        return v
    
    @property
    def maestro_path(self) -> Path:
        """Path to maestro (human) workspace"""
        return self.working_folder / "maestro"
    
    @property
    def config_file_path(self) -> Path:
        """Path to configuration file"""
        return self.working_folder / "workspace_config.json"
    
    def get_agent_workspace(self, role: str) -> Path:
        """Get workspace path for a specific agent role"""
        return self.working_folder / role
    
    def get_agent_repo_path(self, role: str) -> Path:
        """Get repository path for a specific agent"""
        return self.get_agent_workspace(role) / "devteam"
    
    def save(self) -> None:
        """Save configuration to file"""
        self.working_folder.mkdir(parents=True, exist_ok=True)
        
        config_data = self.model_dump()
        # Convert Path to string for JSON serialization
        config_data['working_folder'] = str(config_data['working_folder'])
        
        with open(self.config_file_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    @classmethod
    def load(cls, working_folder: Path) -> Optional['WorkspaceConfig']:
        """Load configuration from file"""
        config_file = working_folder / "workspace_config.json"
        if not config_file.exists():
            return None
        
        with open(config_file) as f:
            data = json.load(f)
        
        return cls(**data)
    
    def is_initialized(self) -> bool:
        """Check if workspace is properly initialized"""
        return (
            self.config_file_path.exists() and
            self.maestro_path.exists() and
            (self.maestro_path / ".git").exists()
        )