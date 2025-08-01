"""End-to-end integration tests"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from core.claude_agent import ClaudeAgent, AgentSettings, AgentRole, Task
from core.orchestrator import AgentOrchestrator
from agents.api import AgentAPI
from core.telegram_bridge import TelegramBridge, TelegramSettings
from core.github_sync import GitHubSync, GitHubSettings


class TestEndToEnd:
    """Test complete workflows end-to-end"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_agent_lifecycle(self, temp_dir, mock_anthropic_client):
        """Test complete agent lifecycle"""
        # Create orchestrator
        orchestrator = AgentOrchestrator(config_dir=temp_dir / "config")
        
        with patch('subprocess.Popen') as mock_popen:
            with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
                # Mock process
                mock_process = Mock()
                mock_process.pid = 12345
                mock_popen.return_value = mock_process
                
                # Mock agent readiness
                orchestrator._wait_for_agent = AsyncMock()
                
                # Create agent
                agent = await orchestrator.create_agent(
                    role=AgentRole.BACKEND,
                    model="claude-3-sonnet-20240229"
                )
                
                assert agent.role == AgentRole.BACKEND
                assert agent.status == "running"
                assert agent.pid == 12345
                
                # Verify files created
                env_file = Path(agent.env_file)
                assert env_file.exists()
                
                claude_file = temp_dir / "config" / "claude-backend.md"
                assert claude_file.exists()
                
                # Stop agent
                await orchestrator.stop_agent("backend")
                
                assert agent.status == "stopped"
                assert agent.pid is None
                
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_task_assignment_flow(self, temp_dir, mock_anthropic_client, mock_httpx_client):
        """Test task assignment and completion flow"""
        # Setup
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            # Create agent
            settings = AgentSettings(
                role=AgentRole.BACKEND,
                port=8301,
                anthropic_api_key="test-key",
                claude_file=str(temp_dir / "claude.md")
            )
            
            # Create claude.md
            Path(settings.claude_file).write_text("# Test")
            
            agent = ClaudeAgent(settings)
            
            # Create task
            task = Task(
                id="test-1",
                title="Implement feature",
                description="Add new endpoint"
            )
            
            # Assign task
            await agent.assign_task(task)
            
            assert agent.state.current_task == task
            assert task.status.value == "in_progress"
            
            # Process message with task context
            response = await agent.process_message(
                "How should I implement this?",
                {"task": task}
            )
            
            assert response == "Test response from Claude"
            
            # Complete task
            completed = await agent.complete_task()
            
            assert completed == task
            assert task.status.value == "done"
            assert agent.state.current_task is None
            assert len(agent.state.task_history) == 1
            
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_github_to_agent_flow(self, github_sync, orchestrator, mock_httpx_client):
        """Test GitHub issue to agent assignment flow"""
        # Setup orchestrator with GitHub
        orchestrator.github_sync = github_sync
        orchestrator.client = mock_httpx_client
        
        # Create mock agent
        from core.orchestrator import AgentProcess
        agent = AgentProcess(
            role=AgentRole.BACKEND,
            port=8301,
            env_file="test.env",
            status="running"
        )
        orchestrator.agents["backend"] = agent
        
        # Mock HTTP response for task assignment
        mock_httpx_client.post.return_value.status_code = 200
        
        # Run GitHub task assignment
        await orchestrator.assign_github_tasks()
        
        # Verify task was assigned
        mock_httpx_client.post.assert_called()
        call_args = mock_httpx_client.post.call_args
        assert "assign" in call_args[0][0]
        assert call_args[1]["json"]["github_issue_number"] == 1
        
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_telegram_to_agent_communication(self, telegram_bridge, mock_httpx_client):
        """Test Telegram to agent communication"""
        # Register agent
        telegram_bridge.registry.register("backend", "http://localhost:8301", 8301)
        telegram_bridge.client = mock_httpx_client
        
        # Mock agent response
        mock_httpx_client.post.return_value.json.return_value = {
            "response": "I'll implement that feature right away!"
        }
        
        # Simulate Telegram message
        update = Mock()
        update.message.text = "@backend implement user authentication"
        context = Mock()
        
        await telegram_bridge._handle_message(update, context)
        
        # Verify communication
        mock_httpx_client.post.assert_called_once()
        update.message.reply_text.assert_called_once()
        
        reply = update.message.reply_text.call_args[0][0]
        assert "BACKEND responds" in reply
        assert "I'll implement that feature" in reply
        
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_system_integration(self, temp_dir):
        """Test full system with all components"""
        # This would be a more comprehensive test in a real environment
        # For now, we verify that all components can be initialized together
        
        orchestrator = AgentOrchestrator(config_dir=temp_dir / "config")
        
        # Initialize with mock settings
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
                mock_telegram.return_value = AsyncMock()
                mock_github.return_value = Mock()
                
                await orchestrator.initialize(telegram_settings, github_settings)
                
                assert orchestrator.telegram_bridge is not None
                assert orchestrator.github_sync is not None
                
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_recovery(self, orchestrator, mock_httpx_client):
        """Test system error recovery"""
        orchestrator.client = mock_httpx_client
        
        # Create agent that will fail
        from core.orchestrator import AgentProcess
        agent = AgentProcess(
            role=AgentRole.BACKEND,
            port=8301,
            env_file="test.env",
            status="running"
        )
        orchestrator.agents["backend"] = agent
        
        # Make status check fail
        mock_httpx_client.get.side_effect = Exception("Connection refused")
        
        status = await orchestrator.get_agent_status("backend")
        
        # Should handle error gracefully
        assert status["status"] == "offline"
        assert status["role"] == "backend"
        
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_agent_operations(self, orchestrator):
        """Test concurrent operations on multiple agents"""
        # Mock multiple agents
        orchestrator.agents = {
            "backend": Mock(status="running"),
            "frontend": Mock(status="running"),
            "database": Mock(status="running")
        }
        
        # Mock get_agent_status to return different statuses
        statuses = [
            {"role": "backend", "health": "active"},
            {"role": "frontend", "health": "idle"},
            {"role": "database", "health": "active"}
        ]
        
        orchestrator.get_agent_status = AsyncMock(side_effect=statuses)
        
        # Get all statuses concurrently
        results = await orchestrator.get_all_agents_status()
        
        assert len(results) == 3
        assert all(r["role"] in ["backend", "frontend", "database"] for r in results)