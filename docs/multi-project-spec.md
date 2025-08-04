# Multi-Project Architecture Specification

## Overview

Transform the current single-project DevTeam system into a multi-project workspace that allows managing multiple development projects, each with its own repository, agents, and configuration.

## Directory Structure

```
~/devteam-home/                    # User-selected home folder
├── devteam.config.json           # Application-level configuration
├── projects/                     # All projects directory
│   ├── project-1/               # Individual project
│   │   ├── project.config.json  # Project-specific configuration
│   │   ├── maestro/            # Human working directory (cloned repo)
│   │   ├── agents/             # Agent workspaces
│   │   │   ├── backend/        # Backend agent workspace
│   │   │   ├── frontend/       # Frontend agent workspace
│   │   │   └── ...            # Other agent workspaces
│   │   └── templates/          # Project-specific CLAUDE.md templates
│   │       ├── backend.md
│   │       └── frontend.md
│   ├── project-2/
│   │   └── ...
│   └── ...
└── system-templates/            # Default CLAUDE.md templates
    ├── backend.md
    ├── frontend.md
    └── ...
```

## Configuration Files

### Application-Level Configuration (`devteam.config.json`)

```json
{
  "version": "2.0.0",
  "home_directory": "/Users/username/devteam-home",
  "current_project": "project-1",
  "global_settings": {
    "default_base_branch": "main-agents",
    "default_git_config": {
      "user_name": "DevTeam Agents",
      "user_email": "agents@devteam.local"
    },
    "ui_preferences": {
      "theme": "light",
      "sidebar_collapsed": false,
      "default_view": "dashboard"
    }
  },
  "tokens": {
    "anthropic_api_key": "sk-ant-...",
    "github_token": "ghp_...",
    "telegram_bot_token": "...",
    "telegram_channel_id": "..."
  },
  "predefined_roles": [
    "backend",
    "frontend", 
    "database",
    "qa",
    "ba",
    "teamlead",
    "devops",
    "security"
  ],
  "projects": {
    "project-1": {
      "name": "E-commerce Platform",
      "path": "projects/project-1",
      "created_at": "2025-01-15T10:00:00Z",
      "last_accessed": "2025-01-20T15:30:00Z"
    },
    "project-2": {
      "name": "Analytics Dashboard",
      "path": "projects/project-2",
      "created_at": "2025-01-18T14:00:00Z",
      "last_accessed": "2025-01-19T09:15:00Z"
    }
  }
}
```

### Project-Level Configuration (`project.config.json`)

```json
{
  "project_id": "project-1",
  "project_name": "E-commerce Platform",
  "description": "Multi-vendor e-commerce platform with AI recommendations",
  "repository": {
    "url": "https://github.com/company/ecommerce-platform.git",
    "base_branch": "main-agents",
    "default_branch": "main"
  },
  "git_config": {
    "user_name": "E-commerce DevTeam",
    "user_email": "ecommerce-agents@company.com"
  },
  "active_agents": {
    "backend-alex": {
      "role": "backend",
      "name": "Alex",
      "status": "active",
      "workspace": "agents/backend-alex",
      "current_branch": "feature/api-optimization",
      "last_active": "2025-01-20T15:00:00Z",
      "created_at": "2025-01-15T10:30:00Z"
    },
    "frontend-sarah": {
      "role": "frontend",
      "name": "Sarah",
      "status": "active",
      "workspace": "agents/frontend-sarah",
      "current_branch": "feature/responsive-design",
      "last_active": "2025-01-20T14:30:00Z",
      "created_at": "2025-01-15T11:00:00Z"
    }
  },
  "project_metadata": {
    "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL"],
    "team_size": 5,
    "started_date": "2025-01-15",
    "status": "active"
  },
  "custom_roles": {
    "api-specialist": {
      "description": "Specialist in REST API design and optimization",
      "template": "templates/api-specialist.md"
    }
  },
  "project_tokens": {
    "database_url": "postgresql://...",
    "api_keys": {
      "stripe": "sk_test_...",
      "sendgrid": "SG..."
    }
  }
}
```

## UI Flow

### 1. First-Time Setup
```
1. Launch application
2. Welcome screen: "Choose DevTeam Home Directory"
3. Directory picker with validation
4. Create initial structure:
   - devteam.config.json
   - projects/ directory
   - system-templates/ directory
5. Prompt for global tokens (Anthropic API key required)
6. Show main application UI
```

### 2. Main Application UI
```
┌─────────────────────────────────────────────────────────┐
│ DevTeam                              [Settings] [Logout] │
├─────────────────────────────────────────────────────────┤
│ ┌───────────────┬─────────────────────────────────────┐ │
│ │ Projects      │ E-commerce Platform                  │ │
│ │               │                                       │ │
│ │ + New Project │ Repository: github.com/company/...   │ │
│ │               │ Active Agents: 2                      │ │
│ │ ▼ Active      │                                       │ │
│ │   E-commerce  │ [Manage Agents] [Git Status]         │ │
│ │   Analytics   │                                       │ │
│ │               │ Agents:                               │ │
│ │ ▼ Archived    │ ┌─────────┬─────────┬─────────┐     │ │
│ │   Old Project │ │ Backend │Frontend │   QA    │     │ │
│ │               │ │ Active  │ Active  │Inactive │     │ │
│ │               │ └─────────┴─────────┴─────────┘     │ │
│ └───────────────┴─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 3. Create New Project Flow
```
1. Click "New Project"
2. Form:
   - Project Name
   - Description
   - Repository URL
   - Base Branch (default: main-agents)
   - Override Git Config? (checkbox)
   - Initial Agents to Create (multi-select)
3. Create project structure
4. Clone repository to maestro/
5. Initialize selected agents
6. Switch to new project view
```

## API Endpoints

### Application Management
- `GET /api/app/status` - Check if home directory is configured
- `POST /api/app/initialize` - Initialize home directory
- `GET /api/app/config` - Get application configuration
- `PUT /api/app/config` - Update application configuration

### Project Management
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{project_id}` - Get project details
- `PUT /api/projects/{project_id}` - Update project
- `DELETE /api/projects/{project_id}` - Archive/delete project
- `POST /api/projects/{project_id}/activate` - Switch to project

### Agent Management (Project-Scoped)
- `GET /api/projects/{project_id}/agents` - List project agents
- `POST /api/projects/{project_id}/agents` - Create agent
- `DELETE /api/projects/{project_id}/agents/{role}` - Remove agent

## Key Features

### 1. Project Isolation
- Each project has completely separate workspaces
- No cross-contamination between projects
- Agents work only within their project context

### 2. Token Management
- Global tokens (Anthropic, GitHub) at application level
- Project-specific tokens/secrets at project level
- Inheritance: projects use global tokens unless overridden

### 3. Template System
- System-wide default templates in home directory
- Project-specific template overrides
- Template discovery: project → system → built-in

### 4. Quick Project Switching
- Dropdown or sidebar for fast project switching
- Remember last active project
- Keyboard shortcuts (Cmd+P for project switcher)

### 5. Project Status Indicators
- Active/Inactive status
- Last accessed timestamp
- Number of active agents
- Git repository status

## Migration Strategy

For existing single-project setups:
1. Detect existing workspace on startup
2. Offer migration: "Convert to multi-project workspace?"
3. Create new structure
4. Move existing workspace to `projects/imported-project/`
5. Update configurations

## Benefits

1. **Organization**: Clear separation between projects
2. **Flexibility**: Different configurations per project
3. **Scalability**: Easy to add new projects
4. **Context**: Agents maintain project-specific knowledge
5. **Efficiency**: Quick switching between projects