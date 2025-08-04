"""Tests for the project configuration module"""

import pytest
import json
from pathlib import Path
from datetime import datetime

from core.project_config import (
    ProjectConfig,
    Repository,
    GitConfig,
    AgentInfo,
    ProjectMetadata,
    CustomRole
)


class TestProjectConfig:
    """Test cases for ProjectConfig"""
    
    def test_create_project_config(self):
        """Test creating a new project configuration"""
        config = ProjectConfig.create(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git",
            description="Test description",
            base_branch="main-agents"
        )
        
        assert config.project_name == "Test Project"
        assert config.description == "Test description"
        assert config.repository.url == "https://github.com/test/repo.git"
        assert config.repository.base_branch == "main-agents"
        assert config.project_metadata.status == "active"
        assert config.project_id == "test-project"  # Should be derived from project name
        assert config.folder_name == "test-project"  # Should match project_id
    
    def test_agent_info(self):
        """Test AgentInfo model"""
        agent = AgentInfo(
            role="backend",
            name="Alex",
            workspace="agents/backend-alex"
        )
        
        assert agent.role == "backend"
        assert agent.name == "Alex"
        assert agent.status == "active"
        assert agent.workspace == "agents/backend-alex"
        assert agent.agent_id == "backend-alex"
        assert isinstance(agent.created_at, datetime)
    
    def test_agent_id_generation(self):
        """Test agent ID generation with spaces and special characters"""
        agent = AgentInfo(
            role="frontend",
            name="Sarah Johnson",
            workspace="agents/frontend-sarah-johnson"
        )
        
        assert agent.agent_id == "frontend-sarah-johnson"
    
    def test_add_agent(self):
        """Test adding agents to a project"""
        config = ProjectConfig(
            project_id="test-project",
            project_name="Test Project",
            repository=Repository(url="https://github.com/test/repo.git")
        )
        
        agent_id = config.add_agent("backend", "Alex", "agents/backend-alex")
        
        assert agent_id == "backend-alex"
        assert agent_id in config.active_agents
        assert config.active_agents[agent_id].role == "backend"
        assert config.active_agents[agent_id].name == "Alex"
    
    def test_add_duplicate_agent(self):
        """Test adding agents with duplicate names"""
        config = ProjectConfig(
            project_id="test-project",
            project_name="Test Project",
            repository=Repository(url="https://github.com/test/repo.git")
        )
        
        # Add first Alex
        agent_id1 = config.add_agent("backend", "Alex", "agents/backend-alex")
        # Add second Alex
        agent_id2 = config.add_agent("backend", "Alex", "agents/backend-alex-1")
        
        assert agent_id1 == "backend-alex"
        assert agent_id2 == "backend-alex-1"
        assert len(config.active_agents) == 2
    
    def test_remove_agent(self):
        """Test removing an agent"""
        config = ProjectConfig(
            project_id="test-project",
            project_name="Test Project",
            repository=Repository(url="https://github.com/test/repo.git")
        )
        
        agent_id = config.add_agent("backend", "Alex", "agents/backend-alex")
        assert agent_id in config.active_agents
        
        result = config.remove_agent(agent_id)
        assert result is True
        assert agent_id not in config.active_agents
        
        # Try removing non-existent agent
        result = config.remove_agent("non-existent")
        assert result is False
    
    def test_update_agent_status(self):
        """Test updating agent status"""
        config = ProjectConfig(
            project_id="test-project",
            project_name="Test Project",
            repository=Repository(url="https://github.com/test/repo.git")
        )
        
        agent_id = config.add_agent("backend", "Alex", "agents/backend-alex")
        original_time = config.active_agents[agent_id].last_active
        
        # Update status
        import time
        time.sleep(0.1)
        config.update_agent_status(agent_id, "paused")
        
        assert config.active_agents[agent_id].status == "paused"
        assert config.active_agents[agent_id].last_active > original_time
    
    def test_get_agent_by_role(self):
        """Test getting agents by role"""
        config = ProjectConfig(
            project_id="test-project",
            project_name="Test Project",
            repository=Repository(url="https://github.com/test/repo.git")
        )
        
        config.add_agent("backend", "Alex", "agents/backend-alex")
        config.add_agent("frontend", "Sarah", "agents/frontend-sarah")
        
        backend_agent = config.get_agent_by_role("backend")
        assert backend_agent is not None
        assert backend_agent.name == "Alex"
        
        # Non-existent role
        db_agent = config.get_agent_by_role("database")
        assert db_agent is None
    
    def test_get_all_agents_by_role(self):
        """Test getting all agents with a specific role"""
        config = ProjectConfig(
            project_id="test-project",
            project_name="Test Project",
            repository=Repository(url="https://github.com/test/repo.git")
        )
        
        config.add_agent("backend", "Alex", "agents/backend-alex")
        config.add_agent("backend", "Blake", "agents/backend-blake")
        config.add_agent("frontend", "Sarah", "agents/frontend-sarah")
        
        backend_agents = config.get_all_agents_by_role("backend")
        assert len(backend_agents) == 2
        assert all(agent.role == "backend" for agent in backend_agents)
        
        frontend_agents = config.get_all_agents_by_role("frontend")
        assert len(frontend_agents) == 1
    
    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading project configuration"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        # Create config with agents
        config = ProjectConfig.create(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git",
            git_config=GitConfig(
                user_name="Test User",
                user_email="test@example.com"
            )
        )
        
        config.add_agent("backend", "Alex", "agents/backend-alex")
        config.add_agent("frontend", "Sarah", "agents/frontend-sarah")
        
        # Add custom role
        config.custom_roles["api-specialist"] = CustomRole(
            description="API specialist",
            template="templates/api-specialist.md"
        )
        
        # Save
        config.set_config_path(project_dir / "project.config.json")
        config.save()
        
        # Load
        loaded = ProjectConfig.load(project_dir)
        
        assert loaded is not None
        assert loaded.project_name == "Test Project"
        assert loaded.git_config.user_name == "Test User"
        assert len(loaded.active_agents) == 2
        assert "backend-alex" in loaded.active_agents
        assert "api-specialist" in loaded.custom_roles
    
    def test_project_metadata(self):
        """Test project metadata"""
        metadata = ProjectMetadata(
            tech_stack=["Python", "FastAPI", "React"],
            team_size=5,
            started_date="2025-01-15",
            status="active"
        )
        
        assert len(metadata.tech_stack) == 3
        assert metadata.team_size == 5
        assert metadata.started_date == "2025-01-15"
        assert metadata.status == "active"
    
    def test_repository_config(self):
        """Test repository configuration"""
        repo = Repository(
            url="https://github.com/test/repo.git",
            base_branch="develop",
            default_branch="main"
        )
        
        assert repo.url == "https://github.com/test/repo.git"
        assert repo.base_branch == "develop"
        assert repo.default_branch == "main"
    
    def test_project_tokens(self):
        """Test project-specific tokens"""
        config = ProjectConfig(
            project_id="test-project",
            project_name="Test Project",
            repository=Repository(url="https://github.com/test/repo.git")
        )
        
        config.project_tokens["database_url"] = "postgresql://localhost/test"
        config.project_tokens["api_keys"] = {
            "stripe": "sk_test_123",
            "sendgrid": "SG.123"
        }
        
        assert config.project_tokens["database_url"] == "postgresql://localhost/test"
        assert config.project_tokens["api_keys"]["stripe"] == "sk_test_123"
    
    def test_load_nonexistent_config(self, tmp_path):
        """Test loading from non-existent directory"""
        project_dir = tmp_path / "nonexistent"
        config = ProjectConfig.load(project_dir)
        
        assert config is None
    
    def test_datetime_serialization(self, tmp_path):
        """Test datetime serialization in JSON"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        config = ProjectConfig(
            project_id="test-project",
            project_name="Test Project",
            repository=Repository(url="https://github.com/test/repo.git")
        )
        
        # Add agent with datetime fields
        config.add_agent("backend", "Alex", "agents/backend-alex")
        
        # Save and load
        config.set_config_path(project_dir / "project.config.json")
        config.save()
        
        loaded = ProjectConfig.load(project_dir)
        
        # Check datetime fields are properly restored
        agent = loaded.active_agents["backend-alex"]
        assert isinstance(agent.created_at, datetime)
        assert isinstance(agent.last_active, datetime)