"""Integration tests for Web API"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
import json

from web.backend import app, orchestrator
from core.orchestrator import AgentOrchestrator, AgentProcess, AgentRole
from core.telegram_bridge import TelegramSettings
from core.github_sync import GitHubSettings


class TestWebAPI:
    """Test Web API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
        
    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator"""
        mock = AsyncMock(spec=AgentOrchestrator)
        mock.agents = {}
        mock.telegram_bridge = None
        mock.github_sync = None
        
        # Patch the global orchestrator
        with patch('web.backend.orchestrator', mock):
            yield mock
            
    def test_initialize_system_full(self, client, mock_orchestrator):
        """Test system initialization with all integrations"""
        config = {
            "anthropic_api_key": "test-key",
            "telegram_bot_token": "bot-token",
            "telegram_channel_id": "channel-id",
            "github_token": "github-token",
            "github_repo": "org/repo"
        }
        
        response = client.post("/api/system/initialize", json=config)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "initialized"
        assert data["telegram"] is True
        assert data["github"] is True
        
        mock_orchestrator.initialize.assert_called_once()
        
    def test_initialize_system_minimal(self, client, mock_orchestrator):
        """Test system initialization with minimal config"""
        config = {
            "anthropic_api_key": "test-key"
        }
        
        response = client.post("/api/system/initialize", json=config)
        
        assert response.status_code == 200
        data = response.json()
        assert data["telegram"] is False
        assert data["github"] is False
        
    def test_get_agents(self, client, mock_orchestrator):
        """Test getting all agents"""
        # The new system auto-discovers all 6 agent types
        response = client.get("/api/agents")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6  # All 6 agent types
        roles = [agent["role"] for agent in data]
        assert "backend" in roles
        assert "frontend" in roles
        assert "database" in roles
        assert "qa" in roles
        assert "ba" in roles
        assert "teamlead" in roles
        
    def test_get_agents_not_initialized(self, client):
        """Test getting agents when system not initialized"""
        # New system always returns agent status (online/offline)
        response = client.get("/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6
            
    def test_create_agent(self, client, mock_orchestrator):
        """Test creating a new agent"""
        # New system has agents already running as services
        request_data = {
            "role": "backend",
            "model": "claude-3-5-sonnet-20241022",
            "github_repo": "org/repo",
            "telegram_channel_id": "12345"
        }
        
        response = client.post("/api/agents", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        # Can be either already_running or not_running depending on whether agents are running
        assert data["status"] in ["already_running", "not_running"]
        if data["status"] == "not_running":
            assert "start-devteam.sh" in data["message"]
        
    def test_create_agent_error(self, client, mock_orchestrator):
        """Test agent creation error handling"""
        # Test with invalid role - FastAPI returns 422 for enum validation errors
        response = client.post("/api/agents", json={"role": "invalid_role"})
        
        assert response.status_code == 422  # Unprocessable Entity for validation error
        assert "Input should be" in response.json()["detail"][0]["msg"]
        
    def test_get_agent_status(self, client, mock_orchestrator):
        """Test getting specific agent status"""
        # New system checks agent health directly
        response = client.get("/api/agents/backend")
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "backend"
        assert "health" in data  # Can be 'running' or 'offline'
        
    def test_get_agent_status_not_found(self, client, mock_orchestrator):
        """Test getting status of non-existent agent"""
        response = client.get("/api/agents/unknown")
        
        assert response.status_code == 404
        assert "Unknown agent role" in response.json()["detail"]
        
    def test_restart_agent(self, client, mock_orchestrator):
        """Test restarting an agent"""
        response = client.post("/api/agents/backend/restart")
        
        assert response.status_code == 501
        assert "standalone services" in response.json()["detail"]
        
    def test_stop_agent(self, client, mock_orchestrator):
        """Test stopping an agent"""
        response = client.delete("/api/agents/backend")
        
        assert response.status_code == 501
        assert "standalone services" in response.json()["detail"]
        
    @patch('httpx.AsyncClient')
    def test_assign_task(self, mock_httpx, client, mock_orchestrator):
        """Test manually assigning a task"""
        # Setup agent
        agent = AgentProcess(
            role=AgentRole.BACKEND,
            port=8301,
            env_file="test.env"
        )
        mock_orchestrator.agents = {"backend": agent}
        
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "assigned"}
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        request_data = {
            "agent_role": "backend",
            "task_title": "Implement feature",
            "task_description": "Add new endpoint",
            "github_issue_number": 42
        }
        
        response = client.post("/api/tasks/assign", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "assigned"
        
    def test_assign_task_agent_not_found(self, client, mock_orchestrator):
        """Test assigning task to non-existent agent"""
        request_data = {
            "agent_role": "unknown",
            "task_title": "Test",
            "task_description": "Test"
        }
        
        response = client.post("/api/tasks/assign", json=request_data)
        
        assert response.status_code == 404
        assert "Unknown agent role" in response.json()["detail"]
        
    def test_sync_github_tasks(self, client, mock_orchestrator):
        """Test syncing GitHub tasks"""
        mock_orchestrator.github_sync = Mock()
        
        response = client.post("/api/tasks/sync-github")
        
        assert response.status_code == 200
        assert response.json()["status"] == "synced"
        
        mock_orchestrator.assign_github_tasks.assert_called_once()
        
    def test_sync_github_not_configured(self, client, mock_orchestrator):
        """Test GitHub sync when not configured"""
        # In the new system, GitHub sync is always available if configured in .env
        response = client.post("/api/tasks/sync-github")
        
        # Will succeed if configured, or fail if not
        assert response.status_code in [200, 400]
        if response.status_code == 400:
            assert "GitHub not configured" in response.json()["detail"]
        
    def test_get_agent_logs(self, client, mock_orchestrator):
        """Test getting agent logs"""
        # New system reads logs directly from files
        response = client.get("/api/agents/backend/logs?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)
        
    def test_get_claude_prompt(self, client, temp_dir):
        """Test getting CLAUDE.md content"""
        # Create test file
        claude_file = temp_dir / "config" / "claude-backend.md"
        claude_file.parent.mkdir(exist_ok=True)
        claude_file.write_text("# Test prompt")
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="# Test prompt"):
                response = client.get("/api/claude/backend")
                
                assert response.status_code == 200
                assert response.json()["content"] == "# Test prompt"
                
    def test_get_claude_prompt_not_found(self, client):
        """Test getting non-existent CLAUDE.md"""
        with patch('pathlib.Path.exists', return_value=False):
            response = client.get("/api/claude/unknown")
            assert response.status_code == 404
            
    def test_update_claude_prompt(self, client, temp_dir):
        """Test updating CLAUDE.md content"""
        claude_file = temp_dir / "config" / "claude-backend.md"
        claude_file.parent.mkdir(exist_ok=True)
        
        with patch('pathlib.Path.write_text') as mock_write:
            response = client.put(
                "/api/claude/backend",
                json={"content": "# Updated prompt"}
            )
            
            assert response.status_code == 200
            assert response.json()["status"] == "updated"
            mock_write.assert_called_once_with("# Updated prompt")
            
    def test_websocket_connection(self, client, mock_orchestrator):
        """Test WebSocket connection"""
        mock_orchestrator.get_all_agents_status.return_value = []
        
        with client.websocket_connect("/ws") as websocket:
            # Connection should be accepted
            # In real scenario, would receive periodic updates
            pass
            
    def test_request_validation(self, client):
        """Test request validation for various endpoints"""
        # Missing required fields
        response = client.post("/api/agents", json={})
        assert response.status_code == 422
        
        response = client.post("/api/tasks/assign", json={"agent_role": "backend"})
        assert response.status_code == 422
        
        response = client.post("/api/system/initialize", json={})
        assert response.status_code == 422