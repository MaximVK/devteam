# DevTeam Scripts

The DevTeam system now uses just two universal scripts for all operations:

## 🚀 start.sh
Universal startup script that automatically detects your configuration:
- Checks for workspace configuration at `$DEVTEAM_WORKSPACE` or `~/devteam-workspace`
- Falls back to legacy workspace-aware agents if found
- Falls back to standard agents as last resort

**Usage:**
```bash
./start.sh

# Or with custom workspace:
DEVTEAM_WORKSPACE=/path/to/workspace ./start.sh
```

## 🛑 stop.sh
Universal stop script that:
- Stops all services by port
- Kills processes by name pattern
- Verifies all services are stopped
- Provides feedback if any processes remain

**Usage:**
```bash
./stop.sh
```

## All Services Included

Both scripts handle ALL DevTeam services:

### Agent Services (Ports 8301-8306)
- Backend Agent
- Frontend Agent
- Database Agent
- QA Agent
- BA Agent
- Team Lead Agent

### Infrastructure Services
- Web Backend API (Port 8000)
- Web Frontend (Port 3000)
- Tool Server (Port 8500)
- Telegram Bridge (conditional)

### Support Processes
- Status checker
- Log monitoring

## Configuration Modes

The scripts automatically detect and use the appropriate configuration:

1. **Workspace Mode** (New)
   - Uses `workspace_config.json` from `$DEVTEAM_WORKSPACE`
   - Only starts configured agents
   - Full multi-project support

2. **Legacy Workspace Mode**
   - Uses `config/agent_workspace.json`
   - Agents have file awareness prompts

3. **Standard Mode**
   - Basic agent configuration
   - No workspace awareness

## Logs

All services write logs to the `./logs/` directory:
- `backend.log`, `frontend.log`, etc. - Agent logs
- `web-backend.log` - Web API logs
- `web-frontend.log` - Frontend dev server logs
- `tool_server.log` - Tool server logs
- `telegram_bridge.log` - Telegram integration logs

## Troubleshooting

If services don't stop properly:
1. Run `./stop.sh` again
2. Check for remaining processes: `ps aux | grep devteam`
3. Manually kill stubborn processes: `kill -9 <PID>`