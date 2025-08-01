"""Central configuration management for DevTeam"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main configuration settings for DevTeam system"""
    
    # Anthropic API
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    default_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Default Claude model"
    )
    
    # Telegram Configuration (Optional)
    telegram_bot_token: Optional[str] = Field(
        default=None,
        description="Telegram bot token"
    )
    telegram_channel_id: Optional[str] = Field(
        default=None,
        description="Telegram channel/group ID"
    )
    
    # GitHub Configuration (Optional)
    github_token: Optional[str] = Field(
        default=None,
        description="GitHub personal access token"
    )
    github_repo: Optional[str] = Field(
        default=None,
        description="GitHub repository (owner/repo)"
    )
    github_organization: Optional[str] = Field(
        default=None,
        description="GitHub organization name"
    )
    
    # Agent Ports
    backend_port: int = Field(default=8301, description="Backend agent port")
    frontend_port: int = Field(default=8302, description="Frontend agent port")
    database_port: int = Field(default=8303, description="Database agent port")
    qa_port: int = Field(default=8304, description="QA agent port")
    ba_port: int = Field(default=8305, description="BA agent port")
    teamlead_port: int = Field(default=8306, description="Team lead agent port")
    
    # Web Dashboard
    web_backend_port: int = Field(default=8000, description="Web backend port")
    web_frontend_port: int = Field(default=3000, description="Web frontend port")
    
    # Database Configuration (Optional)
    database_url: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection URL"
    )
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    # Development/Testing
    test_mode: bool = Field(default=False, description="Enable test mode")
    mock_anthropic: bool = Field(default=False, description="Mock Anthropic API")
    mock_telegram: bool = Field(default=False, description="Mock Telegram API")
    mock_github: bool = Field(default=False, description="Mock GitHub API")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def github_repo_name(self) -> Optional[str]:
        """Extract repository name from full repo path"""
        if self.github_repo:
            return self.github_repo.split("/")[-1]
        return None
    
    @property
    def github_owner(self) -> Optional[str]:
        """Extract owner from full repo path"""
        if self.github_repo and "/" in self.github_repo:
            return self.github_repo.split("/")[0]
        return None
    
    def get_agent_port(self, role: str) -> int:
        """Get port for specific agent role"""
        port_map = {
            "backend": self.backend_port,
            "frontend": self.frontend_port,
            "database": self.database_port,
            "qa": self.qa_port,
            "ba": self.ba_port,
            "teamlead": self.teamlead_port,
        }
        return port_map.get(role, 8300)
    
    def is_telegram_configured(self) -> bool:
        """Check if Telegram is properly configured"""
        return bool(self.telegram_bot_token and self.telegram_channel_id)
    
    def is_github_configured(self) -> bool:
        """Check if GitHub is properly configured"""
        return bool(self.github_token and self.github_repo)


# Global settings instance
settings = Settings()


# For testing: load from a test env file
def load_test_settings(env_file: str = ".env.test") -> Settings:
    """Load settings from a test environment file"""
    return Settings(_env_file=env_file)