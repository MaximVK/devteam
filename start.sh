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

# Detect home directory configuration
echo ""
echo "🔍 Detecting configuration..."

HOME_DIR="${DEVTEAM_HOME:-$HOME/devteam-home}"

# Check for app configuration
if [ -f "$HOME_DIR/devteam.config.json" ]; then
    echo "  📁 Found home configuration at: $HOME_DIR"
else
    echo "  ⚠️  No home configuration found"
    echo "  Please run the web interface to set up DevTeam first"
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

# Note: Telegram bridge is now configured and started per-project
# through the web interface when starting project agents

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

if [ -f "$HOME_DIR/devteam.config.json" ]; then
    echo ""
    echo "📁 Home Directory: $HOME_DIR"
    echo ""
    echo "💡 To manage projects and agents:"
    echo "  • Visit http://localhost:3000"
    echo "  • Select a project to start its agents"
fi

echo ""
echo "📁 Logs: ./logs/"
echo "🛑 To stop all: ./stop.sh"
echo ""
echo "Press Ctrl+C to view logs (services will keep running)..."

# Tail logs
tail -f logs/*.log