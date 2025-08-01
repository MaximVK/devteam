#!/usr/bin/env python3
"""Test Telegram integration"""

import asyncio
from config.settings import settings
from core.telegram_bridge import TelegramBridge, TelegramSettings

async def test_telegram():
    print("🔍 Testing Telegram integration...")
    print(f"Bot Token: {settings.telegram_bot_token[:20]}...")
    print(f"Channel ID: {settings.telegram_channel_id}")
    
    if not settings.is_telegram_configured():
        print("❌ Telegram is not configured properly")
        return
    
    # Create settings
    telegram_settings = TelegramSettings(
        bot_token=settings.telegram_bot_token,
        channel_id=settings.telegram_channel_id
    )
    
    # Create bridge
    bridge = TelegramBridge(telegram_settings)
    
    # Test sending a message
    try:
        await bridge.send_message("🧪 Test message from DevTeam system")
        print("✅ Message sent successfully!")
        print("\nNow try sending a message to your Telegram group:")
        print("  @backend hello")
        print("  @frontend what's your status?")
        print("\nThe bot will route these to the appropriate agents.")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_telegram())