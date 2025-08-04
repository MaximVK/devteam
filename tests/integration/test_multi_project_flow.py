"""Integration tests for multi-project workflow"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil
import json

from core.app_config import AppConfig, TokenConfig
from core.project_config import ProjectConfig, GitConfig
from core.project_manager import ProjectManager
from core.template_manager import TemplateManager
from core.agent_manager import AgentManager


class TestMultiProjectFlow:
    """End-to-end tests for multi-project functionality"""
    
    @pytest.fixture
    def temp_home(self):
        """Create temporary home directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @patch('subprocess.run')
    def test_complete_project_lifecycle(self, mock_run, temp_home):
        """Test complete project lifecycle from initialization to agent creation"""
        # Mock git operations
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        # Step 1: Initialize application
        tokens = TokenConfig(
            anthropic_api_key="test-key",
            github_token="ghp-test"
        )
        app_config = AppConfig.initialize_home(temp_home, tokens)
        
        assert app_config.home_directory == temp_home
        assert (temp_home / "devteam.config.json").exists()
        assert (temp_home / "projects").exists()
        assert (temp_home / "system-templates").exists()
        
        # Step 2: Create project manager
        project_manager = ProjectManager(app_config)
        
        # Step 3: Create first project
        project1_id = project_manager.create_project(
            project_name="E-commerce Platform",
            repository_url="https://github.com/company/ecommerce.git",
            description="Multi-vendor e-commerce platform",
            initial_agents=[
                {"role": "backend", "name": "Alex"},
                {"role": "frontend", "name": "Sarah"}
            ]
        )
        
        assert project1_id in app_config.projects
        # Project path uses folder name derived from project name
        folder1_name = "e-commerce-platform"  # Expected from "E-commerce Platform"
        project1_path = temp_home / "projects" / folder1_name
        assert project1_path.exists()
        
        # Step 4: Load project and check agents
        project1_config = ProjectConfig.load(project1_path)
        assert len(project1_config.active_agents) == 2
        assert any(agent.name == "Alex" for agent in project1_config.active_agents.values())
        assert any(agent.name == "Sarah" for agent in project1_config.active_agents.values())
        
        # Step 5: Create second project with custom git config
        git_config = GitConfig(
            user_name="Analytics Team",
            user_email="analytics@company.com"
        )
        
        project2_id = project_manager.create_project(
            project_name="Analytics Dashboard",
            repository_url="https://github.com/company/analytics.git",
            git_config=git_config
        )
        
        assert project2_id in app_config.projects
        assert len(app_config.projects) == 2
        
        # Step 6: Switch between projects
        project_manager.switch_project(project2_id)
        assert app_config.current_project == project2_id
        
        project_manager.switch_project(project1_id)
        assert app_config.current_project == project1_id
        
        # Step 7: Add more agents to project 1
        qa_agent_id = project_manager.create_agent(project1_id, "qa", "Jordan")
        assert qa_agent_id is not None
        
        # Reload project config
        project1_config = ProjectConfig.load(project1_path)
        assert len(project1_config.active_agents) == 3
        
        # Step 8: List all projects
        projects_list = project_manager.list_projects()
        assert len(projects_list) == 2
        assert projects_list[0]["is_current"] or projects_list[1]["is_current"]
        
        # Step 9: Archive a project
        project_manager.archive_project(project2_id)
        folder2_name = "analytics-dashboard"  # Expected from "Analytics Dashboard"
        project2_config = ProjectConfig.load(temp_home / "projects" / folder2_name)
        assert project2_config.project_metadata.status == "archived"
    
    def test_template_system_integration(self, temp_home):
        """Test template system with project and system templates"""
        # Initialize app
        app_config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        # Create system templates
        backend_template = app_config.system_templates_directory / "backend.md"
        backend_template.write_text("""# Backend Developer
You are {{AGENT_NAME}}, a backend developer specializing in {{ROLE}} development.

## System Template
This is the system-wide backend template.""")
        
        frontend_template = app_config.system_templates_directory / "frontend.md"
        frontend_template.write_text("""# Frontend Developer
You are {{AGENT_NAME}}, a frontend developer.""")
        
        # Create project
        project_path = app_config.projects_directory / "test-project"
        project_path.mkdir(parents=True)
        (project_path / "templates").mkdir()
        
        # Create project-specific backend template (should override system)
        project_backend = project_path / "templates" / "backend.md"
        project_backend.write_text("""# Project Backend Developer
You are {{AGENT_NAME}} working on this specific project.

## Project Template
This is the project-specific backend template.""")
        
        # Test template manager
        project_config = ProjectConfig.create(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git"
        )
        project_config.set_config_path(project_path / "project.config.json")
        project_config.save()
        
        template_manager = TemplateManager(app_config, project_path=project_path)
        
        # Backend should use project template
        backend_path = template_manager.get_template_path("backend")
        assert backend_path == project_backend
        
        # Frontend should use system template
        frontend_path = template_manager.get_template_path("frontend")
        assert frontend_path == frontend_template
        
        # Nonexistent role should return None
        assert template_manager.get_template_path("devops") is None
    
    @patch('subprocess.run')
    def test_agent_naming_conflicts(self, mock_run, temp_home):
        """Test handling of agent naming conflicts"""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        # Initialize and create project
        app_config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        project_manager = ProjectManager(app_config)
        
        project_id = project_manager.create_project(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git"
        )
        
        # Create multiple agents with same name
        agent1_id = project_manager.create_agent(project_id, "backend", "Alex")
        agent2_id = project_manager.create_agent(project_id, "backend", "Alex")
        agent3_id = project_manager.create_agent(project_id, "frontend", "Alex")
        
        # All should have unique IDs
        assert agent1_id == "backend-alex"
        assert agent2_id == "backend-alex-1"
        assert agent3_id == "frontend-alex"
        
        # Check all agents exist
        folder_name = "test-project"  # Expected from "Test Project"
        project_config = ProjectConfig.load(
            app_config.projects_directory / folder_name
        )
        assert len(project_config.active_agents) == 3
    
    def test_project_isolation(self, temp_home):
        """Test that projects are properly isolated"""
        # Initialize app
        app_config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        # Create two projects with different settings
        project1_path = app_config.projects_directory / "project-1"
        project1_path.mkdir(parents=True)
        
        project1_config = ProjectConfig.create(
            project_name="Project 1",
            repository_url="https://github.com/test/repo1.git"
        )
        project1_config.project_tokens["api_key"] = "project1-secret"
        project1_config.add_agent("backend", "Alex", "agents/backend-alex")
        project1_config.set_config_path(project1_path / "project.config.json")
        project1_config.save()
        
        project2_path = app_config.projects_directory / "project-2"
        project2_path.mkdir(parents=True)
        
        project2_config = ProjectConfig.create(
            project_name="Project 2",
            repository_url="https://github.com/test/repo2.git"
        )
        project2_config.project_tokens["api_key"] = "project2-secret"
        project2_config.add_agent("backend", "Blake", "agents/backend-blake")
        project2_config.set_config_path(project2_path / "project.config.json")
        project2_config.save()
        
        # Load and verify isolation
        loaded1 = ProjectConfig.load(project1_path)
        loaded2 = ProjectConfig.load(project2_path)
        
        assert loaded1.project_tokens["api_key"] == "project1-secret"
        assert loaded2.project_tokens["api_key"] == "project2-secret"
        
        assert len(loaded1.active_agents) == 1
        assert len(loaded2.active_agents) == 1
        
        agent1 = list(loaded1.active_agents.values())[0]
        agent2 = list(loaded2.active_agents.values())[0]
        
        assert agent1.name == "Alex"
        assert agent2.name == "Blake"
    
    def test_migration_scenario(self, temp_home):
        """Test migrating from old workspace to new multi-project structure"""
        # Simulate old workspace structure
        old_workspace = temp_home / "old-workspace"
        old_workspace.mkdir()
        
        old_config = {
            "workspace_folder": str(old_workspace),
            "repository_url": "https://github.com/test/legacy.git",
            "agents": ["backend", "frontend"]
        }
        
        old_config_file = old_workspace / "workspace_config.json"
        old_config_file.write_text(json.dumps(old_config))
        
        # Initialize new multi-project structure
        app_config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        # Create imported project
        project_manager = ProjectManager(app_config)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            imported_id = project_manager.create_project(
                project_name="Imported Legacy Project",
                repository_url=old_config["repository_url"],
                description="Migrated from old workspace"
            )
        
        # Verify migration
        assert imported_id in app_config.projects
        folder_name = "imported-legacy-project"  # Expected from "Imported Legacy Project"
        project_config = ProjectConfig.load(
            app_config.projects_directory / folder_name
        )
        assert project_config.repository.url == old_config["repository_url"]
    
    def test_concurrent_project_operations(self, temp_home):
        """Test that multiple projects can be operated on independently"""
        # Initialize app
        app_config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        project_manager = ProjectManager(app_config)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # Create multiple projects
            project_ids = []
            for i in range(3):
                project_id = project_manager.create_project(
                    project_name=f"Project {i}",
                    repository_url=f"https://github.com/test/repo{i}.git"
                )
                project_ids.append(project_id)
                
                # Add agents to each
                for j in range(2):
                    project_manager.create_agent(
                        project_id,
                        "backend" if j == 0 else "frontend",
                        f"Agent{i}{j}"
                    )
        
        # Verify all projects exist with correct agents
        for i, project_id in enumerate(project_ids):
            # project_id is now the same as folder_name
            project_config = ProjectConfig.load(
                app_config.projects_directory / project_id
            )
            assert len(project_config.active_agents) == 2
            
            # Check agent names
            agent_names = [agent.name for agent in project_config.active_agents.values()]
            assert f"Agent{i}0" in agent_names
            assert f"Agent{i}1" in agent_names
    
    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_project_agent_lifecycle(self, mock_popen, mock_run, temp_home):
        """Test complete agent lifecycle with new architecture"""
        mock_run.return_value = MagicMock(returncode=0)
        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Initialize app
        app_config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        project_manager = ProjectManager(app_config)
        agent_manager = AgentManager(app_config)
        
        # Create project with agents
        project_id = project_manager.create_project(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git",
            initial_agents=[
                {"role": "backend", "name": "Alex"},
                {"role": "frontend", "name": "Sarah"}
            ]
        )
        
        # Verify project created
        assert project_id in app_config.projects
        folder_name = "test-project"  # Expected from "Test Project"
        project_config = ProjectConfig.load(app_config.projects_directory / folder_name)
        assert len(project_config.active_agents) == 2
        
        # Start agents
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 1234
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            results = agent_manager.start_project_agents(project_id)
        
        assert results["backend-alex"] == "started"
        assert results["frontend-sarah"] == "started"
        assert project_id in agent_manager.running_processes
        
        # Check status
        status = agent_manager.get_project_status(project_id)
        assert status["backend-alex"]["running"] is True
        assert status["frontend-sarah"]["running"] is True
        
        # Stop agents
        stop_results = agent_manager.stop_project_agents(project_id)
        assert "backend-alex" in stop_results
        assert "frontend-sarah" in stop_results
        assert project_id not in agent_manager.running_processes
    
    def test_telegram_configuration_per_project(self, temp_home):
        """Test Telegram configuration at project level"""
        # Initialize app
        app_config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        # Create two projects with different Telegram configs
        project1_path = app_config.projects_directory / "project-1"
        project1_path.mkdir(parents=True)
        
        project1_config = ProjectConfig.create(
            project_name="Project 1",
            repository_url="https://github.com/test/repo1.git"
        )
        project1_config.telegram_config.bot_token = "bot-token-1"
        project1_config.telegram_config.group_id = "group-1"
        project1_config.telegram_config.enabled = True
        project1_config.set_config_path(project1_path / "project.config.json")
        project1_config.save()
        
        project2_path = app_config.projects_directory / "project-2"
        project2_path.mkdir(parents=True)
        
        project2_config = ProjectConfig.create(
            project_name="Project 2",
            repository_url="https://github.com/test/repo2.git"
        )
        project2_config.telegram_config.bot_token = "bot-token-2"
        project2_config.telegram_config.group_id = "group-2"
        project2_config.telegram_config.enabled = False
        project2_config.set_config_path(project2_path / "project.config.json")
        project2_config.save()
        
        # Load and verify configs
        loaded1 = ProjectConfig.load(project1_path)
        loaded2 = ProjectConfig.load(project2_path)
        
        assert loaded1.telegram_config.bot_token == "bot-token-1"
        assert loaded1.telegram_config.enabled is True
        assert loaded2.telegram_config.bot_token == "bot-token-2"
        assert loaded2.telegram_config.enabled is False
    
    @patch('subprocess.run')
    def test_no_automatic_agent_startup(self, mock_run, temp_home):
        """Test that agents are not automatically started"""
        mock_run.return_value = MagicMock(returncode=0)
        
        # Initialize app
        app_config = AppConfig.initialize_home(
            temp_home,
            TokenConfig(anthropic_api_key="test-key")
        )
        
        project_manager = ProjectManager(app_config)
        
        # Create project with initial agents
        project_id = project_manager.create_project(
            project_name="Test Project",
            repository_url="https://github.com/test/repo.git",
            initial_agents=[
                {"role": "backend", "name": "Alex"}
            ]
        )
        
        # Verify agents were created but not started
        folder_name = "test-project"  # Expected from "Test Project"
        project_config = ProjectConfig.load(app_config.projects_directory / folder_name)
        assert len(project_config.active_agents) == 1
        
        # Agent manager should have no running processes
        agent_manager = AgentManager(app_config)
        status = agent_manager.get_project_status(project_id)
        assert status == {"status": "no agents running"}