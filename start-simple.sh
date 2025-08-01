#!/bin/bash
# Simple startup without workspace features

echo "🚀 Starting DevTeam (Simple Mode)"
echo "================================"

cd /Users/maxim/dev/experimental/devteam
source .venv/bin/activate

# Kill existing
for port in 8301 8302 8303 8304 8305 8306 8000 3000; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done

echo "Starting agents..."
AGENT_ROLE=BACKEND python agents/run_agent.py > logs/backend.log 2>&1 &
echo "✅ Backend agent"

AGENT_ROLE=FRONTEND python agents/run_agent.py > logs/frontend.log 2>&1 &
echo "✅ Frontend agent"

AGENT_ROLE=DATABASE python agents/run_agent.py > logs/database.log 2>&1 &
echo "✅ Database agent"

AGENT_ROLE=QA python agents/run_agent.py > logs/qa.log 2>&1 &
echo "✅ QA agent"

AGENT_ROLE=BA python agents/run_agent.py > logs/ba.log 2>&1 &
echo "✅ BA agent"

AGENT_ROLE=TEAMLEAD python agents/run_agent.py > logs/teamlead.log 2>&1 &
echo "✅ Team Lead agent"

sleep 3

echo "Starting web services..."
python -m uvicorn web.backend:app --host 0.0.0.0 --port 8000 > logs/web-backend.log 2>&1 &
echo "✅ Web backend"

cd web/frontend && npm run dev > ../../logs/web-frontend.log 2>&1 &
cd ../..
echo "✅ Web frontend"

sleep 2

echo "Starting Telegram bridge..."
# Set SSL certificates for macOS
export SSL_CERT_FILE=$(python -m certifi)
export REQUESTS_CA_BUNDLE=$(python -m certifi)
python start_telegram_bridge.py > logs/telegram_bridge.log 2>&1 &
echo "✅ Telegram bridge"

echo ""
echo "✅ System started!"
echo "Web UI: http://localhost:3000"
echo "API: http://localhost:8000/docs"
echo "Telegram: Send messages with @backend, @frontend, etc."