#!/bin/bash
# Stop all DevTeam services

echo "🛑 Stopping DevTeam services..."

# Kill processes on all our ports
for port in 8301 8302 8303 8304 8305 8306 8000; do
    echo "  Stopping service on port $port..."
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done

echo "✅ All services stopped."