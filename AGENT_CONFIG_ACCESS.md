# How to Access Agent Configuration Page

## Prerequisites

1. Make sure you're in the correct directory:
   ```bash
   cd ~/dev/experimental/devteam
   ```

2. Start the DevTeam services:
   ```bash
   ./devteam.sh
   ```

3. Make sure the frontend is running (port 3000):
   - Check if it's already running: `lsof -i :3000`
   - If not, run: `cd web/frontend && npm run dev`

4. Make sure the backend is running (port 8000):
   - Check if it's already running: `lsof -i :8000`
   - If not, run: `cd web && python backend.py`

## Accessing Agent Configuration

### Method 1: Through Project Dashboard (Recommended)

1. Open your browser and go to: http://localhost:3000
2. Navigate to the **Projects** page (click "Projects" in the left menu)
3. You'll see your current project with agent cards
4. On each agent card, you can:
   - **Click the agent name** (it's now clickable with blue hover effect)
   - **Click "View Details" button**
5. This takes you to: `/projects/{projectId}/agents/{agentId}`

### Method 2: Through Agents Page

1. Go to http://localhost:3000/agents
2. Look for the **blue Settings icon** (⚙️) on each agent card
3. Click it to go to that agent's configuration
4. Note: This only works if you have a current project selected

### Method 3: Direct URL

If you know your project ID and agent ID, you can go directly to:
```
http://localhost:3000/projects/{projectId}/agents/{agentId}
```

Example:
```
http://localhost:3000/projects/devteam/agents/frontend-maksimka
```

## What You'll See on the Agent Configuration Page

The page has 4 tabs:

1. **Settings Tab**:
   - Basic settings (model, tokens, temperature)
   - Resource limits (memory, CPU)
   - Permissions (internet, packages, git)
   - Allowed paths (files the agent can access)
   - Allowed commands (commands the agent can run)
   - Environment variables
   - System prompt additions

2. **Logs Tab**:
   - Real-time agent logs
   - Refresh button to update

3. **Commands Tab**:
   - History of commands executed by the agent

4. **History Tab**:
   - Conversation history with the agent

## Troubleshooting

If you can't see the Settings icon on the Agents page:
1. Make sure you have a project selected
2. Check browser console for errors (F12 → Console)
3. Refresh the page

If the agent detail page shows "Agent not found":
1. Make sure the agent exists in your current project
2. Check the URL format is correct
3. Try accessing through the Project Dashboard instead

## File Locations

- Agent Detail Component: `web/frontend/src/components/AgentDetail.tsx`
- Project Dashboard: `web/frontend/src/components/ProjectDashboard.tsx`
- API Configuration: `web/frontend/src/services/api.ts`
- Backend Endpoints: `web/backend.py` (lines 310-387)