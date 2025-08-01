#\!/bin/bash
# DevTeam CLI

case "$1" in
    start)
        ./start-devteam.sh
        ;;
    stop)
        ./stop-devteam.sh
        ;;
    status)
        source .venv/bin/activate && python check_status.py
        ;;
    logs)
        if [ -z "$2" ]; then
            echo "Available logs:"
            ls -1 logs/
        else
            tail -f logs/$2.log
        fi
        ;;
    test)
        echo "🧪 Testing Backend Agent..."
        curl -X POST http://localhost:8301/ask \
            -H "Content-Type: application/json" \
            -d '{"message": "Hello\! What is your role?"}'
        echo ""
        ;;
    *)
        echo "DevTeam - AI-powered development team"
        echo ""
        echo "Usage: ./devteam.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start   - Start all services"
        echo "  stop    - Stop all services"
        echo "  status  - Check service status"
        echo "  logs    - View logs (e.g., ./devteam.sh logs backend)"
        echo "  test    - Test agent communication"
        echo ""
        echo "Quick access:"
        echo "  Web UI: http://localhost:3000"
        echo "  API Docs: http://localhost:8000/docs"
        ;;
esac
EOF && chmod +x devteam.sh < /dev/null