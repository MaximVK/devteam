#!/usr/bin/env python3
"""Initialize the DevTeam system with all agents"""

import asyncio
import httpx
from config.settings import settings

async def init_system():
    """Initialize the system with agents"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # First check if backend is running
        try:
            response = await client.get(f"{base_url}/")
            print("✅ Web backend is running")
        except Exception as e:
            print(f"❌ Web backend not accessible: {e}")
            return
        
        # Initialize the system
        print("🔧 Initializing system...")
        init_data = {}
        
        # Add Telegram settings if configured
        if settings.is_telegram_configured():
            init_data["telegram_bot_token"] = settings.telegram_bot_token
            init_data["telegram_channel_id"] = settings.telegram_channel_id
            print("  - Telegram configured")
        
        # Add GitHub settings if configured
        if settings.is_github_configured():
            init_data["github_token"] = settings.github_token
            init_data["github_repo"] = settings.github_repo
            print("  - GitHub configured")
        
        try:
            response = await client.post(f"{base_url}/api/system/initialize", json=init_data)
            if response.status_code == 200:
                print("✅ System initialized successfully")
            else:
                print(f"❌ Failed to initialize: {response.text}")
        except Exception as e:
            print(f"❌ Error initializing: {e}")
        
        # Create agents
        agents = ["backend", "frontend", "database", "qa", "ba", "teamlead"]
        
        for role in agents:
            print(f"🤖 Creating {role} agent...")
            agent_data = {
                "role": role,
                "port": settings.get_agent_port(role),
                "model": settings.default_model
            }
            
            try:
                response = await client.post(f"{base_url}/api/agents", json=agent_data)
                if response.status_code == 200:
                    print(f"  ✅ {role} agent created")
                else:
                    print(f"  ❌ Failed to create {role}: {response.text}")
            except Exception as e:
                print(f"  ❌ Error creating {role}: {e}")
        
        # Check final status
        response = await client.get(f"{base_url}/api/agents")
        agents_list = response.json()
        print(f"\n✅ System ready with {len(agents_list)} agents")
        
        # Show agent endpoints
        print("\n📍 Agent endpoints:")
        for agent in agents_list:
            print(f"  - {agent['role']}: http://localhost:{agent.get('port', 'unknown')}")

if __name__ == "__main__":
    asyncio.run(init_system())