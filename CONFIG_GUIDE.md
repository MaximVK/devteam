# DevTeam Configuration Guide

## 📋 Configuration Files

The DevTeam system supports multiple configuration methods:

### 1. Environment Variables (`.env`)
**Recommended for production**

```bash
# Copy the example file
cp .env.example .env

# Edit with your values
nano .env
```

**Required variables:**
- `ANTHROPIC_API_KEY` - Your Anthropic API key

**Optional integrations:**
- `TELEGRAM_BOT_TOKEN` - For Telegram notifications
- `TELEGRAM_CHANNEL_ID` - Telegram channel/group ID
- `GITHUB_TOKEN` - For GitHub integration
- `GITHUB_REPO` - Your GitHub repository

### 2. JSON Configuration (`config/config.json`)
**Alternative configuration method**

```bash
# Copy the example file
cp config/config.json.example config/config.json

# Edit with your values
nano config/config.json
```

### 3. Python Settings (`config/settings.py`)
**Programmatic access to configuration**

```python
from config.settings import settings

# Access settings
api_key = settings.anthropic_api_key
is_telegram_enabled = settings.is_telegram_configured()
```

## 🚀 Quick Setup

### For Development:
```bash
# 1. Copy the example env file
cp .env.example .env

# 2. Add your Anthropic API key
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# 3. Run the setup script
./scripts/setup.py
```

### For Testing:
```bash
# Use the test configuration
cp .env.test .env

# Run tests
poetry run pytest
```

## 🔧 Configuration Options

### Core Settings
| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | ✅ | - |
| `DEFAULT_MODEL` | Claude model to use | ❌ | claude-3-sonnet-20240229 |

### Telegram Integration
| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | ❌ | - |
| `TELEGRAM_CHANNEL_ID` | Channel/group ID | ❌ | - |

### GitHub Integration
| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GITHUB_TOKEN` | Personal access token | ❌ | - |
| `GITHUB_REPO` | Repository (owner/name) | ❌ | - |
| `GITHUB_ORGANIZATION` | Organization name | ❌ | - |

### Agent Ports
| Variable | Description | Default |
|----------|-------------|---------|
| `BACKEND_PORT` | Backend agent port | 8301 |
| `FRONTEND_PORT` | Frontend agent port | 8302 |
| `DATABASE_PORT` | Database agent port | 8303 |
| `QA_PORT` | QA agent port | 8304 |
| `BA_PORT` | BA agent port | 8305 |
| `TEAMLEAD_PORT` | Team lead agent port | 8306 |

## 🔐 Security Notes

1. **Never commit `.env` files** - They contain secrets
2. **Use environment variables** for production
3. **Rotate API keys** regularly
4. **Use separate keys** for development and production

## 🧪 Test Configuration

For running tests with mocked services:

```bash
# Set test mode
export TEST_MODE=true
export MOCK_ANTHROPIC=true
export MOCK_TELEGRAM=true
export MOCK_GITHUB=true

# Run tests
poetry run pytest
```

## 📝 Per-Agent Configuration

Each agent can have its own configuration file:

```bash
config/
├── .env.backend
├── .env.frontend
├── .env.database
├── .env.qa
├── .env.ba
└── .env.teamlead
```

Example agent-specific config:
```env
# config/.env.backend
ROLE=backend
PORT=8301
MODEL=claude-3-sonnet-20240229
GITHUB_REPO=myorg/myproject
TELEGRAM_CHANNEL_ID=123456789
```

## 🔄 Configuration Priority

Settings are loaded in this order (later overrides earlier):
1. Default values in code
2. `config/config.json`
3. `.env` file
4. Environment variables
5. Command-line arguments

## 💡 Tips

- Use `.env` for secrets
- Use `config.json` for complex configurations
- Use environment variables in CI/CD
- Keep test configurations separate
- Document all custom settings