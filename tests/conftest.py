"""Shared pytest fixtures and configuration"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import os
from datetime import datetime

from core.claude_agent import ClaudeAgent, AgentSettings, AgentRole
from core.telegram_bridge import TelegramBridge, TelegramSettings
from core.github_sync import GitHubSync, GitHubSettings
from core.orchestrator import AgentOrchestrator


@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client"""
    with patch('anthropic.Anthropic') as mock:
        client = Mock()
        mock.return_value = client
        
        # Mock message response
        response = Mock()
        response.content = [Mock(text="Test response from Claude")]
        response.usage = Mock(input_tokens=10, output_tokens=20)
        
        client.messages.create = Mock(return_value=response)
        yield client


@pytest.fixture
def agent_settings(temp_dir):
    """Create test agent settings"""
    return AgentSettings(
        role=AgentRole.BACKEND,
        port=8301,
        model="claude-3-sonnet-20240229",
        claude_file=str(temp_dir / "claude.md"),
        anthropic_api_key="test-api-key"
    )


@pytest.fixture
def claude_agent(agent_settings, mock_anthropic_client):
    """Create a test Claude agent"""
    # Create claude.md file
    Path(agent_settings.claude_file).write_text("# Test prompt")
    
    with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
        agent = ClaudeAgent(agent_settings)
        yield agent


@pytest.fixture
def telegram_settings():
    """Create test Telegram settings"""
    return TelegramSettings(
        bot_token="test-bot-token",
        channel_id="test-channel-id",
        allowed_users=[12345]
    )


@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot"""
    with patch('telegram.ext.Application') as mock_app:
        app = AsyncMock()
        builder = Mock()
        token_builder = Mock()
        
        # Setup builder chain
        mock_app.builder.return_value = builder
        builder.token.return_value = token_builder
        token_builder.build.return_value = app
        
        # Mock bot and application methods
        app.bot = AsyncMock()
        app.bot.send_message = AsyncMock()
        app.initialize = AsyncMock()
        app.start = AsyncMock()
        app.updater = AsyncMock()
        app.updater.start_polling = AsyncMock()
        app.updater.stop = AsyncMock()
        app.stop = AsyncMock()
        app.shutdown = AsyncMock()
        
        yield app


@pytest.fixture
def telegram_bridge(telegram_settings, mock_telegram_bot):
    """Create a test Telegram bridge"""
    with patch('telegram.ext.Application') as mock_app:
        # Setup the mock to return our mocked bot
        builder = Mock()
        token_builder = Mock()
        mock_app.builder.return_value = builder
        builder.token.return_value = token_builder
        token_builder.build.return_value = mock_telegram_bot
        
        bridge = TelegramBridge(telegram_settings)
        yield bridge


@pytest.fixture
def github_settings():
    """Create test GitHub settings"""
    return GitHubSettings(
        token="test-github-token",
        repo_name="test-repo",
        organization="test-org"
    )


@pytest.fixture
def mock_github():
    """Mock GitHub client"""
    with patch('github.Github') as mock_github:
        github = Mock()
        repo = Mock()
        org = Mock()
        user = Mock()
        
        mock_github.return_value = github
        github.get_organization.return_value = org
        github.get_user.return_value = user
        org.get_repo.return_value = repo
        user.get_repo.return_value = repo
        
        # Mock issue
        issue = Mock()
        issue.number = 1
        issue.title = "Test issue"
        issue.body = "Test description"
        issue.labels = [Mock(name="role:backend")]
        issue.assignee = None
        issue.state = "open"
        issue.created_at = issue.updated_at = datetime.now()
        
        repo.get_issues.return_value = [issue]
        repo.create_issue.return_value = issue
        repo.get_issue.return_value = issue
        
        # Mock PR
        pr = Mock()
        pr.number = 1
        pr.user = Mock(login="test-user")
        pr.mergeable = True
        
        repo.create_pull.return_value = pr
        repo.get_pull.return_value = pr
        
        yield github, repo


@pytest.fixture
def github_sync(github_settings, mock_github):
    """Create a test GitHub sync"""
    with patch('github.Github', return_value=mock_github[0]):
        with patch.object(GitHubSync, '_get_repo', return_value=mock_github[1]):
            sync = GitHubSync(github_settings)
            sync.repo = mock_github[1]
            yield sync


@pytest.fixture
def orchestrator(temp_dir):
    """Create a test orchestrator"""
    return AgentOrchestrator(config_dir=temp_dir / "config")


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for API calls"""
    client = AsyncMock()
    
    # Mock successful responses
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"status": "ok"}
    
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    
    return client


@pytest.fixture
def fastapi_test_client():
    """Create FastAPI test client"""
    from fastapi.testclient import TestClient
    from web.backend import app
    
    return TestClient(app)


@pytest.fixture
def mock_env_vars():
    """Set up test environment variables"""
    env_vars = {
        "ANTHROPIC_API_KEY": "test-api-key",
        "TELEGRAM_BOT_TOKEN": "test-bot-token",
        "GITHUB_TOKEN": "test-github-token"
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars