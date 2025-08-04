"""Application-level configuration for multi-project DevTeam system"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json
import os


class UIPreferences(BaseModel):
    """UI preferences for the application"""
    theme: str = "light"
    sidebar_collapsed: bool = False
    default_view: str = "dashboard"


class GlobalSettings(BaseModel):
    """Global settings that apply to all projects"""
    default_base_branch: str = "main-agents"
    default_git_config: Dict[str, str] = Field(default_factory=lambda: {
        "user_name": "DevTeam Agents",
        "user_email": "agents@devteam.local"
    })
    ui_preferences: UIPreferences = Field(default_factory=UIPreferences)


class TokenConfig(BaseModel):
    """Global token configuration"""
    anthropic_api_key: Optional[str] = None
    github_token: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_channel_id: Optional[str] = None


class ProjectInfo(BaseModel):
    """Basic project information for the registry"""
    name: str
    path: str
    created_at: datetime
    last_accessed: datetime


class AppConfig(BaseModel):
    """Application-level configuration"""
    version: str = "2.0.0"
    home_directory: Path
    primary_folder: Optional[Path] = None  # Primary folder for all projects
    current_project: Optional[str] = None
    global_settings: GlobalSettings = Field(default_factory=GlobalSettings)
    tokens: TokenConfig = Field(default_factory=TokenConfig)
    predefined_roles: List[str] = Field(default_factory=lambda: [
        "backend", "frontend", "database", "qa", 
        "ba", "teamlead", "devops", "security"
    ])
    projects: Dict[str, ProjectInfo] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat()
        }
    
    @property
    def config_path(self) -> Path:
        """Get the path to the configuration file"""
        return self.home_directory / "devteam.config.json"
    
    @property
    def projects_directory(self) -> Path:
        """Get the projects directory path"""
        if self.primary_folder:
            return Path(self.primary_folder) / "projects"
        return self.home_directory / "projects"
    
    @property
    def system_templates_directory(self) -> Path:
        """Get the system templates directory path"""
        return self.home_directory / "system-templates"
    
    def save(self) -> None:
        """Save configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2, default=str)
    
    @classmethod
    def load(cls, home_directory: Path) -> Optional['AppConfig']:
        """Load configuration from home directory"""
        config_path = home_directory / "devteam.config.json"
        if not config_path.exists():
            return None
        
        try:
            with open(config_path) as f:
                data = json.load(f)
                # Convert datetime strings back to datetime objects
                for project_id, project_info in data.get("projects", {}).items():
                    if "created_at" in project_info:
                        project_info["created_at"] = datetime.fromisoformat(project_info["created_at"])
                    if "last_accessed" in project_info:
                        project_info["last_accessed"] = datetime.fromisoformat(project_info["last_accessed"])
                return cls(**data)
        except Exception as e:
            print(f"Error loading app config: {e}")
            return None
    
    @classmethod
    def initialize_home(cls, home_directory: Path, tokens: TokenConfig) -> 'AppConfig':
        """Initialize a new home directory with default configuration"""
        config = cls(
            home_directory=home_directory,
            tokens=tokens
        )
        
        # Create directory structure
        config.projects_directory.mkdir(parents=True, exist_ok=True)
        config.system_templates_directory.mkdir(parents=True, exist_ok=True)
        
        # Save initial configuration
        config.save()
        
        return config
    
    def add_project(self, project_id: str, project_name: str, project_path: str) -> None:
        """Add a project to the registry"""
        self.projects[project_id] = ProjectInfo(
            name=project_name,
            path=project_path,
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )
        self.save()
    
    def update_project_access(self, project_id: str) -> None:
        """Update the last accessed time for a project"""
        if project_id in self.projects:
            self.projects[project_id].last_accessed = datetime.now()
            self.save()
    
    def set_current_project(self, project_id: str) -> None:
        """Set the current active project"""
        if project_id in self.projects:
            self.current_project = project_id
            self.update_project_access(project_id)
            self.save()
    
    def get_current_project_path(self) -> Optional[Path]:
        """Get the path to the current project"""
        if self.current_project and self.current_project in self.projects:
            return self.home_directory / self.projects[self.current_project].path
        return None