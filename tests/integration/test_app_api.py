"""Integration tests for application API endpoints"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from web.backend import app
from web.app_api import set_app_config, get_app_config, _agent_manager
from core.app_config import AppConfig, TokenConfig
from core.project_config import ProjectConfig
from core.agent_manager import AgentManager


class TestAppAPI:
    """Test cases for application API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and cleanup for each test"""
        # Clear global app config before each test
        set_app_config(None)
        # Also clear the global _agent_manager
        import web.app_api
        web.app_api._agent_manager = None
        yield
        # Cleanup after test
        set_app_config(None)
        web.app_api._agent_manager = None
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def temp_home(self):
        """Create temporary home directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_app_status_not_initialized(self, client):
        """Test app status when not initialized"""
        # Mock get_app_config to return None
        with patch('web.app_api.get_app_config', return_value=None):
            response = client.get("/api/app/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["initialized"] is False
        assert data["home_directory"] is None
        assert data["project_count"] == 0
    
    def test_app_status_initialized(self, client, temp_home):
        """Test app status when initialized"""
        # Initialize app config
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        set_app_config(config)
        
        response = client.get("/api/app/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["initialized"] is True
        assert data["home_directory"] == str(temp_home)
        assert data["current_project"] is None
    
    def test_initialize_app(self, client, temp_home):
        """Test initializing the application"""
        response = client.post("/api/app/initialize", json={
            "home_directory": str(temp_home),
            "anthropic_api_key": "test-key",
            "github_token": "ghp-test",
            "telegram_bot_token": "tg-test",
            "telegram_channel_id": "@test"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Application initialized successfully" in data["message"]
        
        # Check directories were created
        assert (temp_home / "projects").exists()
        assert (temp_home / "system-templates").exists()
        assert (temp_home / "devteam.config.json").exists()
        
        # Check global config is set
        config = get_app_config()
        assert config is not None
        assert config.tokens.anthropic_api_key == "test-key"
    
    def test_initialize_app_already_initialized(self, client, temp_home):
        """Test initializing when already initialized"""
        # First initialization
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        # Try to initialize again
        response = client.post("/api/app/initialize", json={
            "home_directory": str(temp_home),
            "anthropic_api_key": "new-key"
        })
        
        assert response.status_code == 400
        assert "already initialized" in response.json()["detail"]
    
    def test_get_app_configuration(self, client, temp_home):
        """Test getting app configuration"""
        # Initialize first
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        set_app_config(config)
        
        response = client.get("/api/app/config")
        
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["home_directory"] == str(temp_home)
        assert len(data["predefined_roles"]) == 8
        assert "backend" in data["predefined_roles"]
    
    def test_update_app_configuration(self, client, temp_home):
        """Test updating app configuration"""
        # Initialize first
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        set_app_config(config)
        
        response = client.put("/api/app/config", json={
            "predefined_roles": ["backend", "frontend", "custom"]
        })
        
        assert response.status_code == 200
        
        # Check config was updated
        updated_config = get_app_config()
        assert len(updated_config.predefined_roles) == 3
        assert "custom" in updated_config.predefined_roles
    
    @patch('subprocess.run')
    def test_create_project(self, mock_run, client, temp_home):
        """Test creating a new project"""
        # Mock git operations
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        # Initialize app first
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        set_app_config(config)
        
        response = client.post("/api/app/projects", json={
            "project_name": "Test Project",
            "repository_url": "https://github.com/test/repo.git",
            "description": "Test description",
            "base_branch": "main-agents",
            "override_git_config": False,
            "initial_agents": [
                {"role": "backend", "name": "Alex"},
                {"role": "frontend", "name": "Sarah"}
            ]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "project_id" in data
        
        # Check project was created with folder name
        folder_name = "test-project"  # Expected folder name from "Test Project"
        project_path = temp_home / "projects" / folder_name
        assert project_path.exists()
        assert (project_path / "project.config.json").exists()
    
    def test_list_projects(self, client, temp_home):
        """Test listing projects"""
        # Initialize app
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        # Add test projects
        project_ids = []
        for i in range(2):
            project_id = f"project-{i}"  # Now project_id equals folder_name
            project_ids.append(project_id)
            folder_name = f"project-{i}"
            project_path = temp_home / "projects" / folder_name
            project_path.mkdir(parents=True)
            
            proj_config = ProjectConfig.create(
                project_name=f"Project {i}",
                repository_url=f"https://github.com/test/repo{i}.git"
            )
            proj_config.set_config_path(project_path / "project.config.json")
            proj_config.save()
            
            config.add_project(project_id, f"Project {i}", f"projects/{folder_name}")
        
        config.set_current_project(project_ids[0])
        set_app_config(config)
        
        response = client.get("/api/app/projects")
        
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 2
        assert projects[0]["name"] == "Project 0"
        assert projects[0]["is_current"] is True
        assert projects[1]["is_current"] is False
    
    def test_get_project_details(self, client, temp_home):
        """Test getting project details"""
        # Setup project
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        project_id = "test-project"
        project_path = temp_home / "projects" / project_id
        project_path.mkdir(parents=True)
        
        proj_config = ProjectConfig.create(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git"
        )
        proj_config.folder_name = "test-project"  # Set folder name to match project_id
        proj_config.add_agent("backend", "Alex", "agents/backend-alex")
        proj_config.set_config_path(project_path / "project.config.json")
        proj_config.save()
        
        config.add_project(project_id, "Test Project", f"projects/{project_id}")
        set_app_config(config)
        
        response = client.get(f"/api/app/projects/{project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Test Project"
        assert data["agent_count"] == 1
        assert "backend-alex" in data["agents"]
    
    def test_switch_project(self, client, temp_home):
        """Test switching between projects"""
        # Setup projects
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        config.add_project("project-1", "Project 1", "projects/project-1")
        config.add_project("project-2", "Project 2", "projects/project-2")
        set_app_config(config)
        
        response = client.post("/api/app/projects/project-2/switch")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["current_project"] == "project-2"
        
        # Check config was updated
        assert config.current_project == "project-2"
    
    def test_archive_project(self, client, temp_home):
        """Test archiving a project"""
        # Setup project
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        project_id = "test-project"
        project_path = temp_home / "projects" / project_id
        project_path.mkdir(parents=True)
        
        proj_config = ProjectConfig.create(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git"
        )
        proj_config.set_config_path(project_path / "project.config.json")
        proj_config.save()
        
        config.add_project(project_id, "Test Project", f"projects/{project_id}")
        config.set_current_project(project_id)
        set_app_config(config)
        
        response = client.delete(f"/api/app/projects/{project_id}")
        
        assert response.status_code == 200
        
        # Check project was archived
        archived_config = ProjectConfig.load(project_path)
        assert archived_config.project_metadata.status == "archived"
        assert config.current_project is None
    
    @patch('subprocess.run')
    def test_create_agent_endpoint(self, mock_run, client, temp_home):
        """Test creating an agent via API"""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        # Setup project
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        project_id = "test-project"
        project_path = temp_home / "projects" / project_id
        project_path.mkdir(parents=True)
        (project_path / "maestro").mkdir()
        
        proj_config = ProjectConfig.create(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git"
        )
        proj_config.set_config_path(project_path / "project.config.json")
        proj_config.save()
        
        config.add_project(project_id, "Test Project", f"projects/{project_id}")
        set_app_config(config)
        
        response = client.post(f"/api/app/projects/{project_id}/agents", json={
            "role": "backend",
            "name": "Alex"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "agent_id" in data
    
    def test_remove_agent_endpoint(self, client, temp_home):
        """Test removing an agent via API"""
        # Setup project with agent
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        project_id = "test-project"
        project_path = temp_home / "projects" / project_id
        project_path.mkdir(parents=True)
        
        proj_config = ProjectConfig.create(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git"
        )
        agent_id = proj_config.add_agent("backend", "Alex", "agents/backend-alex")
        proj_config.set_config_path(project_path / "project.config.json")
        proj_config.save()
        
        # Create agent workspace
        agent_workspace = project_path / "agents" / "backend-alex"
        agent_workspace.mkdir(parents=True)
        
        config.add_project(project_id, "Test Project", f"projects/{project_id}")
        set_app_config(config)
        
        response = client.delete(f"/api/app/projects/{project_id}/agents/{agent_id}")
        
        assert response.status_code == 200
        
        # Check agent was removed
        updated_config = ProjectConfig.load(project_path)
        assert agent_id not in updated_config.active_agents
    
    def test_error_handling_no_app_initialized(self, client):
        """Test error handling when app is not initialized"""
        # Mock get_app_config to return None for all endpoints
        with patch('web.app_api.get_app_config', return_value=None):
            endpoints = [
                ("/api/app/config", "get"),
                ("/api/app/config", "put"),
                ("/api/app/projects", "get"),
                ("/api/app/projects", "post"),
                ("/api/app/projects/test/switch", "post"),
            ]
            
            for endpoint, method in endpoints:
                if method == "get":
                    response = client.get(endpoint)
                elif method == "post":
                    response = client.post(endpoint, json={})
                elif method == "put":
                    response = client.put(endpoint, json={})
                
                # Some endpoints might return 422 (validation error) instead of 400
                # when required fields are missing
                if response.status_code == 422:
                    # That's fine for POST/PUT endpoints that require specific data
                    continue
                assert response.status_code == 400, f"Expected 400 for {endpoint}, got {response.status_code}"
            assert "not initialized" in response.json()["detail"]
    
    @patch('core.agent_manager.AgentManager.start_project_agents')
    def test_start_project_agents(self, mock_start, client, temp_home):
        """Test starting agents for a project"""
        # Setup
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        config.add_project("test-project", "Test Project", "projects/test-project")
        set_app_config(config)
        
        # Mock agent manager response
        mock_start.return_value = {
            "backend-alex": "started",
            "frontend-sarah": "started"
        }
        
        response = client.post("/api/app/projects/test-project/agents/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "results" in data
        assert data["results"]["backend-alex"] == "started"
        mock_start.assert_called_once_with("test-project")
    
    @patch('core.agent_manager.AgentManager.stop_project_agents')
    def test_stop_project_agents(self, mock_stop, client, temp_home):
        """Test stopping agents for a project"""
        # Setup
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        config.add_project("test-project", "Test Project", "projects/test-project")
        set_app_config(config)
        
        # Mock agent manager response
        mock_stop.return_value = {
            "backend-alex": "stopped",
            "frontend-sarah": "stopped"
        }
        
        response = client.post("/api/app/projects/test-project/agents/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "results" in data
        mock_stop.assert_called_once_with("test-project")
    
    @patch('core.agent_manager.AgentManager.get_project_status')
    def test_get_project_agents_status(self, mock_status, client, temp_home):
        """Test getting agent status for a project"""
        # Setup
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        config.add_project("test-project", "Test Project", "projects/test-project")
        set_app_config(config)
        
        # Mock agent manager response
        mock_status.return_value = {
            "backend-alex": {"running": True, "pid": 1234},
            "frontend-sarah": {"running": False}
        }
        
        response = client.get("/api/app/projects/test-project/agents/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "test-project"
        assert data["agents"]["backend-alex"]["running"] is True
        assert data["agents"]["backend-alex"]["pid"] == 1234
        mock_status.assert_called_once_with("test-project")
    
    @patch('core.agent_manager.AgentManager.get_all_projects_status')
    def test_get_all_agents_status(self, mock_all_status, client, temp_home):
        """Test getting agent status for all projects"""
        # Setup
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        set_app_config(config)
        
        # Mock agent manager response
        mock_all_status.return_value = {
            "project1": {
                "agents": {"agent1": {"running": True}},
                "total_agents": 1,
                "running_agents": 1
            },
            "project2": {
                "agents": {},
                "total_agents": 0,
                "running_agents": 0
            }
        }
        
        response = client.get("/api/app/agents/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert data["projects"]["project1"]["running_agents"] == 1
        assert data["projects"]["project2"]["running_agents"] == 0
        mock_all_status.assert_called_once()
    
    def test_update_telegram_config(self, client, temp_home):
        """Test updating Telegram configuration for a project"""
        # Setup project
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        project_id = "test-project"
        project_path = temp_home / "projects" / project_id
        project_path.mkdir(parents=True)
        
        proj_config = ProjectConfig.create(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git"
        )
        proj_config.set_config_path(project_path / "project.config.json")
        proj_config.save()
        
        config.add_project(project_id, "Test Project", f"projects/{project_id}")
        set_app_config(config)
        
        response = client.put(f"/api/app/projects/{project_id}/telegram", json={
            "bot_token": "test-bot-token",
            "group_id": "test-group",
            "enabled": True
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Check config was updated
        updated_config = ProjectConfig.load(project_path)
        assert updated_config.telegram_config.bot_token == "test-bot-token"
        assert updated_config.telegram_config.group_id == "test-group"
        assert updated_config.telegram_config.enabled is True
    
    def test_project_details_includes_telegram(self, client, temp_home):
        """Test that project details include telegram config"""
        # Setup project with telegram config
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        project_id = "test-project"
        project_path = temp_home / "projects" / project_id
        project_path.mkdir(parents=True)
        
        proj_config = ProjectConfig.create(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git"
        )
        proj_config.telegram_config.bot_token = "test-token"
        proj_config.telegram_config.enabled = True
        proj_config.set_config_path(project_path / "project.config.json")
        proj_config.save()
        
        config.add_project(project_id, "Test Project", f"projects/{project_id}")
        set_app_config(config)
        
        response = client.get(f"/api/app/projects/{project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "telegram_config" in data
        assert data["telegram_config"]["bot_token"] == "test-token"
        assert data["telegram_config"]["enabled"] is True
    
    def test_start_agents_project_not_found(self, client, temp_home):
        """Test starting agents for non-existent project"""
        # Setup
        config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        set_app_config(config)
        
        response = client.post("/api/app/projects/nonexistent/agents/start")
        
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]
    
    def test_agent_manager_not_available(self, client):
        """Test agent endpoints when agent manager is not available"""
        # Clear agent manager
        import web.app_api
        web.app_api._agent_manager = None
        
        # Set minimal config without agent manager
        config = Mock()
        config.projects = {"test": Mock()}
        config.home_directory = Path("/tmp/test")  # Provide a Path object
        set_app_config(config)
        
        # Mock get_agent_manager to return None
        with patch('web.app_api.get_agent_manager', return_value=None):
            response = client.post("/api/app/projects/test/agents/start")
        
        assert response.status_code == 500
        assert "Agent manager not available" in response.json()["detail"]