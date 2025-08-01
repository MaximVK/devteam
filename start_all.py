#!/usr/bin/env python3
"""Start all DevTeam services"""

import os
import sys
import subprocess
import time

# Ensure we're in the right directory
os.chdir("/Users/maxim/dev/experimental/devteam")

# Activate virtual environment
activate_cmd = "source .venv/bin/activate && "

# Kill existing processes
print("🧹 Cleaning up existing processes...")
ports = [8301, 8302, 8303, 8304, 8305, 8306, 8000]
for port in ports:
    os.system(f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true")

time.sleep(2)

# Start agents
print("\n🤖 Starting agents...")
agents = [
    ("backend", 8301),
    ("frontend", 8302),
    ("database", 8303),
    ("qa", 8304),
    ("ba", 8305),
    ("teamlead", 8306)
]

for role, port in agents:
    cmd = f'AGENT_ROLE={role.upper()} {activate_cmd}python agents/run_agent.py > logs/{role}.log 2>&1 &'
    os.makedirs("logs", exist_ok=True)
    os.system(cmd)
    print(f"  ✅ {role} agent starting on port {port}")
    time.sleep(2)

# Start orchestrator
print("\n🎯 Starting orchestrator...")
cmd = f'{activate_cmd}python -m core.orchestrator > logs/orchestrator.log 2>&1 &'
os.system(cmd)
print("  ✅ Orchestrator started")

# Start web backend
print("\n🌐 Starting web backend...")
cmd = f'{activate_cmd}python -m uvicorn web.backend:app --host 0.0.0.0 --port 8000 > logs/web.log 2>&1 &'
os.system(cmd)
print("  ✅ Web backend started on port 8000")

print("\n✅ All services started!")
print("\n📊 Check status:")
print("  - Web Dashboard: http://localhost:3000")
print("  - API Docs: http://localhost:8000/docs")
print("  - Logs: ./logs/")
print("\n🛑 To stop: kill processes or run ./stop.sh")