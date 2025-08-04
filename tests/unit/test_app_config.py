"""Tests for the application configuration module"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from core.app_config import (
    AppConfig, 
    TokenConfig, 
    GlobalSettings, 
    UIPreferences,
    ProjectInfo
)


class TestAppConfig:
    """Test cases for AppConfig"""
    
    def test_create_app_config(self):
        """Test creating a new app configuration"""
        home_dir = Path("/tmp/test-devteam")
        tokens = TokenConfig(
            anthropic_api_key="test-key",
            github_token="ghp-test"
        )
        
        config = AppConfig(
            home_directory=home_dir,
            tokens=tokens
        )
        
        assert config.version == "2.0.0"
        assert config.home_directory == home_dir
        assert config.tokens.anthropic_api_key == "test-key"
        assert len(config.predefined_roles) == 8
        assert "backend" in config.predefined_roles
    
    def test_config_paths(self):
        """Test configuration path properties"""
        home_dir = Path("/tmp/test-devteam")
        config = AppConfig(home_directory=home_dir)
        
        assert config.config_path == home_dir / "devteam.config.json"
        assert config.projects_directory == home_dir / "projects"
        assert config.system_templates_directory == home_dir / "system-templates"
    
    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading configuration"""
        home_dir = tmp_path / "devteam-home"
        tokens = TokenConfig(
            anthropic_api_key="test-key",
            github_token="ghp-test",
            telegram_bot_token="tg-test"
        )
        
        # Create and save config
        config = AppConfig(
            home_directory=home_dir,
            tokens=tokens,
            current_project="test-project"
        )
        config.save()
        
        # Load config
        loaded_config = AppConfig.load(home_dir)
        
        assert loaded_config is not None
        assert loaded_config.version == config.version
        assert loaded_config.current_project == "test-project"
        assert loaded_config.tokens.anthropic_api_key == "test-key"
        assert loaded_config.tokens.github_token == "ghp-test"
    
    def test_initialize_home(self, tmp_path):
        """Test initializing a new home directory"""
        home_dir = tmp_path / "devteam-home"
        tokens = TokenConfig(anthropic_api_key="test-key")
        
        config = AppConfig.initialize_home(home_dir, tokens)
        
        assert config.home_directory == home_dir
        assert config.tokens.anthropic_api_key == "test-key"
        assert (home_dir / "projects").exists()
        assert (home_dir / "system-templates").exists()
        assert (home_dir / "devteam.config.json").exists()
    
    def test_add_project(self, tmp_path):
        """Test adding a project to the registry"""
        home_dir = tmp_path / "devteam-home"
        config = AppConfig(home_directory=home_dir)
        
        config.add_project(
            "project-1",
            "Test Project",
            "projects/project-1"
        )
        
        assert "project-1" in config.projects
        assert config.projects["project-1"].name == "Test Project"
        assert config.projects["project-1"].path == "projects/project-1"
        assert isinstance(config.projects["project-1"].created_at, datetime)
    
    def test_update_project_access(self, tmp_path):
        """Test updating project access time"""
        home_dir = tmp_path / "devteam-home"
        config = AppConfig(home_directory=home_dir)
        
        config.add_project("project-1", "Test Project", "projects/project-1")
        original_time = config.projects["project-1"].last_accessed
        
        # Wait a bit and update access
        import time
        time.sleep(0.1)
        config.update_project_access("project-1")
        
        assert config.projects["project-1"].last_accessed > original_time
    
    def test_set_current_project(self, tmp_path):
        """Test setting the current project"""
        home_dir = tmp_path / "devteam-home"
        config = AppConfig(home_directory=home_dir)
        
        config.add_project("project-1", "Test Project", "projects/project-1")
        config.set_current_project("project-1")
        
        assert config.current_project == "project-1"
        
        # Should update access time
        assert config.projects["project-1"].last_accessed is not None
    
    def test_get_current_project_path(self, tmp_path):
        """Test getting the current project path"""
        home_dir = tmp_path / "devteam-home"
        config = AppConfig(home_directory=home_dir)
        
        # No current project
        assert config.get_current_project_path() is None
        
        # Add and set project
        config.add_project("project-1", "Test Project", "projects/project-1")
        config.set_current_project("project-1")
        
        expected_path = home_dir / "projects/project-1"
        assert config.get_current_project_path() == expected_path
    
    def test_global_settings_defaults(self):
        """Test global settings default values"""
        settings = GlobalSettings()
        
        assert settings.default_base_branch == "main-agents"
        assert settings.default_git_config["user_name"] == "DevTeam Agents"
        assert settings.default_git_config["user_email"] == "agents@devteam.local"
        assert settings.ui_preferences.theme == "light"
        assert settings.ui_preferences.sidebar_collapsed is False
    
    def test_json_serialization(self, tmp_path):
        """Test JSON serialization with datetime objects"""
        home_dir = tmp_path / "devteam-home"
        config = AppConfig(home_directory=home_dir)
        
        # Add project with datetime
        config.add_project("project-1", "Test Project", "projects/project-1")
        
        # Save and load
        config.save()
        loaded = AppConfig.load(home_dir)
        
        # Check datetime is properly serialized/deserialized
        assert isinstance(loaded.projects["project-1"].created_at, datetime)
        assert isinstance(loaded.projects["project-1"].last_accessed, datetime)
    
    def test_load_nonexistent_config(self, tmp_path):
        """Test loading from non-existent directory"""
        home_dir = tmp_path / "nonexistent"
        config = AppConfig.load(home_dir)
        
        assert config is None
    
    def test_load_corrupted_config(self, tmp_path):
        """Test loading corrupted configuration file"""
        home_dir = tmp_path / "devteam-home"
        home_dir.mkdir()
        
        # Write corrupted JSON
        config_file = home_dir / "devteam.config.json"
        config_file.write_text("{ invalid json }")
        
        config = AppConfig.load(home_dir)
        assert config is None