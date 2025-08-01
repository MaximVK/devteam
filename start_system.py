#!/usr/bin/env python3
"""Start the DevTeam system"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings


def start_agent(role: str, port: int):
    """Start an agent process"""
    print(f"🚀 Starting {role} agent on port {port}...")
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "agents.run_agent:app",
        "--host", "0.0.0.0",
        "--port", str(port)
    ]
    
    # Set AGENT_ROLE environment variable
    env = {**os.environ, "AGENT_ROLE": role.upper()}
    
    return subprocess.Popen(cmd, env=env)


def start_web_backend():
    """Start the web backend"""
    print("🌐 Starting web backend on port 8000...")
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "web.backend:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]
    return subprocess.Popen(cmd)


async def main():
    """Main startup function"""
    print("🎯 DevTeam System Startup")
    print("=" * 60)
    
    # Check configuration
    print("🔍 Checking configuration...")
    print(f"✅ Anthropic API: {'Configured' if settings.anthropic_api_key else 'Missing'}")
    print(f"✅ Telegram: {'Configured' if settings.is_telegram_configured() else 'Not configured'}")
    print(f"✅ GitHub: {'Configured' if settings.is_github_configured() else 'Not configured'}")
    print()
    
    # Start agents
    processes = []
    agents = [
        ("backend", settings.backend_port),
        ("frontend", settings.frontend_port),
        ("database", settings.database_port),
        ("qa", settings.qa_port),
        ("ba", settings.ba_port),
        ("teamlead", settings.teamlead_port),
    ]
    
    for role, port in agents:
        proc = start_agent(role, port)
        processes.append(proc)
        time.sleep(2)  # Give each agent time to start
    
    # Start web backend
    web_proc = start_web_backend()
    processes.append(web_proc)
    
    print()
    print("✅ All services started!")
    print()
    print("📱 Telegram Bot: Send messages to your Telegram group")
    print("   Use @backend, @frontend, etc. to talk to specific agents")
    print()
    print("🌐 Web Dashboard: http://localhost:8000")
    print("   (Frontend will be at http://localhost:3000 if you run it separately)")
    print()
    print("Press Ctrl+C to stop all services...")
    
    try:
        # Wait for interrupt
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        for proc in processes:
            proc.terminate()
        
        # Wait for processes to terminate
        for proc in processes:
            proc.wait()
        
        print("✅ All services stopped.")


if __name__ == "__main__":
    import os
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass