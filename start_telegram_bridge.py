#!/usr/bin/env python3
"""Start the Telegram bridge to route messages to agents"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from core.telegram_bridge import TelegramBridge, TelegramSettings
import httpx


class StandaloneAgentRegistry:
    """Registry that forwards to standalone agents"""
    
    def __init__(self):
        self.agent_ports = {
            "backend": 8301,
            "frontend": 8302,
            "database": 8303,
            "qa": 8304,
            "ba": 8305,
            "teamlead": 8306
        }
    
    def get_agent_url(self, role: str) -> str:
        """Get agent URL for a role"""
        port = self.agent_ports.get(role.lower())
        if port:
            return f"http://localhost:{port}"
        return None
    
    def register_agent(self, role: str, url: str):
        """Compatibility method - agents are already running"""
        pass
    
    async def route_message(self, role: str, message: str, sender: str) -> str:
        """Route message to the appropriate agent"""
        port = self.agent_ports.get(role.lower())
        
        if not port:
            return f"Unknown agent role: {role}. Available: {', '.join(self.agent_ports.keys())}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:{port}/ask",
                    json={"message": message, "context": {"sender": sender, "source": "telegram"}},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "No response from agent")
                else:
                    return f"Agent error: {response.status_code}"
        except Exception as e:
            return f"Failed to reach {role} agent: {str(e)}"


async def main():
    """Run the Telegram bridge"""
    if not settings.is_telegram_configured():
        print("❌ Telegram is not configured. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID")
        return
    
    print("🚀 Starting Telegram Bridge")
    print(f"Bot Token: {settings.telegram_bot_token[:20]}...")
    print(f"Channel ID: {settings.telegram_channel_id}")
    
    # Create settings
    telegram_settings = TelegramSettings(
        bot_token=settings.telegram_bot_token,
        channel_id=settings.telegram_channel_id
    )
    
    # Create bridge with custom registry
    bridge = TelegramBridge(telegram_settings)
    bridge.registry = StandaloneAgentRegistry()
    
    # Start the bridge
    try:
        await bridge.start()
        print("✅ Telegram bridge started successfully!")
        print("\nSend messages like:")
        print("  @backend create a user service")
        print("  @frontend change menu color to light grey")
        print("  @qa write tests for login")
        
        # Keep running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping Telegram bridge...")
        await bridge.stop()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())