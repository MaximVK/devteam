# DevTeam - Claude-Based Multi-Agent Development System

A local multi-agent development environment where AI agents powered by Claude API simulate real-world software development roles. Agents communicate through Telegram and GitHub, and are managed through a web interface.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 16+
- Poetry (Python package manager)
- Anthropic API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd devteam
```

2. Run the setup script:
```bash
./scripts/setup.py
```

3. Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

4. Start the backend server:
```bash
./start_backend.sh
```

5. Start the frontend (in a new terminal):
```bash
./start_frontend.sh
```

6. Open http://localhost:3000 in your browser

## 🏗️ Architecture

### Core Components

- **ClaudeAgent**: Core agent class with Claude API integration
- **AgentAPI**: REST API for each agent (FastAPI)
- **TelegramBridge**: Two-way Telegram communication
- **GitHubSync**: GitHub Issues and PR integration
- **AgentOrchestrator**: Manages agent lifecycle
- **WebUI**: React dashboard for system management

### Agent Roles

- **Frontend**: React, TypeScript, UI/UX
- **Backend**: FastAPI, business logic, APIs
- **Database**: Schema design, migrations, optimization
- **QA**: Testing, code review, quality assurance
- **BA**: Requirements analysis, task creation
- **TeamLead**: Architecture, coordination, reviews

## 📁 Project Structure

```
devteam/
├── agents/           # Agent API implementation
├── core/             # Core system components
├── web/              # Web interface (React + FastAPI)
│   ├── backend.py    # Dashboard API
│   └── frontend/     # React dashboard
├── config/           # Agent configurations
├── templates/        # CLAUDE.md templates
├── scripts/          # Setup and utility scripts
└── pyproject.toml    # Python dependencies
```

## 🔧 Configuration

### System Configuration

Configure the system through the web interface Settings page:

- **Anthropic API Key** (required)
- **Telegram Bot Token** (optional)
- **GitHub Token** (optional)

### Agent Configuration

Each agent has:
- Dedicated port (8301-8306)
- Role-specific CLAUDE.md prompt
- Environment configuration (.env.role)
- Claude model selection (Sonnet/Opus)

## 🤖 Using the System

### Creating Agents

1. Navigate to the Agents page
2. Click "Create Agent"
3. Select role and model
4. Configure optional integrations
5. Agent starts automatically

### Assigning Tasks

1. Go to the Tasks page
2. Click "Assign Task" or "Sync GitHub"
3. Select agent and provide task details
4. Monitor progress on Dashboard

### Telegram Commands

- `@backend implement user auth` - Send task to specific agent
- `/status` - Check system status
- `/agents` - List all agents

## 🛠️ Development

### Running Tests

```bash
poetry run pytest
```

### Adding New Agent Roles

1. Add role definition to `templates/claude_roles.yaml`
2. Run `./scripts/generate_claude.py --all`
3. Update `AgentRole` enum in `core/claude_agent.py`

### API Endpoints

Backend API (http://localhost:8000):
- `GET /api/agents` - List all agents
- `POST /api/agents` - Create new agent
- `GET /api/agents/{role}/status` - Agent status
- `POST /api/tasks/assign` - Assign task
- `WebSocket /ws` - Real-time updates

Agent API (http://localhost:{port}):
- `GET /status` - Agent status
- `POST /ask` - Send message to agent
- `POST /assign` - Assign task
- `GET /history` - Message/task history

## 📊 Monitoring

The dashboard provides:
- Real-time agent status
- Task progress tracking
- Token usage and costs
- Message history
- System health metrics

## 🔒 Security

- API keys stored in environment variables
- Agent isolation through separate processes
- No hardcoded credentials
- Secure GitHub/Telegram integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📝 License

[Your License Here]

## 🆘 Troubleshooting

### Agent won't start
- Check port availability
- Verify Anthropic API key
- Check logs in terminal

### Telegram not working
- Verify bot token
- Check channel permissions
- Ensure bot is in channel

### GitHub sync issues
- Verify token permissions
- Check repository access
- Review API rate limits