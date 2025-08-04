#!/usr/bin/env python3
"""Telegram bridge for agent communication"""

import asyncio
import logging
import re
from typing import Dict, Optional, Set
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import aiohttp
import httpx
import ssl
import certifi

logger = logging.getLogger(__name__)


class TelegramBridge:
    """Bridge between Telegram and DevTeam agents"""
    
    def __init__(self, bot_token: str, channel_id: str):
        self.bot_token = bot_token
        self.channel_id = channel_id
        
        # Create httpx client without SSL verification for development
        # This bypasses the SSL certificate issues on macOS
        from telegram.request import HTTPXRequest
        import warnings
        import urllib3
        
        # Disable SSL warnings
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Monkey patch httpx to disable SSL
        original_client = httpx.AsyncClient
        
        def patched_client(*args, **kwargs):
            kwargs['verify'] = False
            return original_client(*args, **kwargs)
        
        httpx.AsyncClient = patched_client
        
        request = HTTPXRequest(
            http_version="1.1",
            connection_pool_size=8
        )
        
        self.app = Application.builder().token(bot_token).request(request).build()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Set up handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CommandHandler("status", self.handle_status))
        self.app.add_handler(CommandHandler("help", self.handle_help))
        
        # For receiving messages from agents
        self.agent_messages_queue = asyncio.Queue()
    
    async def start(self):
        """Start the Telegram bridge"""
        self.session = aiohttp.ClientSession()
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            # Send startup message
            await self.send_message("🤖 DevTeam Telegram Bridge started")
            
            # Keep running
            await asyncio.Event().wait()
        finally:
            if self.session:
                await self.session.close()
            await self.app.stop()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        if not update.message or not update.message.text:
            return
        
        text = update.message.text
        user = update.message.from_user
        
        # Look for @mentions
        mentions = re.findall(r'@(\w+)', text)
        if not mentions:
            return
        
        # Get agent URLs
        agent_urls = self.get_agent_urls()
        
        for mention in mentions:
            if mention.lower() in [name.lower() for name in agent_urls.keys()]:
                # Found an agent mention
                agent_name = next(name for name in agent_urls.keys() if name.lower() == mention.lower())
                agent_url = agent_urls[agent_name]
                
                # Extract message for this agent
                # Remove the @mention to get the actual message
                agent_message = text.replace(f'@{mention}', '').strip()
                
                if agent_message:
                    # Send to agent
                    await self.send_to_agent(
                        agent_url, 
                        agent_message, 
                        user.username or user.first_name,
                        update.message.message_id
                    )
    
    async def send_to_agent(self, agent_url: str, message: str, from_user: str, message_id: int):
        """Send message to an agent"""
        if not self.session:
            return
        
        try:
            # Prepare the message
            payload = {
                "message": message,
                "from_user": f"Telegram:{from_user}",
                "context": {
                    "source": "telegram",
                    "message_id": message_id
                }
            }
            
            # Send to agent
            async with self.session.post(agent_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    agent_response = result.get("response", "Agent responded but no message was returned")
                    
                    # Send response back to Telegram
                    await self.send_message(agent_response, reply_to=message_id)
                else:
                    logger.error(f"Agent returned status {response.status}")
                    await self.send_message(f"❌ Agent is not responding (status: {response.status})", reply_to=message_id)
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to agent: {e}")
            await self.send_message(f"❌ Could not connect to agent", reply_to=message_id)
        except Exception as e:
            logger.error(f"Error sending to agent: {e}")
            await self.send_message(f"❌ Error: {str(e)}", reply_to=message_id)
    
    async def send_message(self, text: str, reply_to: Optional[int] = None) -> None:
        """Send message to Telegram channel"""
        try:
            bot = Bot(self.bot_token)
            
            # Telegram has a 4096 character limit for messages
            max_length = 4000  # Leave some buffer
            
            if len(text) <= max_length:
                await bot.send_message(
                    chat_id=self.channel_id,
                    text=text,
                    reply_to_message_id=reply_to
                )
            else:
                # Split long messages
                parts = []
                current_part = ""
                
                # Try to split by paragraphs first
                paragraphs = text.split('\n\n')
                for paragraph in paragraphs:
                    if len(current_part) + len(paragraph) + 2 <= max_length:
                        if current_part:
                            current_part += "\n\n"
                        current_part += paragraph
                    else:
                        if current_part:
                            parts.append(current_part)
                        current_part = paragraph
                
                if current_part:
                    parts.append(current_part)
                
                # Send each part
                for i, part in enumerate(parts):
                    await bot.send_message(
                        chat_id=self.channel_id,
                        text=part + (f"\n\n[{i+1}/{len(parts)}]" if len(parts) > 1 else ""),
                        reply_to_message_id=reply_to if i == 0 else None
                    )
                    
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        agent_urls = self.get_agent_urls()
        
        status_lines = ["📊 *Agent Status*\n"]
        for agent_name, url in agent_urls.items():
            # Try to ping the agent
            if self.session:
                try:
                    async with self.session.get(f"{url.replace('/ask', '/status')}", timeout=2) as response:
                        if response.status == 200:
                            status_lines.append(f"✅ @{agent_name} - Online")
                        else:
                            status_lines.append(f"⚠️ @{agent_name} - Responding but unhealthy")
                except:
                    status_lines.append(f"❌ @{agent_name} - Offline")
            else:
                status_lines.append(f"❓ @{agent_name} - Unknown")
        
        await update.message.reply_text(
            "\n".join(status_lines),
            parse_mode="Markdown"
        )
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 *DevTeam Telegram Bridge Help*

*Commands:*
/status - Show agent status
/help - Show this help message

*Talking to agents:*
Mention an agent with @ followed by their name, then your message.
Example: @frontend Hello, can you help me?

*Available agents:*
"""
        agent_urls = self.get_agent_urls()
        for agent_name in agent_urls.keys():
            help_text += f"• @{agent_name}\n"
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    def get_agent_urls(self) -> Dict[str, str]:
        """Get agent URLs - to be overridden by subclasses"""
        return {}