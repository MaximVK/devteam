#!/bin/bash
# Start all DevTeam agents and services

echo "🚀 Starting DevTeam System"
echo "========================="

# Activate virtual environment
source .venv/bin/activate

# Kill any existing processes on our ports
echo "🧹 Cleaning up existing processes..."
for port in 8301 8302 8303 8304 8305 8306 8000; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done

# Start each agent in the background
echo "🤖 Starting agents..."
AGENT_ROLE=backend python agents/run_agent.py &
echo "  ✅ Backend agent started on port 8301"
sleep 2

AGENT_ROLE=frontend python agents/run_agent.py &
echo "  ✅ Frontend agent started on port 8302"
sleep 2

AGENT_ROLE=database python agents/run_agent.py &
echo "  ✅ Database agent started on port 8303"
sleep 2

AGENT_ROLE=qa python agents/run_agent.py &
echo "  ✅ QA agent started on port 8304"
sleep 2

AGENT_ROLE=ba python agents/run_agent.py &
echo "  ✅ BA agent started on port 8305"
sleep 2

AGENT_ROLE=teamlead python agents/run_agent.py &
echo "  ✅ Team Lead agent started on port 8306"
sleep 2

# Start web backend
echo "🌐 Starting web backend..."
python -m uvicorn web.backend:app --host 0.0.0.0 --port 8000 --reload &
echo "  ✅ Web backend started on port 8000"

echo ""
echo "✅ All services started!"
echo ""
echo "📱 Telegram: Send messages to your group chat"
echo "   Use @backend, @frontend, @qa, @ba, @database, @teamlead"
echo ""
echo "🌐 Web Dashboard: http://localhost:8000"
echo ""
echo "🛑 To stop all services, run: ./stop.sh"
echo ""
echo "Press Ctrl+C to stop watching logs..."

# Keep the script running to show logs
wait