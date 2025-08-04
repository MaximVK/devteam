#!/usr/bin/env python3
"""Base agent implementation for DevTeam"""

import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Request model for chat/ask endpoints"""
    message: str
    from_user: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response model for chat/ask endpoints"""
    response: str
    agent: str


class BaseAgent:
    """Base class for all DevTeam agents"""
    
    def __init__(self, agent_name: str, port: int, workspace_path: Path):
        self.agent_name = agent_name
        self.port = port
        self.workspace_path = workspace_path
        # Extract role from agent name (format: role-name)
        self.agent_role = agent_name.split('-')[0] if '-' in agent_name else 'agent'
        self.app = FastAPI(title=f"DevTeam Agent - {agent_name}")
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up FastAPI routes"""
        
        @self.app.get("/")
        async def root():
            return {
                "agent": self.agent_name,
                "status": "running",
                "workspace": str(self.workspace_path)
            }
        
        @self.app.get("/status")
        async def status():
            return {
                "agent": self.agent_name,
                "status": "healthy",
                "port": self.port
            }
        
        @self.app.post("/ask")
        async def ask(request: ChatRequest) -> ChatResponse:
            """Handle chat/ask requests"""
            try:
                response = await self.process_message(
                    request.message,
                    request.from_user,
                    request.context
                )
                return ChatResponse(
                    response=response,
                    agent=self.agent_name
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                return ChatResponse(
                    response=f"Error: {str(e)}",
                    agent=self.agent_name
                )
    
    async def process_message(self, message: str, from_user: Optional[str] = None, 
                            context: Optional[Dict[str, Any]] = None) -> str:
        """Process incoming message using Claude API"""
        import os
        from anthropic import AsyncAnthropic
        
        system_prompt = self.get_system_prompt()
        
        logger.info(f"Message from {from_user or 'unknown'}: {message}")
        
        # Get API key from environment
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            # Try to get from app config
            try:
                from pathlib import Path
                import json
                home_dir = Path(os.environ.get('DEVTEAM_HOME', Path.home() / 'devteam-home'))
                config_file = home_dir / 'config.json'
                if config_file.exists():
                    with open(config_file) as f:
                        config = json.load(f)
                        api_key = config.get('tokens', {}).get('anthropic_api_key')
            except Exception as e:
                logger.error(f"Failed to load API key from config: {e}")
        
        if not api_key:
            return f"[{self.agent_name}] Error: No Anthropic API key configured"
        
        try:
            # Initialize Claude client with custom httpx client to avoid proxy issues
            import anthropic
            import httpx
            
            # Create httpx client without proxy settings
            http_client = httpx.Client()
            
            # Create Anthropic client with custom http client
            client = anthropic.Anthropic(
                api_key=api_key,
                http_client=http_client
            )
            
            # Prepare messages
            messages = [
                {
                    "role": "user",
                    "content": message
                }
            ]
            
            # Add context if provided
            if context:
                messages[0]["content"] = f"Context: {context}\n\nMessage: {message}"
            
            # Call Claude API
            try:
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages
                )
                
                # Extract text from response
                if hasattr(response.content[0], 'text'):
                    return response.content[0].text
                else:
                    return str(response.content[0])
                    
            except anthropic.APIError as e:
                logger.error(f"Claude API error: {e}")
                return f"Sorry, I encountered an API error: {str(e)}"
            
        except ImportError as e:
            logger.error(f"Failed to import anthropic: {e}")
            return "Sorry, the Anthropic library is not properly installed."
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.exception("Full traceback:")
            return f"Sorry, I encountered an unexpected error: {type(e).__name__}: {str(e)}"
    
    def get_system_prompt(self) -> str:
        """Get system prompt for the agent - to be overridden"""
        return f"You are {self.agent_name}, a DevTeam agent."
    
    async def send_startup_message(self):
        """Send startup message to Telegram"""
        try:
            import aiohttp
            import os
            import json
            from pathlib import Path
            
            # Get project configuration to find Telegram settings
            project_id = os.environ.get('DEVTEAM_PROJECT_ID')
            home_dir = Path(os.environ.get('DEVTEAM_HOME', Path.home() / 'devteam-home'))
            
            if not project_id:
                logger.debug("No DEVTEAM_PROJECT_ID set, skipping startup message")
                return
                
            # Load project config to get Telegram settings
            project_path = home_dir / 'projects' / project_id
            project_config_file = project_path / 'project.config.json'
            
            if not project_config_file.exists():
                logger.debug(f"Project config not found at {project_config_file}")
                return
                
            with open(project_config_file) as f:
                project_config = json.load(f)
                
            telegram_config = project_config.get('telegram_config', {})
            if not telegram_config.get('enabled') or not telegram_config.get('bot_token'):
                logger.debug("Telegram not enabled or configured for project")
                return
                
            # Send message directly to Telegram API
            bot_token = telegram_config['bot_token']
            chat_id = telegram_config.get('group_id')
            
            if not chat_id:
                logger.debug("No Telegram group_id configured")
                return
                
            # Extract just the agent name (e.g., "Maksimka" from "frontend-Maksimka")
            agent_display_name = self.agent_name.split('-')[-1] if '-' in self.agent_name else self.agent_name
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": f"[{project_config.get('project_name', project_id)}] 👋 Hello, I'm {agent_display_name}! Ready to start working :)"
                }
                
                async with session.post(url, json=payload, ssl=False) as response:
                    if response.status == 200:
                        logger.info("Sent startup message to Telegram")
                    else:
                        logger.warning(f"Failed to send startup message: {response.status}")
                        
        except Exception as e:
            logger.debug(f"Could not send startup message: {e}")
    
    async def run(self):
        """Run the agent server"""
        logger.info(f"Starting {self.agent_name} on port {self.port}")
        logger.info(f"Workspace: {self.workspace_path}")
        
        # Ensure workspace exists
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Send startup message
        await self.send_startup_message()
        
        # Run the FastAPI server
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()