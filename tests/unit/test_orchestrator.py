"""Unit tests for AgentOrchestrator"""

import pytest
import asyncio
import subprocess
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from core.orchestrator import (
    AgentOrchestrator, PortConfig, AgentProcess, AgentRole
)
from core.telegram_bridge import TelegramSettings
from core.github_sync import GitHubSettings


class TestPortConfig:
    """Test PortConfig functionality"""
    
    def test_allocate_port(self):
        """Test port allocation"""
        config = PortConfig()
        
        # Allocate first port
        port1 = config.allocate_port("backend")
        assert port1 == 8300
        assert config.allocated_ports["backend"] == 8300
        
        # Allocate second port
        port2 = config.allocate_port("frontend")
        assert port2 == 8301
        
        # Request same role again - should return same port
        port3 = config.allocate_port("backend")
        assert port3 == 8300
        
    def test_allocate_all_ports(self):
        """Test allocating maximum ports"""
        config = PortConfig(start_port=9000, max_agents=3)
        
        config.allocate_port("agent1")
        config.allocate_port("agent2")
        config.allocate_port("agent3")
        
        # Should raise error when all ports allocated
        with pytest.raises(ValueError, match="No available ports"):
            config.allocate_port("agent4")
            
    def test_release_port(self):
        """Test releasing allocated port"""
        config = PortConfig()
        
        port = config.allocate_port("backend")
        assert "backend" in config.allocated_ports
        
        config.release_port("backend")
        assert "backend" not in config.allocated_ports
        
        # Should be able to allocate again
        new_port = config.allocate_port("backend")
        assert new_port == port


