#!/bin/bash
# Stop all DevTeam services

echo "🛑 Stopping DevTeam services..."
echo "=============================="

# Kill processes on all ports
ports=(8301 8302 8303 8304 8305 8306 8000 3000)
services=("Backend Agent" "Frontend Agent" "Database Agent" "QA Agent" "BA Agent" "Team Lead" "Web Backend" "Web Frontend")

for i in ${!ports[@]}; do
    port=${ports[$i]}
    service=${services[$i]}
    
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "  Stopping $service (port $port)..."
        lsof -ti:$port | xargs kill -9 2>/dev/null
    fi
done

# Also kill any Python processes related to agents
pkill -f "python agents/run_agent.py" 2>/dev/null || true
pkill -f "uvicorn web.backend:app" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

echo ""
echo "✅ All services stopped."
echo ""
echo "To start again: ./start-devteam.sh"