"""Project-level configuration for DevTeam projects"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json
import uuid
from .agent_config import AgentConfiguration


class Repository(BaseModel):
    """Repository configuration for a project"""
    url: str
    base_branch: str = "main-agents"
    default_branch: str = "main"


class GitConfig(BaseModel):
    """Git configuration for the project"""
    user_name: str
    user_email: str


class AgentInfo(BaseModel):
    """Information about an agent in the project"""
    role: str
    name: str
    status: str = "active"  # active, inactive, paused
    workspace: str
    current_branch: Optional[str] = None
    last_active: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def agent_id(self) -> str:
        """Generate a unique agent ID from role and name"""
        return f"{self.role}-{self.name.lower().replace(' ', '-')}"


class ProjectMetadata(BaseModel):
    """Project metadata"""
    tech_stack: List[str] = Field(default_factory=list)
    team_size: int = 0
    started_date: Optional[str] = None
    status: str = "active"  # active, archived, paused


class CustomRole(BaseModel):
    """Custom role definition"""
    description: str


class TelegramConfig(BaseModel):
    """Telegram configuration for the project"""
    bot_token: str = ""
    group_id: str = ""
    enabled: bool = False
    template: Optional[str] = None  # Path to template file


class ProjectConfig(BaseModel):
    """Project-level configuration"""
    project_id: str
    project_name: str
    folder_name: Optional[str] = None  # Custom folder name for this project
    description: str = ""
    repository: Repository
    git_config: Optional[GitConfig] = None  # If None, use global config
    active_agents: Dict[str, AgentInfo] = Field(default_factory=dict)
    agent_configurations: Dict[str, AgentConfiguration] = Field(default_factory=dict)
    project_metadata: ProjectMetadata = Field(default_factory=ProjectMetadata)
    custom_roles: Dict[str, CustomRole] = Field(default_factory=dict)
    project_tokens: Dict[str, Any] = Field(default_factory=dict)
    telegram_config: TelegramConfig = Field(default_factory=TelegramConfig)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @property
    def config_path(self) -> Path:
        """Get the path to the project configuration file"""
        # This will be set when loading/saving
        return getattr(self, '_config_path', Path.cwd() / "project.config.json")
    
    def set_config_path(self, path: Path) -> None:
        """Set the configuration file path"""
        self._config_path = path
    
    def save(self) -> None:
        """Save configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2, default=str)
    
    @classmethod
    def load(cls, project_path: Path) -> Optional['ProjectConfig']:
        """Load configuration from project directory"""
        config_path = project_path / "project.config.json"
        if not config_path.exists():
            return None
        
        try:
            with open(config_path) as f:
                data = json.load(f)
                # Convert datetime strings back to datetime objects
                for agent_id, agent_info in data.get("active_agents", {}).items():
                    if "last_active" in agent_info:
                        agent_info["last_active"] = datetime.fromisoformat(agent_info["last_active"])
                    if "created_at" in agent_info:
                        agent_info["created_at"] = datetime.fromisoformat(agent_info["created_at"])
                
                config = cls(**data)
                config.set_config_path(config_path)
                return config
        except Exception as e:
            print(f"Error loading project config: {e}")
            return None
    
    @classmethod
    def create(cls, 
               project_name: str,
               repository_url: str,
               description: str = "",
               folder_name: Optional[str] = None,
               base_branch: str = "main-agents",
               git_config: Optional[GitConfig] = None) -> 'ProjectConfig':
        """Create a new project configuration"""
        # Use folder_name as project_id, or derive from project name
        if not folder_name:
            folder_name = project_name.lower().replace(' ', '-')
        
        return cls(
            project_id=folder_name,
            project_name=project_name,
            folder_name=folder_name,
            description=description,
            repository=Repository(
                url=repository_url,
                base_branch=base_branch
            ),
            git_config=git_config,
            project_metadata=ProjectMetadata(
                started_date=datetime.now().date().isoformat(),
                status="active"
            )
        )
    
    def add_agent(self, role: str, name: str, workspace_path: str) -> str:
        """Add an agent to the project"""
        agent = AgentInfo(
            role=role,
            name=name,
            workspace=workspace_path
        )
        agent_id = agent.agent_id
        
        # Ensure unique agent ID
        if agent_id in self.active_agents:
            # Add a number suffix if needed
            counter = 1
            while f"{agent_id}-{counter}" in self.active_agents:
                counter += 1
            agent_id = f"{agent_id}-{counter}"
        
        self.active_agents[agent_id] = agent
        
        # Create default configuration for the agent
        if agent_id not in self.agent_configurations:
            self.agent_configurations[agent_id] = AgentConfiguration.get_default_for_role(
                agent_id, role
            )
        
        self.save()
        return agent_id
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the project"""
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]
            self.save()
            return True
        return False
    
    def update_agent_status(self, agent_id: str, status: str) -> None:
        """Update agent status"""
        if agent_id in self.active_agents:
            self.active_agents[agent_id].status = status
            self.active_agents[agent_id].last_active = datetime.now()
            self.save()
    
    def get_agent_by_role(self, role: str) -> Optional[AgentInfo]:
        """Get the first agent with a specific role"""
        for agent in self.active_agents.values():
            if agent.role == role:
                return agent
        return None
    
    def get_all_agents_by_role(self, role: str) -> List[AgentInfo]:
        """Get all agents with a specific role"""
        return [agent for agent in self.active_agents.values() if agent.role == role]
    
    def get_agent_workspace(self, agent_id: str) -> Path:
        """Get the workspace directory for an agent"""
        # Create agent workspace under project directory
        workspace_dir = self.config_path.parent / "workspaces" / agent_id
        workspace_dir.mkdir(parents=True, exist_ok=True)
        return workspace_dir
    
    def get_agent_configuration(self, agent_id: str) -> AgentConfiguration:
        """Get configuration for an agent"""
        if agent_id not in self.agent_configurations:
            # Create default configuration based on role
            agent_info = self.active_agents.get(agent_id)
            if agent_info:
                self.agent_configurations[agent_id] = AgentConfiguration.get_default_for_role(
                    agent_id, agent_info.role
                )
            else:
                # Fallback to basic configuration
                self.agent_configurations[agent_id] = AgentConfiguration(agent_id=agent_id)
        
        return self.agent_configurations[agent_id]
    
    def update_agent_configuration(self, agent_id: str, config: AgentConfiguration) -> None:
        """Update agent configuration"""
        self.agent_configurations[agent_id] = config
        self.save()