class TestAgentOrchestrator:
    """Test AgentOrchestrator functionality"""
    
    def test_initialization(self, orchestrator, temp_dir):
        """Test orchestrator initialization"""
        assert orchestrator.config_dir == temp_dir / "config"
        assert orchestrator.config_dir.exists()
        assert isinstance(orchestrator.port_config, PortConfig)
        assert orchestrator.agents == {}
        assert orchestrator.processes == {}
        
    @pytest.mark.asyncio
    async def test_initialize_with_integrations(self, orchestrator):
        """Test initializing with Telegram and GitHub"""
        telegram_settings = TelegramSettings(
            bot_token="test-token",
            channel_id="test-channel"
        )
        github_settings = GitHubSettings(
            token="test-token",
            repo_name="test-repo"
        )
        
        with patch('core.orchestrator.TelegramBridge') as mock_telegram:
            with patch('core.orchestrator.GitHubSync') as mock_github:
                bridge_instance = AsyncMock()
                mock_telegram.return_value = bridge_instance
                
                await orchestrator.initialize(telegram_settings, github_settings)
                
                assert orchestrator.telegram_bridge is not None
                assert orchestrator.github_sync is not None
                bridge_instance.start.assert_called_once()
                
    @pytest.mark.asyncio
    async def test_create_agent(self, orchestrator, temp_dir):
        """Test creating a new agent"""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            # Mock wait_for_agent
            orchestrator._wait_for_agent = AsyncMock()
            
            # Create the agent in orchestrator first
            from core.orchestrator import AgentProcess
            agent_process = AgentProcess(
                role=AgentRole.BACKEND,
                port=8300,
                env_file=str(temp_dir / "config" / ".env.backend")
            )
            orchestrator.agents["backend"] = agent_process
            
            agent = await orchestrator.create_agent(
                role=AgentRole.BACKEND,
                model="claude-3-sonnet-20240229",
                github_repo="org/repo",
                telegram_channel_id="12345"
            )
            
            assert agent.role == AgentRole.BACKEND
            assert agent.port == 8300
            assert agent.pid == 12345
            assert agent.status == "running"
            
            # Check env file created
            env_file = temp_dir / "config" / ".env.backend"
            assert env_file.exists()
            content = env_file.read_text()
            assert "ROLE=backend" in content
            assert "PORT=8300" in content
            assert "GITHUB_REPO=org/repo" in content
            
            # Check CLAUDE.md file created
            claude_file = temp_dir / "config" / "claude-backend.md"
            assert claude_file.exists()
            
    @pytest.mark.asyncio
    async def test_create_duplicate_agent(self, orchestrator):
        """Test creating duplicate agent raises error"""
        orchestrator.agents["backend"] = Mock()
        
        with pytest.raises(ValueError, match="already exists"):
            await orchestrator.create_agent(AgentRole.BACKEND)
            
    def test_create_env_file(self, orchestrator, temp_dir):
        """Test environment file creation"""
        orchestrator._create_env_file(
            temp_dir / "test.env",
            "backend",
            8301,
            "claude-3-opus",
            "org/repo",
            "12345"
        )
        
        content = (temp_dir / "test.env").read_text()
        assert "ROLE=backend" in content
        assert "PORT=8301" in content
        assert "MODEL=claude-3-opus" in content
        assert "GITHUB_REPO=org/repo" in content
        assert "TELEGRAM_CHANNEL_ID=12345" in content
        
    @pytest.mark.asyncio
    async def test_start_agent(self, orchestrator):
        """Test starting an agent"""
        agent = AgentProcess(
            role=AgentRole.BACKEND,
            port=8301,
            env_file="test.env"
        )
        orchestrator.agents["backend"] = agent
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            orchestrator._wait_for_agent = AsyncMock()
            
            await orchestrator.start_agent("backend")
            
            assert orchestrator.processes["backend"] == mock_process
            assert agent.pid == 12345
            assert agent.status == "running"
            
            # Verify command
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert "python" in cmd[0]
            assert "-m" in cmd
            assert "agents.api" in cmd
            assert "test.env" in cmd
            
    @pytest.mark.asyncio
    async def test_start_nonexistent_agent(self, orchestrator):
        """Test starting non-existent agent"""
        with pytest.raises(ValueError, match="Agent frontend not found"):
            await orchestrator.start_agent("frontend")
            
    @pytest.mark.asyncio
    async def test_wait_for_agent_success(self, orchestrator, mock_httpx_client):
        """Test waiting for agent to be ready"""
        orchestrator.client = mock_httpx_client
        mock_httpx_client.get.return_value.status_code = 200
        
        # Should complete without error
        await orchestrator._wait_for_agent(8301, timeout=1)
        
    @pytest.mark.asyncio
    async def test_wait_for_agent_timeout(self, orchestrator, mock_httpx_client):
        """Test timeout waiting for agent"""
        orchestrator.client = mock_httpx_client
        mock_httpx_client.get.side_effect = Exception("Connection refused")
        
        with pytest.raises(TimeoutError):
            await orchestrator._wait_for_agent(8301, timeout=0.1)
            
    @pytest.mark.asyncio
    async def test_stop_agent(self, orchestrator):
        """Test stopping an agent"""
        mock_process = Mock()
        orchestrator.processes["backend"] = mock_process
        
        agent = Mock()
        orchestrator.agents["backend"] = agent
        
        await orchestrator.stop_agent("backend")
        
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        assert "backend" not in orchestrator.processes
        assert agent.status == "stopped"
        assert agent.pid is None
        
    @pytest.mark.asyncio
    async def test_stop_agent_force_kill(self, orchestrator):
        """Test force killing agent if terminate fails"""
        mock_process = Mock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 5)
        orchestrator.processes["backend"] = mock_process
        
        await orchestrator.stop_agent("backend")
        
        mock_process.kill.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_restart_agent(self, orchestrator):
        """Test restarting an agent"""
        orchestrator.stop_agent = AsyncMock()
        orchestrator.start_agent = AsyncMock()
        
        await orchestrator.restart_agent("backend")
        
        orchestrator.stop_agent.assert_called_once_with("backend")
        orchestrator.start_agent.assert_called_once_with("backend")
        
    @pytest.mark.asyncio
    async def test_get_agent_status_online(self, orchestrator, mock_httpx_client):
        """Test getting status of online agent"""
        agent = AgentProcess(
            role=AgentRole.BACKEND,
            port=8301,
            env_file="test.env",
            pid=12345,
            status="running"
        )
        orchestrator.agents["backend"] = agent
        orchestrator.client = mock_httpx_client
        
        mock_httpx_client.get.return_value.status_code = 200
        mock_httpx_client.get.return_value.json.return_value = {
            "role": "backend",
            "health": "active",
            "current_task": None
        }
        
        status = await orchestrator.get_agent_status("backend")
        
        assert status["role"] == "backend"
        assert status["health"] == "active"
        assert status["process"]["pid"] == 12345
        assert status["process"]["status"] == "running"
        assert "uptime" in status["process"]
        
    @pytest.mark.asyncio
    async def test_get_agent_status_offline(self, orchestrator, mock_httpx_client):
        """Test getting status of offline agent"""
        agent = AgentProcess(
            role=AgentRole.BACKEND,
            port=8301,
            env_file="test.env",
            status="stopped"
        )
        orchestrator.agents["backend"] = agent
        orchestrator.client = mock_httpx_client
        
        mock_httpx_client.get.side_effect = Exception("Connection refused")
        
        status = await orchestrator.get_agent_status("backend")
        
        assert status["role"] == "backend"
        assert status["status"] == "offline"
        
    @pytest.mark.asyncio
    async def test_get_all_agents_status(self, orchestrator):
        """Test getting status of all agents"""
        orchestrator.agents = {
            "backend": Mock(),
            "frontend": Mock()
        }
        
        orchestrator.get_agent_status = AsyncMock(side_effect=[
            {"role": "backend", "status": "online"},
            {"role": "frontend", "status": "offline"}
        ])
        
        statuses = await orchestrator.get_all_agents_status()
        
        assert len(statuses) == 2
        assert statuses[0]["role"] == "backend"
        assert statuses[1]["role"] == "frontend"
        
    @pytest.mark.asyncio
    async def test_assign_github_tasks(self, orchestrator, mock_httpx_client):
        """Test assigning GitHub tasks to agents"""
        # Setup agents
        orchestrator.agents = {
            "backend": AgentProcess(
                role=AgentRole.BACKEND,
                port=8301,
                env_file="test.env",
                status="running"
            )
        }
        
        # Setup GitHub sync
        github_sync = AsyncMock()
        task = Mock()
        task.issue_number = 1
        task.title = "Test task"
        task.body = "Description"
        task.assignee = None
        
        github_sync.get_tasks_for_role.return_value = [task]
        github_sync.update_issue_status = AsyncMock()
        orchestrator.github_sync = github_sync
        
        # Setup HTTP client
        orchestrator.client = mock_httpx_client
        mock_httpx_client.post.return_value.status_code = 200
        
        # Setup Telegram bridge
        telegram_bridge = AsyncMock()
        orchestrator.telegram_bridge = telegram_bridge
        
        await orchestrator.assign_github_tasks()
        
        # Verify task assignment
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        assert "assign" in call_args[0][0]
        assert call_args[1]["json"]["github_issue_number"] == 1
        
        # Verify GitHub update
        github_sync.update_issue_status.assert_called_once()
        
        # Verify Telegram notification
        telegram_bridge.send_message.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_shutdown(self, orchestrator):
        """Test orchestrator shutdown"""
        # Setup mocks
        orchestrator.processes = {
            "backend": Mock(),
            "frontend": Mock()
        }
        orchestrator.stop_agent = AsyncMock()
        orchestrator.telegram_bridge = AsyncMock()
        orchestrator.client = AsyncMock()
        
        await orchestrator.shutdown()
        
        # Verify all agents stopped
        assert orchestrator.stop_agent.call_count == 2
        
        # Verify Telegram stopped
        orchestrator.telegram_bridge.stop.assert_called_once()
        
        # Verify HTTP client closed
        orchestrator.client.aclose.assert_called_once()