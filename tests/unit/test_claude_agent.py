"""Unit tests for ClaudeAgent"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from pathlib import Path

from core.claude_agent import ClaudeAgent, AgentSettings, AgentRole, Task, TaskStatus, AgentState


class TestClaudeAgent:
    """Test ClaudeAgent functionality"""
    
    def test_agent_initialization(self, claude_agent, agent_settings):
        """Test agent initializes correctly"""
        assert claude_agent.settings == agent_settings
        assert claude_agent.state.current_task is None
        assert claude_agent.state.task_history == []
        assert claude_agent.state.total_tokens_used == 0
        
    def test_system_prompt_loading(self, claude_agent, temp_dir):
        """Test system prompt loads from file"""
        # Create claude.md file with content
        claude_file = temp_dir / "claude.md"
        claude_file.write_text("# Custom prompt")
        
        claude_agent.settings.claude_file = str(claude_file)
        claude_agent._system_prompt = None
        
        prompt = claude_agent.system_prompt
        assert prompt == "# Custom prompt"
        
    def test_default_prompt_generation(self, claude_agent):
        """Test default prompt generation for roles"""
        # Test with non-existent file
        claude_agent.settings.claude_file = "/non/existent/file.md"
        claude_agent._system_prompt = None
        
        prompt = claude_agent.system_prompt
        assert "# COMMON" in prompt
        assert "# ROLE: backend" in prompt
        assert "Implement FastAPI services" in prompt
        
    @pytest.mark.asyncio
    async def test_process_message(self, claude_agent, mock_anthropic_client):
        """Test message processing"""
        response = await claude_agent.process_message("Test message")
        
        assert response == "Test response from Claude"
        assert claude_agent.state.total_tokens_used == 30  # 10 + 20
        assert len(claude_agent.state.messages) == 1
        
        # Check message history
        msg = claude_agent.state.messages[0]
        assert msg["user_message"] == "Test message"
        assert msg["assistant_response"] == "Test response from Claude"
        assert msg["tokens_used"] == 30
        
    @pytest.mark.asyncio
    async def test_process_message_with_context(self, claude_agent):
        """Test message processing with task context"""
        task = Task(
            id="test-1",
            title="Test task",
            description="Test description"
        )
        
        context = {"task": task}
        response = await claude_agent.process_message("Help with task", context)
        
        assert response == "Test response from Claude"
        
    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, claude_agent):
        """Test error handling in message processing"""
        # Make the API call fail
        claude_agent.client.messages.create.side_effect = Exception("API Error")
        
        response = await claude_agent.process_message("Test message")
        assert "Error processing message: API Error" in response
        
    @pytest.mark.asyncio
    async def test_assign_task(self, claude_agent):
        """Test task assignment"""
        task = Task(
            id="test-1",
            title="Implement feature",
            description="Add new endpoint"
        )
        
        await claude_agent.assign_task(task)
        
        assert claude_agent.state.current_task == task
        assert task.assigned_to == AgentRole.BACKEND
        assert task.status == TaskStatus.IN_PROGRESS
        
    @pytest.mark.asyncio
    async def test_complete_task(self, claude_agent):
        """Test task completion"""
        # Assign a task first
        task = Task(
            id="test-1",
            title="Implement feature",
            description="Add new endpoint"
        )
        await claude_agent.assign_task(task)
        
        # Complete the task
        completed = await claude_agent.complete_task()
        
        assert completed == task
        assert completed.status == TaskStatus.DONE
        assert claude_agent.state.current_task is None
        assert len(claude_agent.state.task_history) == 1
        assert claude_agent.state.task_history[0] == task
        
    @pytest.mark.asyncio
    async def test_complete_task_no_current(self, claude_agent):
        """Test completing task when no task is assigned"""
        completed = await claude_agent.complete_task()
        assert completed is None
        
    def test_get_status(self, claude_agent):
        """Test status retrieval"""
        status = claude_agent.get_status()
        
        assert status["role"] == AgentRole.BACKEND
        assert status["port"] == 8301
        assert status["model"] == "claude-3-sonnet-20240229"
        assert status["current_task"] is None
        assert status["task_history_count"] == 0
        assert status["total_tokens_used"] == 0
        assert "last_activity" in status
        assert status["health"] in ["active", "idle"]
        
    def test_get_status_with_task(self, claude_agent):
        """Test status with active task"""
        task = Task(
            id="test-1",
            title="Test task",
            description="Test"
        )
        claude_agent.state.current_task = task
        
        status = claude_agent.get_status()
        assert status["current_task"]["id"] == "test-1"
        assert status["current_task"]["title"] == "Test task"
        
    def test_all_role_prompts(self):
        """Test that all roles generate appropriate prompts"""
        roles_to_test = [
            (AgentRole.FRONTEND, "React components"),
            (AgentRole.BACKEND, "FastAPI services"),
            (AgentRole.DATABASE, "database schemas"),
            (AgentRole.QA, "Review PRs"),
            (AgentRole.BA, "technical tasks"),
            (AgentRole.TEAMLEAD, "architectural decisions")
        ]
        
        for role, expected_text in roles_to_test:
            settings = AgentSettings(
                role=role,
                port=8300,
                anthropic_api_key="test"
            )
            
            with patch('anthropic.Anthropic'):
                agent = ClaudeAgent(settings)
                prompt = agent._generate_default_prompt()
                
                assert "# COMMON" in prompt
                assert f"# ROLE: {role.value}" in prompt
                assert expected_text in prompt
                
    def test_state_persistence(self, claude_agent):
        """Test that agent state is properly maintained"""
        # Initial state
        assert claude_agent.state.total_tokens_used == 0
        assert len(claude_agent.state.messages) == 0
        
        # Simulate some activity
        claude_agent.state.total_tokens_used = 100
        claude_agent.state.messages.append({
            "timestamp": datetime.now().isoformat(),
            "user_message": "test",
            "assistant_response": "response",
            "tokens_used": 100
        })
        
        # Check state persists
        assert claude_agent.state.total_tokens_used == 100
        assert len(claude_agent.state.messages) == 1