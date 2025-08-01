"""Unit tests for Agent API"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from agents.api import AgentAPI, create_agent_api
from core.claude_agent import ClaudeAgent, AgentSettings, AgentRole, Task, TaskStatus


class TestAgentAPI:
    """Test Agent API functionality"""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent"""
        agent = Mock(spec=ClaudeAgent)
        agent.settings = Mock(role=AgentRole.BACKEND)
        agent.state = Mock(task_history=[], messages=[])
        agent.get_status = Mock(return_value={
            "role": "backend",
            "status": "running",
            "health": "active"
        })
        agent.process_message = AsyncMock(return_value="Test response")
        agent.assign_task = AsyncMock()
        agent.complete_task = AsyncMock(return_value=Task(
            id="test-1",
            title="Completed task",
            description="Test"
        ))
        return agent
        
    @pytest.fixture
    def api_client(self, mock_agent):
        """Create test client with mock agent"""
        api = AgentAPI(mock_agent)
        return TestClient(api.app)
        
    def test_root_endpoint(self, api_client):
        """Test root endpoint"""
        response = api_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "backend"
        assert data["status"] == "running"
        
    def test_status_endpoint(self, api_client, mock_agent):
        """Test status endpoint"""
        response = api_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "backend"
        assert data["health"] == "active"
        mock_agent.get_status.assert_called_once()
        
    def test_ask_endpoint(self, api_client, mock_agent):
        """Test ask endpoint"""
        response = api_client.post("/ask", json={
            "message": "Help me with code",
            "context": {"task_id": "123"}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Test response"
        
        mock_agent.process_message.assert_called_once_with(
            "Help me with code",
            {"task_id": "123"}
        )
        
    def test_ask_endpoint_no_context(self, api_client, mock_agent):
        """Test ask endpoint without context"""
        response = api_client.post("/ask", json={
            "message": "Simple question"
        })
        
        assert response.status_code == 200
        mock_agent.process_message.assert_called_once_with("Simple question", None)
        
    def test_assign_endpoint(self, api_client, mock_agent):
        """Test assign task endpoint"""
        response = api_client.post("/assign", json={
            "id": "test-1",
            "title": "Implement feature",
            "description": "Add new endpoint",
            "github_issue_number": 42
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "assigned"
        assert "task" in data
        
        # Verify task was created correctly
        mock_agent.assign_task.assert_called_once()
        task_arg = mock_agent.assign_task.call_args[0][0]
        assert task_arg.id == "test-1"
        assert task_arg.title == "Implement feature"
        assert task_arg.github_issue_number == 42
        
    def test_complete_endpoint_success(self, api_client, mock_agent):
        """Test complete task endpoint - success"""
        response = api_client.post("/complete")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["task"]["title"] == "Completed task"
        
        mock_agent.complete_task.assert_called_once()
        
    def test_complete_endpoint_no_task(self, api_client, mock_agent):
        """Test complete task endpoint - no active task"""
        mock_agent.complete_task.return_value = None
        
        response = api_client.post("/complete")
        
        assert response.status_code == 400
        data = response.json()
        assert "No active task" in data["detail"]
        
    def test_history_endpoint(self, api_client, mock_agent):
        """Test history endpoint"""
        # Setup mock data
        mock_agent.state.task_history = [
            Task(id="1", title="Task 1", description="Test"),
            Task(id="2", title="Task 2", description="Test")
        ]
        mock_agent.state.messages = [
            {"message": "msg1"},
            {"message": "msg2"},
            {"message": "msg3"}
        ]
        
        response = api_client.get("/history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["task_history"]) == 2
        assert len(data["message_history"]) == 3
        
    def test_history_endpoint_limit(self, api_client, mock_agent):
        """Test history endpoint respects message limit"""
        # Create 100 messages
        mock_agent.state.messages = [{"message": f"msg{i}"} for i in range(100)]
        
        response = api_client.get("/history")
        data = response.json()
        
        # Should only return last 50
        assert len(data["message_history"]) == 50
        assert data["message_history"][0]["message"] == "msg50"
        assert data["message_history"][-1]["message"] == "msg99"
        
    @patch('agents.api.AgentSettings')
    @patch('agents.api.ClaudeAgent')
    def test_create_agent_api(self, mock_claude_agent, mock_settings):
        """Test create_agent_api factory function"""
        # Setup mocks
        settings_instance = Mock()
        mock_settings.return_value = settings_instance
        
        agent_instance = Mock()
        mock_claude_agent.return_value = agent_instance
        
        # Create API
        api = create_agent_api(".env.test")
        
        assert isinstance(api, AgentAPI)
        assert api.agent == agent_instance
        
        # Verify settings were created with correct env file
        mock_settings.assert_called_once()
        assert mock_settings.call_args[1]["_env_file"] == ".env.test"
        
    def test_api_error_handling(self, api_client, mock_agent):
        """Test API error handling"""
        # Make process_message raise an exception
        mock_agent.process_message.side_effect = Exception("API Error")
        
        # The TestClient will raise the exception by default
        # We need to verify that the exception is indeed raised
        import pytest
        
        with pytest.raises(Exception) as exc_info:
            response = api_client.post("/ask", json={"message": "test"})
            
        assert str(exc_info.value) == "API Error"
        
    def test_request_validation(self, api_client):
        """Test request validation"""
        # Missing required fields
        response = api_client.post("/ask", json={})
        assert response.status_code == 422
        
        response = api_client.post("/assign", json={"title": "No ID"})
        assert response.status_code == 422
        
    def test_concurrent_requests(self, api_client, mock_agent):
        """Test handling concurrent requests"""
        import concurrent.futures
        
        def make_request():
            return api_client.post("/ask", json={"message": "concurrent test"})
            
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
        # All should succeed
        assert all(r.status_code == 200 for r in results)
        assert mock_agent.process_message.call_count == 10