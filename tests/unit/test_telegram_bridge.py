"""Unit tests for TelegramBridge"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from core.telegram_bridge import TelegramBridge, TelegramSettings, AgentRegistry


class TestTelegramBridge:
    """Test TelegramBridge functionality"""
    
    @pytest.mark.asyncio
    async def test_bridge_initialization(self, telegram_bridge, telegram_settings):
        """Test bridge initializes correctly"""
        assert telegram_bridge.settings == telegram_settings
        assert isinstance(telegram_bridge.registry, AgentRegistry)
        assert telegram_bridge.application is None
        
    def test_agent_registry(self):
        """Test agent registry functionality"""
        registry = AgentRegistry()
        
        # Register an agent
        registry.register("backend", "http://localhost:8301", 8301)
        
        assert "backend" in registry.agents
        assert registry.agents["backend"]["url"] == "http://localhost:8301"
        assert registry.agents["backend"]["port"] == 8301
        
        # Get agent URL
        url = registry.get_agent_url("backend")
        assert url == "http://localhost:8301"
        
        # Non-existent agent
        url = registry.get_agent_url("frontend")
        assert url is None
        
    @pytest.mark.asyncio
    async def test_start_bridge(self, telegram_settings):
        """Test starting the bridge"""
        with patch('telegram.ext.Application') as mock_app:
            # Setup mock
            app_instance = AsyncMock()
            # Mock the updater attribute
            app_instance.updater = AsyncMock()
            builder = Mock()
            token_builder = Mock()
            
            mock_app.builder.return_value = builder
            builder.token.return_value = token_builder
            token_builder.build.return_value = app_instance
            
            # Mock the bot to prevent real API calls
            mock_bot = AsyncMock()
            app_instance.bot = mock_bot
            
            # Create bridge
            bridge = TelegramBridge(telegram_settings)
            # Set the mocked application
            bridge.application = app_instance
            
            # Now start it
            await bridge.start()
            
            assert bridge.application is not None
            app_instance.initialize.assert_called_once()
            app_instance.start.assert_called_once()
            app_instance.updater.start_polling.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_stop_bridge(self, telegram_bridge, mock_telegram_bot):
        """Test stopping the bridge"""
        telegram_bridge.application = mock_telegram_bot
        
        await telegram_bridge.stop()
        
        mock_telegram_bot.updater.stop.assert_called_once()
        mock_telegram_bot.stop.assert_called_once()
        mock_telegram_bot.shutdown.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_handle_start_command(self, telegram_bridge):
        """Test /start command handler"""
        update = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        
        await telegram_bridge._handle_start(update, context)
        
        update.message.reply_text.assert_called_once()
        message = update.message.reply_text.call_args[0][0]
        assert "DevTeam Bot Started" in message
        assert "/agents" in message
        assert "/status" in message
        
    @pytest.mark.asyncio
    async def test_handle_status_command(self, telegram_bridge, mock_httpx_client):
        """Test /status command handler"""
        # Register some agents
        telegram_bridge.registry.register("backend", "http://localhost:8301", 8301)
        telegram_bridge.registry.register("frontend", "http://localhost:8302", 8302)
        
        # Mock httpx client responses
        telegram_bridge.client = mock_httpx_client
        mock_httpx_client.get.return_value.json.return_value = {
            "health": "active",
            "current_task": {"title": "Test task"}
        }
        
        update = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        
        await telegram_bridge._handle_status(update, context)
        
        update.message.reply_text.assert_called_once()
        message = update.message.reply_text.call_args[0][0]
        assert "BACKEND" in message
        assert "FRONTEND" in message
        assert "active" in message
        
    @pytest.mark.asyncio
    async def test_handle_status_with_errors(self, telegram_bridge, mock_httpx_client):
        """Test /status command with agent errors"""
        telegram_bridge.registry.register("backend", "http://localhost:8301", 8301)
        telegram_bridge.client = mock_httpx_client
        
        # Make the request fail
        mock_httpx_client.get.side_effect = Exception("Connection error")
        
        update = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        
        await telegram_bridge._handle_status(update, context)
        
        message = update.message.reply_text.call_args[0][0]
        assert "BACKEND" in message
        assert "Error: Connection error" in message
        
    @pytest.mark.asyncio
    async def test_handle_list_agents_empty(self, telegram_bridge):
        """Test /agents command with no agents"""
        update = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        
        await telegram_bridge._handle_list_agents(update, context)
        
        update.message.reply_text.assert_called_with("No agents registered yet.")
        
    @pytest.mark.asyncio
    async def test_handle_list_agents(self, telegram_bridge):
        """Test /agents command with registered agents"""
        telegram_bridge.registry.register("backend", "http://localhost:8301", 8301)
        telegram_bridge.registry.register("frontend", "http://localhost:8302", 8302)
        
        update = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        
        await telegram_bridge._handle_list_agents(update, context)
        
        message = update.message.reply_text.call_args[0][0]
        assert "backend" in message
        assert "8301" in message
        assert "frontend" in message
        assert "8302" in message
        
    @pytest.mark.asyncio
    async def test_handle_message_to_agent(self, telegram_bridge, mock_httpx_client):
        """Test routing messages to agents"""
        telegram_bridge.registry.register("backend", "http://localhost:8301", 8301)
        telegram_bridge.client = mock_httpx_client
        
        mock_httpx_client.post.return_value.json.return_value = {
            "response": "Agent response to your message"
        }
        
        update = Mock()
        update.message.text = "@backend implement user authentication"
        update.message.reply_text = AsyncMock()
        context = Mock()
        
        await telegram_bridge._handle_message(update, context)
        
        # Verify API call
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == "http://localhost:8301/ask"
        assert call_args[1]["json"]["message"] == "implement user authentication"
        
        # Verify response
        update.message.reply_text.assert_called_once()
        response_message = update.message.reply_text.call_args[0][0]
        assert "BACKEND responds" in response_message
        assert "Agent response to your message" in response_message
        
    @pytest.mark.asyncio
    async def test_handle_message_unknown_agent(self, telegram_bridge):
        """Test message to unknown agent"""
        update = Mock()
        update.message.text = "@unknown do something"
        update.message.reply_text = AsyncMock()
        context = Mock()
        
        await telegram_bridge._handle_message(update, context)
        
        update.message.reply_text.assert_called_with("❌ No agent found for role: unknown")
        
    @pytest.mark.asyncio
    async def test_handle_message_no_pattern(self, telegram_bridge):
        """Test message without @role pattern"""
        update = Mock()
        update.message.text = "Just a regular message"
        context = Mock()
        
        await telegram_bridge._handle_message(update, context)
        
        # Should not reply
        update.message.reply_text.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_handle_message_long_response(self, telegram_bridge, mock_httpx_client):
        """Test handling long responses that need splitting"""
        telegram_bridge.registry.register("backend", "http://localhost:8301", 8301)
        telegram_bridge.client = mock_httpx_client
        
        # Create a very long response
        long_response = "A" * 5000
        mock_httpx_client.post.return_value.json.return_value = {
            "response": long_response
        }
        
        update = Mock()
        update.message.text = "@backend test"
        update.message.reply_text = AsyncMock()
        context = Mock()
        
        await telegram_bridge._handle_message(update, context)
        
        # Should be called multiple times for long message
        assert update.message.reply_text.call_count > 1
        
    @pytest.mark.asyncio
    async def test_handle_message_api_error(self, telegram_bridge, mock_httpx_client):
        """Test handling API errors"""
        telegram_bridge.registry.register("backend", "http://localhost:8301", 8301)
        telegram_bridge.client = mock_httpx_client
        
        mock_httpx_client.post.side_effect = Exception("API Error")
        
        update = Mock()
        update.message.text = "@backend test"
        update.message.reply_text = AsyncMock()
        context = Mock()
        
        await telegram_bridge._handle_message(update, context)
        
        message = update.message.reply_text.call_args[0][0]
        assert "Error communicating with backend" in message
        assert "API Error" in message
        
    @pytest.mark.asyncio
    async def test_send_message(self, telegram_bridge, mock_telegram_bot):
        """Test sending messages"""
        telegram_bridge.application = mock_telegram_bot
        
        await telegram_bridge.send_message("Test message", "backend")
        
        mock_telegram_bot.bot.send_message.assert_called_once()
        call_args = mock_telegram_bot.bot.send_message.call_args
        assert call_args[1]["chat_id"] == "test-channel-id"
        assert "BACKEND" in call_args[1]["text"]
        assert "Test message" in call_args[1]["text"]
        
    @pytest.mark.asyncio
    async def test_send_message_no_role(self, telegram_bridge, mock_telegram_bot):
        """Test sending messages without role"""
        telegram_bridge.application = mock_telegram_bot
        
        await telegram_bridge.send_message("General message")
        
        call_args = mock_telegram_bot.bot.send_message.call_args
        assert call_args[1]["text"] == "General message"
        
    @pytest.mark.asyncio
    async def test_send_message_not_initialized(self, telegram_bridge):
        """Test sending message when bot not initialized"""
        telegram_bridge.application = None
        
        # Should not raise error
        await telegram_bridge.send_message("Test")
        
    def test_register_agent(self, telegram_bridge):
        """Test registering an agent"""
        telegram_bridge.register_agent("qa", 8303)
        
        assert "qa" in telegram_bridge.registry.agents
        assert telegram_bridge.registry.agents["qa"]["url"] == "http://localhost:8303"
        assert telegram_bridge.registry.agents["qa"]["port"] == 8303