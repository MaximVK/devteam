"""Unit tests for AgentManager"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import subprocess
import json
import tempfile
import socket

from core.agent_manager import AgentManager
from core.app_config import AppConfig, TokenConfig
from core.project_config import ProjectConfig, AgentInfo, TelegramConfig


class TestAgentManager:
    """Test AgentManager functionality"""
    
    @pytest.fixture
    def app_config(self):
        """Create test app config"""
        config = AppConfig(
            home_directory=Path("/tmp/test-home"),
            tokens=TokenConfig(anthropic_api_key="test-key")
        )
        # Create a proper ProjectInfo mock
        from core.app_config import ProjectInfo
        from datetime import datetime
        config.projects["test-project"] = ProjectInfo(
            name="Test Project",
            path="projects/test-project",
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )
        return config
    
    @pytest.fixture
    def project_config(self):
        """Create test project config"""
        from core.project_config import Repository
        config = ProjectConfig(
            project_id="test-project",
            project_name="Test Project",
            repository=Repository(url="https://github.com/test/repo.git")
        )
        config.active_agents["backend-alex"] = AgentInfo(
            role="backend",
            name="Alex",
            workspace="agents/backend-alex"
        )
        config.active_agents["frontend-sarah"] = AgentInfo(
            role="frontend", 
            name="Sarah",
            workspace="agents/frontend-sarah"
        )
        return config
    
    @pytest.fixture
    def agent_manager(self, app_config):
        """Create AgentManager instance"""
        return AgentManager(app_config)
    
    def test_init(self, app_config):
        """Test AgentManager initialization"""
        manager = AgentManager(app_config)
        assert manager.app_config == app_config
        assert manager.running_processes == {}
        assert manager.pid_file == app_config.home_directory / ".agent_pids.json"
        assert manager.port_file == app_config.home_directory / ".agent_ports.json"
        assert manager.allocated_ports == {}
    
    @patch('pathlib.Path.exists')
    @patch('core.agent_manager.AgentManager._is_process_running')
    def test_load_pid_file(self, mock_is_running, mock_exists, app_config):
        """Test loading PID file"""
        mock_is_running.return_value = True
        mock_exists.return_value = True
        
        with patch('builtins.open', mock_open(read_data='{"test-project": {"agent1": 1234}}')):
            manager = AgentManager(app_config)
            manager._load_pid_file()
        
        assert "test-project" in manager.running_processes
        assert manager.running_processes["test-project"]["agent1"] == 1234
    
    @patch('builtins.open', mock_open())
    @patch('json.dump')
    def test_save_pid_file(self, mock_json_dump, agent_manager):
        """Test saving PID file"""
        # Create a proper subprocess.Popen mock
        import subprocess
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 5678
        agent_manager.running_processes = {
            "project1": {
                "agent1": mock_process,
                "agent2": 9999  # Already a PID
            }
        }
        
        agent_manager._save_pid_file()
        
        # Check json.dump was called with correct data
        mock_json_dump.assert_called_once()
        saved_data = mock_json_dump.call_args[0][0]
        assert saved_data["project1"]["agent1"] == 5678
        assert saved_data["project1"]["agent2"] == 9999
    
    @patch('psutil.Process')
    def test_is_process_running(self, mock_process, agent_manager):
        """Test process running check"""
        # Process exists and is running
        mock_proc_instance = Mock()
        mock_proc_instance.is_running.return_value = True
        mock_proc_instance.cmdline.return_value = ['python', 'run_project_agent.py']
        mock_process.return_value = mock_proc_instance
        
        assert agent_manager._is_process_running(1234) is True
        
        # Process running but not our agent
        mock_proc_instance.cmdline.return_value = ['python', 'some_other_script.py']
        assert agent_manager._is_process_running(1234) is False
        
        # Process doesn't exist
        import psutil
        mock_process.side_effect = psutil.NoSuchProcess(9999)
        assert agent_manager._is_process_running(9999) is False
    
    @patch('core.agent_manager.subprocess.Popen')
    @patch('core.agent_manager.ProjectConfig.load')
    @patch('builtins.open', mock_open())
    def test_start_project_agents(self, mock_load, mock_popen, agent_manager, project_config):
        """Test starting agents for a project"""
        mock_load.return_value = project_config
        mock_process = Mock()
        mock_process.pid = 1234
        mock_popen.return_value = mock_process
        
        # Create logs directory
        agent_manager.app_config.home_directory.mkdir(parents=True, exist_ok=True)
        
        results = agent_manager.start_project_agents("test-project")
        
        assert results["backend-alex"] == "started"
        assert results["frontend-sarah"] == "started"
        assert agent_manager.running_processes["test-project"]["backend-alex"] == mock_process
        assert agent_manager.running_processes["test-project"]["frontend-sarah"] == mock_process
        
        # Verify Popen was called with correct environment
        assert mock_popen.call_count == 2
        env = mock_popen.call_args_list[0][1]['env']
        assert env['DEVTEAM_PROJECT_ID'] == 'test-project'
        assert env['DEVTEAM_AGENT_ROLE'] == 'backend'
        assert env['DEVTEAM_AGENT_NAME'] == 'Alex'
    
    @patch('core.agent_manager.subprocess.Popen')
    @patch('core.agent_manager.ProjectConfig.load')
    def test_start_project_agents_with_telegram(self, mock_load, mock_popen, agent_manager, project_config):
        """Test starting agents with Telegram enabled"""
        project_config.telegram_config = TelegramConfig(
            bot_token="test-token",
            group_id="test-group",
            enabled=True
        )
        mock_load.return_value = project_config
        
        mock_process = Mock()
        mock_process.pid = 1234
        mock_popen.return_value = mock_process
        
        with patch('builtins.open', mock_open()):
            results = agent_manager.start_project_agents("test-project")
        
        assert "telegram_bridge" in results
        assert results["telegram_bridge"] == "started"
    
    @patch('psutil.Process')
    def test_stop_project_agents(self, mock_process_class, agent_manager):
        """Test stopping agents for a project"""
        # Set up running processes
        mock_popen_process = Mock(spec=subprocess.Popen)
        agent_manager.running_processes["test-project"] = {
            "agent1": mock_popen_process,
            "agent2": 5678  # PID only
        }
        
        # Mock psutil Process for PID
        mock_psutil_process = Mock()
        mock_process_class.return_value = mock_psutil_process
        
        results = agent_manager.stop_project_agents("test-project")
        
        assert results["agent1"] == "stopped"
        assert results["agent2"] == "stopped"
        assert "test-project" not in agent_manager.running_processes
        
        # Verify termination was called
        mock_popen_process.terminate.assert_called_once()
        mock_psutil_process.terminate.assert_called_once()
    
    def test_stop_project_agents_no_agents(self, agent_manager):
        """Test stopping agents when none are running"""
        results = agent_manager.stop_project_agents("test-project")
        assert results == {"status": "no agents running"}
    
    def test_get_project_status(self, agent_manager):
        """Test getting project status"""
        mock_process1 = Mock(spec=subprocess.Popen)
        mock_process1.poll.return_value = None  # Still running
        mock_process1.pid = 1234
        
        mock_process2 = Mock(spec=subprocess.Popen)
        mock_process2.poll.return_value = 0  # Stopped
        mock_process2.pid = 5678
        
        agent_manager.running_processes["test-project"] = {
            "agent1": mock_process1,
            "agent2": mock_process2
        }
        
        status = agent_manager.get_project_status("test-project")
        
        assert status["agent1"]["running"] is True
        assert status["agent1"]["pid"] == 1234
        assert status["agent2"]["running"] is False
        assert status["agent2"]["pid"] == 5678
    
    def test_get_project_status_no_agents(self, agent_manager):
        """Test getting status when no agents are running"""
        status = agent_manager.get_project_status("test-project")
        assert status == {"status": "no agents running"}
    
    def test_get_all_projects_status(self, agent_manager):
        """Test getting status for all projects"""
        # Set up app config with multiple projects
        agent_manager.app_config.projects = {
            "project1": Mock(),
            "project2": Mock()
        }
        
        # Set up running processes
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = None
        mock_process.pid = 1234
        
        agent_manager.running_processes = {
            "project1": {"agent1": mock_process},
            "project2": {}
        }
        
        all_status = agent_manager.get_all_projects_status()
        
        assert "project1" in all_status
        assert "project2" in all_status
        assert all_status["project1"]["total_agents"] == 1
        assert all_status["project1"]["running_agents"] == 1
        assert all_status["project2"]["total_agents"] == 0
        assert all_status["project2"]["running_agents"] == 0
    
    def test_stop_all_agents(self, agent_manager):
        """Test stopping all agents"""
        agent_manager.running_processes = {
            "project1": {"agent1": Mock()},
            "project2": {"agent2": Mock()}
        }
        
        with patch.object(agent_manager, 'stop_project_agents') as mock_stop:
            agent_manager.stop_all_agents()
            
            assert mock_stop.call_count == 2
            mock_stop.assert_any_call("project1")
            mock_stop.assert_any_call("project2")
    
    @patch('socket.socket')
    def test_find_available_port(self, mock_socket, agent_manager):
        """Test finding available port"""
        # Mock socket to simulate port availability
        mock_sock_instance = Mock()
        mock_socket.return_value.__enter__.return_value = mock_sock_instance
        
        # First port is taken, second is available
        mock_sock_instance.bind.side_effect = [OSError(), None]
        
        port = agent_manager._find_available_port(8301, 8302)
        assert port == 8302
        
    def test_port_allocation(self, agent_manager):
        """Test dynamic port allocation tracking"""
        # Test initial state
        assert agent_manager.allocated_ports == {}
        assert hasattr(agent_manager, 'port_file')
        assert agent_manager.port_file == agent_manager.app_config.home_directory / ".agent_ports.json"
    
    @patch('core.agent_manager.subprocess.Popen')
    @patch('builtins.open', mock_open())
    def test_start_telegram_bridge(self, mock_popen, agent_manager, project_config):
        """Test starting Telegram bridge"""
        project_config.telegram_config.bot_token = "test-token"
        project_config.telegram_config.group_id = "test-group"
        
        mock_process = Mock()
        mock_process.pid = 9999
        mock_popen.return_value = mock_process
        
        # Initialize the project in running_processes
        agent_manager.running_processes["test-project"] = {}
        
        agent_manager._start_telegram_bridge("test-project", project_config)
        
        # Verify Popen was called with correct environment
        env = mock_popen.call_args[1]['env']
        assert env['DEVTEAM_PROJECT_ID'] == 'test-project'
        assert env['TELEGRAM_BOT_TOKEN'] == 'test-token'
        assert env['TELEGRAM_GROUP_ID'] == 'test-group'
        
        # Verify process was tracked
        assert agent_manager.running_processes["test-project"]["telegram_bridge"] == mock_process