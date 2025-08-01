#!/bin/bash
# Complete DevTeam startup script

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
for port in 8301 8302 8303 8304 8305 8306 8000 3000; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done
sleep 2

# Start all agents
echo ""
echo "🤖 Starting AI Agents..."

# Check if workspace is configured
if [ -f "config/agent_workspace.json" ] && [ -d "$HOME/dev/agent-workspace/devteam" ]; then
    echo "  📁 Using workspace-aware agents"
    AGENT_SCRIPT="agents/run_agent_with_workspace.py"
else
    echo "  📦 Using standard agents"
    AGENT_SCRIPT="agents/run_agent.py"
fi

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

# Start Telegram bridge
echo ""
echo "📱 Starting Telegram Bridge..."
python start_telegram_bridge.py > logs/telegram_bridge.log 2>&1 &
echo "  ✅ Telegram bridge started"
sleep 2

# Check status
echo ""
echo "🔍 Checking services..."
sleep 3
python check_status.py

echo ""
echo "=========================================="
echo "✅ DevTeam is ready!"
echo "=========================================="
echo ""
echo "📊 Access Points:"
echo "  • Web Dashboard: http://localhost:3000"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Backend Agent API: http://localhost:8301"
echo "  • Frontend Agent API: http://localhost:8302"
echo "  • Database Agent API: http://localhost:8303"
echo "  • QA Agent API: http://localhost:8304"
echo "  • BA Agent API: http://localhost:8305"
echo "  • Team Lead API: http://localhost:8306"
echo ""
echo "📱 Telegram Commands:"
echo "  • @backend <message>"
echo "  • @frontend <message>"
echo "  • @database <message>"
echo "  • @qa <message>"
echo "  • @ba <message>"
echo "  • @teamlead <message>"
echo ""
echo "📁 Logs: ./logs/"
echo "🛑 To stop all: ./stop-devteam.sh"
echo ""
echo "Press Ctrl+C to view logs (services will keep running)..."

# Tail logs
tail -f logs/*.log