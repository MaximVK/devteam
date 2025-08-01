import asyncio
import re
from typing import Dict, Optional, List, Callable, Any
from datetime import datetime
import logging

from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pydantic import BaseModel, Field
import httpx


logger = logging.getLogger(__name__)


class TelegramSettings(BaseModel):
    bot_token: str
    channel_id: str
    allowed_users: List[int] = []


class AgentRegistry(BaseModel):
    agents: Dict[str, Dict[str, Any]] = {}
    
    def register(self, role: str, url: str, port: int) -> None:
        self.agents[role] = {
            "url": url,
            "port": port,
            "health": "unknown",
            "last_check": datetime.now()
        }
        
    def get_agent_url(self, role: str) -> Optional[str]:
        agent = self.agents.get(role)
        return agent["url"] if agent else None


class TelegramBridge:
    def __init__(self, settings: TelegramSettings):
        self.settings = settings
        self.registry = AgentRegistry()
        self.application: Optional[Application] = None
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def start(self) -> None:
        self.application = Application.builder().token(self.settings.bot_token).build()
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("status", self._handle_status))
        self.application.add_handler(CommandHandler("agents", self._handle_list_agents))
        
        # Message handler for agent commands
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self._handle_message
        ))
        
        # Start polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
    async def stop(self) -> None:
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        await self.client.aclose()
        
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "👋 DevTeam Bot Started!\n\n"
            "Commands:\n"
            "/agents - List all agents\n"
            "/status - Check system status\n"
            "@role message - Send message to specific agent\n"
            "Example: @backend implement user authentication"
        )
        
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        status_text = "🔍 System Status\n\n"
        
        for role, agent in self.registry.agents.items():
            try:
                response = await self.client.get(f"{agent['url']}/status")
                if response.status_code == 200:
                    data = response.json()
                    health = data.get("health", "unknown")
                    current_task = data.get("current_task")
                    
                    status_text += f"**{role.upper()}** 🟢\n"
                    status_text += f"  Port: {agent['port']}\n"
                    status_text += f"  Health: {health}\n"
                    if current_task:
                        status_text += f"  Task: {current_task['title']}\n"
                else:
                    status_text += f"**{role.upper()}** 🔴 (HTTP {response.status_code})\n"
            except Exception as e:
                status_text += f"**{role.upper()}** 🔴 (Error: {str(e)})\n"
                
            status_text += "\n"
            
        await update.message.reply_text(status_text, parse_mode="Markdown")
        
    async def _handle_list_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.registry.agents:
            await update.message.reply_text("No agents registered yet.")
            return
            
        agents_text = "🤖 Registered Agents:\n\n"
        for role, agent in self.registry.agents.items():
            agents_text += f"• **{role}** - Port {agent['port']}\n"
            
        await update.message.reply_text(agents_text, parse_mode="Markdown")
        
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message.text
        
        # Check for @role pattern
        match = re.match(r'@(\w+)\s+(.*)', message)
        if not match:
            return
            
        role = match.group(1).lower()
        agent_message = match.group(2)
        
        # Find agent
        agent_url = self.registry.get_agent_url(role)
        if not agent_url:
            await update.message.reply_text(f"❌ No agent found for role: {role}")
            return
            
        # Send message to agent
        try:
            response = await self.client.post(
                f"{agent_url}/ask",
                json={"message": agent_message}
            )
            
            if response.status_code == 200:
                data = response.json()
                agent_response = data.get("response", "No response")
                
                # Format response
                reply = f"**{role.upper()}** responds:\n\n{agent_response}"
                
                # Split long messages
                if len(reply) > 4000:
                    parts = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
                    for part in parts:
                        await update.message.reply_text(part, parse_mode="Markdown")
                else:
                    await update.message.reply_text(reply, parse_mode="Markdown")
            else:
                await update.message.reply_text(
                    f"❌ Error from {role} agent: HTTP {response.status_code}"
                )
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error communicating with {role}: {str(e)}")
            
    async def send_message(self, message: str, role: Optional[str] = None) -> None:
        """Send a message to the Telegram channel"""
        if not self.application or not self.application.bot:
            logger.error("Bot not initialized")
            return
            
        formatted_message = message
        if role:
            formatted_message = f"**{role.upper()}**:\n{message}"
            
        try:
            await self.application.bot.send_message(
                chat_id=self.settings.channel_id,
                text=formatted_message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            
    def register_agent(self, role: str, port: int) -> None:
        """Register an agent with the bridge"""
        url = f"http://localhost:{port}"
        self.registry.register(role, url, port)
        logger.info(f"Registered agent {role} at {url}")