#!/bin/bash
# Universal DevTeam startup script

echo "🚀 Starting DevTeam System"
echo "=========================="

# Change to project directory
cd /Users/maxim/dev/experimental/devteam

# Activate virtual environment
source .venv/bin/activate

# Create logs directory if it doesn't exist
mkdir -p logs

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
for port in 8301 8302 8303 8304 8305 8306 8000 3000 8500; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done

# Kill all related processes
pkill -f "python agents/run_" 2>/dev/null || true
pkill -f "uvicorn web.backend:app" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "start_telegram_bridge.py" 2>/dev/null || true
pkill -f "tool_server.py" 2>/dev/null || true
pkill -f "telegram_bridge" 2>/dev/null || true
pkill -f "tail -f logs" 2>/dev/null || true

sleep 2

# Detect which mode to use
echo ""
echo "🔍 Detecting configuration..."

WORKSPACE_DIR="${DEVTEAM_WORKSPACE:-$HOME/devteam-workspace}"
USE_WORKSPACE_MODE=false
AGENT_SCRIPT="agents/run_agent.py"

# Check for new workspace configuration
if [ -f "$WORKSPACE_DIR/workspace_config.json" ]; then
    echo "  📁 Found workspace configuration at: $WORKSPACE_DIR"
    USE_WORKSPACE_MODE=true
# Check for legacy workspace configuration
elif [ -f "config/agent_workspace.json" ] && [ -d "$HOME/dev/agent-workspace/devteam" ]; then
    echo "  📁 Using legacy workspace-aware agents"
    AGENT_SCRIPT="agents/run_agent_with_workspace.py"
else
    echo "  📦 Using standard agents"
fi

# Start agents
echo ""
echo "🤖 Starting AI Agents..."

if [ "$USE_WORKSPACE_MODE" = true ]; then
    # Get active agents from workspace config
    ACTIVE_AGENTS=$(python -c "
import json
from pathlib import Path
config_path = Path('$WORKSPACE_DIR') / 'workspace_config.json'
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
        for role in config.get('active_agents', {}).keys():
            print(role)
" 2>/dev/null)
    
    if [ -z "$ACTIVE_AGENTS" ]; then
        echo "  ⚠️  No active agents found in workspace"
        echo "  Please configure agents through the web interface first"
    else
        for role in $ACTIVE_AGENTS; do
            echo "  Starting $role agent..."
            python agents/run_workspace_agent.py $role --workspace "$WORKSPACE_DIR" > logs/${role}.log 2>&1 &
            echo "  ✅ $role agent started"
            sleep 1
        done
    fi
else
    # Start all standard agents
    AGENT_ROLE=BACKEND python $AGENT_SCRIPT > logs/backend.log 2>&1 &
    echo "  ✅ Backend agent started (port 8301)"
    sleep 1
    
    AGENT_ROLE=FRONTEND python $AGENT_SCRIPT > logs/frontend.log 2>&1 &
    echo "  ✅ Frontend agent started (port 8302)"
    sleep 1
    
    AGENT_ROLE=DATABASE python $AGENT_SCRIPT > logs/database.log 2>&1 &
    echo "  ✅ Database agent started (port 8303)"
    sleep 1
    
    AGENT_ROLE=QA python $AGENT_SCRIPT > logs/qa.log 2>&1 &
    echo "  ✅ QA agent started (port 8304)"
    sleep 1
    
    AGENT_ROLE=BA python $AGENT_SCRIPT > logs/ba.log 2>&1 &
    echo "  ✅ BA agent started (port 8305)"
    sleep 1
    
    AGENT_ROLE=TEAMLEAD python $AGENT_SCRIPT > logs/teamlead.log 2>&1 &
    echo "  ✅ Team Lead agent started (port 8306)"
    sleep 2
fi

# Start tool server
echo ""
echo "🔧 Starting Tool Server..."
python tool_server.py > logs/tool_server.log 2>&1 &
echo "  ✅ Tool server started (port 8500)"
sleep 2

# Start web backend
echo ""
echo "🌐 Starting Web Backend..."
python -m uvicorn web.backend:app --host 0.0.0.0 --port 8000 --reload > logs/web-backend.log 2>&1 &
echo "  ✅ Web backend API started (port 8000)"
sleep 2

# Start web frontend
echo ""
echo "🎨 Starting Web Frontend..."
cd web/frontend
npm run dev > ../../logs/web-frontend.log 2>&1 &
cd ../..
echo "  ✅ Web frontend started (port 3000)"
sleep 3

# Start Telegram bridge if configured
echo ""
echo "📱 Checking Telegram configuration..."

HAS_TELEGRAM=false
if [ "$USE_WORKSPACE_MODE" = true ] && [ -f "$WORKSPACE_DIR/workspace_config.json" ]; then
    if grep -q '"telegram_bot_token": "[^"]\+' "$WORKSPACE_DIR/workspace_config.json" 2>/dev/null; then
        HAS_TELEGRAM=true
    fi
elif [ -f ".env" ] && grep -q "TELEGRAM_BOT_TOKEN=.\+" .env 2>/dev/null; then
    HAS_TELEGRAM=true
fi

if [ "$HAS_TELEGRAM" = true ]; then
    python start_telegram_bridge.py > logs/telegram_bridge.log 2>&1 &
    echo "  ✅ Telegram bridge started"
else
    echo "  ⚠️  Telegram not configured (skipping)"
fi
sleep 2

# Check status
echo ""
echo "🔍 Checking services..."
sleep 3
python check_status.py

echo ""
echo "==========================================="
echo "✅ DevTeam is ready!"
echo "==========================================="
echo ""
echo "📊 Access Points:"
echo "  • Web Dashboard: http://localhost:3000"
echo "  • API Documentation: http://localhost:8000/docs"

if [ "$USE_WORKSPACE_MODE" = true ]; then
    echo ""
    echo "📁 Workspace: $WORKSPACE_DIR"
fi

echo ""
echo "📁 Logs: ./logs/"
echo "🛑 To stop all: ./stop.sh"
echo ""
echo "Press Ctrl+C to view logs (services will keep running)..."

# Tail logs
tail -f logs/*.log