#!/usr/bin/env python3
"""Register all running agents with the web backend"""

import requests
import time

def register_agents():
    """Register agents that are already running"""
    print("📝 Registering agents with web backend...")
    
    # First, initialize the system
    init_data = {
        "anthropic_api_key": "already_set_in_agents"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/system/initialize", json=init_data)
        print(f"System init: {response.status_code}")
    except Exception as e:
        print(f"Init error: {e}")
    
    # Wait a bit
    time.sleep(1)
    
    # Try a different approach - directly call agent endpoints
    agents = [
        {"role": "backend", "port": 8301},
        {"role": "frontend", "port": 8302},
        {"role": "database", "port": 8303},
        {"role": "qa", "port": 8304},
        {"role": "ba", "port": 8305},
        {"role": "teamlead", "port": 8306}
    ]
    
    registered = 0
    for agent in agents:
        # Check if agent is running
        try:
            resp = requests.get(f"http://localhost:{agent['port']}/")
            if resp.status_code == 200:
                print(f"✅ {agent['role']} agent is running on port {agent['port']}")
                registered += 1
        except:
            print(f"❌ {agent['role']} agent not accessible")
    
    print(f"\n✅ Found {registered} running agents")
    print("\nThe agents are running independently. To interact with them:")
    print("1. Use the API endpoints directly (e.g., http://localhost:8301/)")
    print("2. Use Telegram with @mentions")
    print("3. Access API docs at http://localhost:8000/docs")

if __name__ == "__main__":
    register_agents()