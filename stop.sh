#!/bin/bash
# Universal DevTeam stop script

echo "🛑 Stopping ALL DevTeam services..."
echo "==================================="

# Kill processes on all known ports
echo ""
echo "📡 Stopping services by port..."
ports=(8301 8302 8303 8304 8305 8306 8000 3000 8500)
services=("Backend Agent" "Frontend Agent" "Database Agent" "QA Agent" "BA Agent" "Team Lead" "Web Backend" "Web Frontend" "Tool Server")

for i in ${!ports[@]}; do
    port=${ports[$i]}
    service=${services[$i]}
    
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "  Stopping $service (port $port)..."
        lsof -ti:$port | xargs kill -9 2>/dev/null
    fi
done

echo ""
echo "🔄 Stopping processes by name..."

# Agent runners
echo "  Stopping agent runners..."
pkill -f "python agents/run_agent.py" 2>/dev/null || true
pkill -f "python agents/run_agent_with_workspace.py" 2>/dev/null || true
pkill -f "python agents/run_workspace_agent.py" 2>/dev/null || true
pkill -f "run_agent" 2>/dev/null || true

# Web services
echo "  Stopping web services..."
pkill -f "uvicorn web.backend:app" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "node.*vite" 2>/dev/null || true

# Infrastructure services
echo "  Stopping infrastructure services..."
pkill -f "start_telegram_bridge.py" 2>/dev/null || true
pkill -f "tool_server.py" 2>/dev/null || true
pkill -f "python check_status.py" 2>/dev/null || true
pkill -f "python start_all.py" 2>/dev/null || true

# More aggressive cleanup
echo "  Aggressive cleanup..."
pkill -9 -f "start_telegram_bridge" 2>/dev/null || true
pkill -9 -f "telegram_bridge" 2>/dev/null || true
pkill -9 -f "devteam.*agent" 2>/dev/null || true

# Clean up any monitoring processes
echo "  Stopping monitoring processes..."
pkill -f "tail -f logs" 2>/dev/null || true
pkill -f "tail.*logs" 2>/dev/null || true

# Verify all ports are free
echo ""
echo "🔍 Verifying services are stopped..."
all_stopped=true

for i in ${!ports[@]}; do
    port=${ports[$i]}
    service=${services[$i]}
    
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "  ⚠️  $service (port $port) is still running!"
        all_stopped=false
    fi
done

if [ "$all_stopped" = true ]; then
    echo "  ✅ All services successfully stopped"
else
    echo ""
    echo "  ⚠️  Some services may still be running"
    echo "  Run this script again or manually kill the processes"
fi

echo ""
echo "✅ Cleanup complete."
echo ""
echo "To start again: ./start.sh"