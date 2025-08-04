#!/usr/bin/env python3
"""Start all agents and register them with the orchestrator"""

import subprocess
import time
import requests
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from core.orchestrator import AgentOrchestrator

def wait_for_agent(port: int, max_retries: int = 30):
    """Wait for an agent to become available"""
    for i in range(max_retries):
        try:
            response = requests.get(f"http://localhost:{port}/")
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def main():
    print("🚀 Starting DevTeam Agents")
    print("========================")
    
    # Kill existing processes
    print("🧹 Cleaning up existing processes...")
    for port in [8301, 8302, 8303, 8304, 8305, 8306]:
        subprocess.run(f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true", shell=True)
    
    # Start each agent
    agents = [
        ("backend", 8301),
        ("frontend", 8302),
        ("database", 8303),
        ("qa", 8304),
        ("ba", 8305),
        ("teamlead", 8306),
    ]
    
    processes = []
    
    for role, port in agents:
        print(f"🤖 Starting {role} agent on port {port}...")
        env = {**subprocess.os.environ, "AGENT_ROLE": role.upper()}
        
        cmd = [
            sys.executable,
            "-m", "uvicorn",
            "agents.run_agent:app",
            "--host", "0.0.0.0",
            "--port", str(port)
        ]
        
        proc = subprocess.Popen(cmd, env=env, cwd="/Users/maxim/dev/experimental/devteam")
        processes.append(proc)
        
        # Wait for agent to start
        if wait_for_agent(port):
            print(f"  ✅ {role} agent started successfully")
        else:
            print(f"  ❌ {role} agent failed to start")
    
    print("\n✅ All agents started!")
    print("\nAgent endpoints:")
    for role, port in agents:
        print(f"  - {role}: http://localhost:{port}")
    
    print("\nPress Ctrl+C to stop all agents...")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
            # Check if any process died
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    role, port = agents[i]
                    print(f"⚠️  {role} agent stopped unexpectedly. Restarting...")
                    env = {**subprocess.os.environ, "AGENT_ROLE": role.upper()}
                    proc = subprocess.Popen(cmd, env=env, cwd="/Users/maxim/dev/experimental/devteam")
                    processes[i] = proc
    except KeyboardInterrupt:
        print("\n🛑 Stopping all agents...")
        for proc in processes:
            proc.terminate()
        for proc in processes:
            proc.wait()
        print("✅ All agents stopped.")

if __name__ == "__main__":
    main()