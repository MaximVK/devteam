# Multi-Bot Telegram Architecture

## Configuration Changes

### 1. Update `.env` file structure:

```env
# Backend Agent Bot
BACKEND_TELEGRAM_BOT_TOKEN=your-backend-bot-token
BACKEND_TELEGRAM_CHANNEL_ID=your-backend-channel-id

# Frontend Agent Bot  
FRONTEND_TELEGRAM_BOT_TOKEN=your-frontend-bot-token
FRONTEND_TELEGRAM_CHANNEL_ID=your-frontend-channel-id

# Database Agent Bot
DATABASE_TELEGRAM_BOT_TOKEN=your-database-bot-token
DATABASE_TELEGRAM_CHANNEL_ID=your-database-channel-id

# QA Agent Bot
QA_TELEGRAM_BOT_TOKEN=your-qa-bot-token
QA_TELEGRAM_CHANNEL_ID=your-qa-channel-id

# BA Agent Bot
BA_TELEGRAM_BOT_TOKEN=your-ba-bot-token
BA_TELEGRAM_CHANNEL_ID=your-ba-channel-id

# Team Lead Bot
TEAMLEAD_TELEGRAM_BOT_TOKEN=your-teamlead-bot-token
TEAMLEAD_TELEGRAM_CHANNEL_ID=your-teamlead-channel-id
```

### 2. Updated Settings Structure:

```python
class AgentTelegramConfig(BaseSettings):
    """Per-agent Telegram configuration"""
    bot_token: Optional[str] = None
    channel_id: Optional[str] = None
    
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Per-agent Telegram configs
    backend_telegram: AgentTelegramConfig = Field(default_factory=AgentTelegramConfig)
    frontend_telegram: AgentTelegramConfig = Field(default_factory=AgentTelegramConfig)
    database_telegram: AgentTelegramConfig = Field(default_factory=AgentTelegramConfig)
    qa_telegram: AgentTelegramConfig = Field(default_factory=AgentTelegramConfig)
    ba_telegram: AgentTelegramConfig = Field(default_factory=AgentTelegramConfig)
    teamlead_telegram: AgentTelegramConfig = Field(default_factory=AgentTelegramConfig)
```

### 3. Architecture Benefits:

**Advantages of Multiple Bots:**
- Complete isolation between agents
- Different permissions per bot
- Separate channels for each agent
- Can have different bot commands per agent
- Better security (compromised bot only affects one agent)

**Disadvantages:**
- More complex setup (6 bots to create and configure)
- Harder to see cross-agent communication
- Need to manage multiple bot tokens
- More Telegram API rate limits to consider

## Implementation Approach

If you want to switch to multiple bots:

1. Each agent would have its own TelegramBridge instance
2. No need for @mention routing
3. Direct messages to each bot
4. Each bot can have specialized commands

## Recommendation

**For Development/Testing:** Single bot is simpler
**For Production:** Multiple bots provide better isolation and security

Which approach would you prefer? I can implement the multi-bot architecture if that better fits your needs.