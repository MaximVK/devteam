"""API endpoints for application-level management"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime
import os
import subprocess
import socket

from core.app_config import AppConfig, TokenConfig, GlobalSettings
from core.project_manager import ProjectManager
from core.project_config import GitConfig, ProjectConfig
from core.agent_manager import AgentManager


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/app", tags=["application"])


class AppInitRequest(BaseModel):
    """Request model for app initialization"""
    home_directory: str
    anthropic_api_key: str
    github_token: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_channel_id: Optional[str] = None


class AppStatusResponse(BaseModel):
    """Response model for app status"""
    initialized: bool
    home_directory: Optional[str] = None
    current_project: Optional[str] = None
    project_count: int = 0


class CreateProjectRequest(BaseModel):
    """Request model for creating a project"""
    project_name: str
    repository_url: str
    description: str = ""
    base_branch: str = "main-agents"
    override_git_config: bool = False
    git_user_name: Optional[str] = None
    git_user_email: Optional[str] = None
    initial_agents: List[Dict[str, str]] = Field(default_factory=list)


class SwitchProjectRequest(BaseModel):
    """Request model for switching projects"""
    project_id: str


class CreateAgentRequest(BaseModel):
    """Request model for creating an agent"""
    role: str
    name: str


# Global app config instance
_app_config: Optional[AppConfig] = None
_agent_manager: Optional[AgentManager] = None


def get_app_config() -> Optional[AppConfig]:
    """Get the current app configuration"""
    global _app_config
    
    if _app_config:
        return _app_config
    
    # Try to find existing config
    # Check common locations
    home_locations = [
        Path.home() / "devteam-home",
        Path.home() / ".devteam",
        Path("/tmp/devteam-home")  # For testing
    ]
    
    for location in home_locations:
        if location.exists():
            config = AppConfig.load(location)
            if config:
                _app_config = config
                return config
    
    return None


def set_app_config(config: AppConfig) -> None:
    """Set the app configuration"""
    global _app_config
    _app_config = config


def get_agent_manager() -> AgentManager:
    """Get or create the agent manager instance"""
    global _agent_manager
    if _agent_manager is None and _app_config is not None:
        _agent_manager = AgentManager(_app_config)
    return _agent_manager


@router.get("/status")
async def get_app_status() -> AppStatusResponse:
    """Get application initialization status"""
    config = get_app_config()
    
    if config:
        return AppStatusResponse(
            initialized=True,
            home_directory=str(config.home_directory),
            current_project=config.current_project,
            project_count=len(config.projects)
        )
    
    return AppStatusResponse(initialized=False)


@router.post("/initialize")
async def initialize_app(request: AppInitRequest) -> Dict[str, Any]:
    """Initialize the application with a home directory"""
    try:
        home_dir = Path(request.home_directory)
        
        # Check if already initialized
        existing_config = AppConfig.load(home_dir)
        if existing_config:
            raise HTTPException(
                status_code=400,
                detail=f"Home directory already initialized at {home_dir}"
            )
        
        # Create token configuration
        tokens = TokenConfig(
            anthropic_api_key=request.anthropic_api_key,
            github_token=request.github_token,
            telegram_bot_token=request.telegram_bot_token,
            telegram_channel_id=request.telegram_channel_id
        )
        
        # Initialize home directory
        config = AppConfig.initialize_home(home_dir, tokens)
        set_app_config(config)
        
        return {
            "success": True,
            "message": "Application initialized successfully",
            "home_directory": str(config.home_directory)
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to initialize app: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_app_configuration() -> Dict[str, Any]:
    """Get application configuration (excluding sensitive data)"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    return {
        "version": config.version,
        "home_directory": str(config.home_directory),
        "primary_folder": str(config.primary_folder) if config.primary_folder else None,
        "tokens": {
            "anthropic_api_key": config.tokens.anthropic_api_key,
            "github_token": config.tokens.github_token,
            "telegram_bot_token": config.tokens.telegram_bot_token,
            "telegram_channel_id": config.tokens.telegram_channel_id
        },
        "current_project": config.current_project,
        "global_settings": config.global_settings.model_dump(),
        "predefined_roles": config.predefined_roles,
        "project_count": len(config.projects)
    }


class AppConfigUpdateRequest(BaseModel):
    """Request model for updating app configuration"""
    home_directory: Optional[str] = None
    primary_folder: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    github_token: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_channel_id: Optional[str] = None
    global_settings: Optional[GlobalSettings] = None
    predefined_roles: Optional[List[str]] = None


@router.put("/config")
async def update_app_configuration(request: AppConfigUpdateRequest) -> Dict[str, Any]:
    """Update application configuration"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    # Update home directory if provided (requires moving config)
    if request.home_directory and str(config.home_directory) != request.home_directory:
        # This is a complex operation - we need to move the entire DevTeam setup
        # For now, we'll just update the path without moving files
        # TODO: Implement proper migration logic
        raise HTTPException(
            status_code=400,
            detail="Changing home directory requires manual migration of DevTeam files"
        )
    
    # Update primary folder
    if request.primary_folder is not None:
        config.primary_folder = Path(request.primary_folder) if request.primary_folder else None
    
    # Update tokens
    if request.anthropic_api_key is not None:
        config.tokens.anthropic_api_key = request.anthropic_api_key
    
    if request.github_token is not None:
        config.tokens.github_token = request.github_token
    
    if request.telegram_bot_token is not None:
        config.tokens.telegram_bot_token = request.telegram_bot_token
    
    if request.telegram_channel_id is not None:
        config.tokens.telegram_channel_id = request.telegram_channel_id
    
    if request.global_settings:
        config.global_settings = request.global_settings
    
    if request.predefined_roles:
        config.predefined_roles = request.predefined_roles
    
    config.save()
    
    return {
        "success": True,
        "message": "Configuration updated successfully"
    }


@router.get("/projects")
async def list_projects() -> List[Dict[str, Any]]:
    """List all projects"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    project_manager = ProjectManager(config)
    return project_manager.list_projects()


@router.post("/projects")
async def create_project(request: CreateProjectRequest) -> Dict[str, Any]:
    """Create a new project"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    project_manager = ProjectManager(config)
    
    # Prepare git config if overriding
    git_config = None
    if request.override_git_config and request.git_user_name and request.git_user_email:
        git_config = GitConfig(
            user_name=request.git_user_name,
            user_email=request.git_user_email
        )
    
    try:
        project_id = project_manager.create_project(
            project_name=request.project_name,
            repository_url=request.repository_url,
            description=request.description,
            base_branch=request.base_branch,
            git_config=git_config,
            initial_agents=request.initial_agents
        )
        
        # Set as current project
        config.set_current_project(project_id)
        
        return {
            "success": True,
            "project_id": project_id,
            "message": f"Project '{request.project_name}' created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def get_project_details(project_id: str) -> Dict[str, Any]:
    """Get details of a specific project"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    project_manager = ProjectManager(config)
    project_config = project_manager.get_project(project_id)
    
    if not project_config:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_info = config.projects.get(project_id)
    
    return {
        "id": project_id,
        "name": project_config.project_name,
        "folder_name": project_config.folder_name,
        "description": project_config.description,
        "repository": project_config.repository.model_dump(),
        "agent_count": len(project_config.active_agents),
        "agents": {
            agent_id: {
                "role": agent.role,
                "name": agent.name,
                "status": agent.status,
                "last_active": agent.last_active.isoformat()
            }
            for agent_id, agent in project_config.active_agents.items()
        },
        "telegram_config": project_config.telegram_config.model_dump(),
        "created_at": project_info.created_at.isoformat() if project_info else None,
        "last_accessed": project_info.last_accessed.isoformat() if project_info else None,
        "is_current": project_id == config.current_project
    }


@router.post("/projects/{project_id}/switch")
async def switch_to_project(project_id: str) -> Dict[str, Any]:
    """Switch to a different project"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    project_manager = ProjectManager(config)
    
    if project_manager.switch_project(project_id):
        return {
            "success": True,
            "message": f"Switched to project {project_id}",
            "current_project": project_id
        }
    else:
        raise HTTPException(status_code=404, detail="Project not found")


@router.delete("/projects/{project_id}")
async def archive_project(project_id: str) -> Dict[str, Any]:
    """Archive a project"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    project_manager = ProjectManager(config)
    
    if project_manager.archive_project(project_id):
        return {
            "success": True,
            "message": f"Project {project_id} archived successfully"
        }
    else:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post("/projects/{project_id}/agents")
async def create_project_agent(project_id: str, request: CreateAgentRequest) -> Dict[str, Any]:
    """Create an agent for a project"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    project_manager = ProjectManager(config)
    
    agent_id = project_manager.create_agent(project_id, request.role, request.name)
    
    if agent_id:
        return {
            "success": True,
            "agent_id": agent_id,
            "message": f"Agent '{request.name}' created successfully"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to create agent")


@router.delete("/projects/{project_id}/agents/{agent_id}")
async def remove_project_agent(project_id: str, agent_id: str) -> Dict[str, Any]:
    """Remove an agent from a project"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    project_manager = ProjectManager(config)
    
    if project_manager.remove_agent(project_id, agent_id):
        return {
            "success": True,
            "message": f"Agent {agent_id} removed successfully"
        }
    else:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/projects/{project_id}/agents/start")
async def start_project_agents(project_id: str) -> Dict[str, Any]:
    """Start all agents for a project"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    if project_id not in config.projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    agent_manager = get_agent_manager()
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not available")
    
    try:
        results = agent_manager.start_project_agents(project_id)
        return {
            "success": True,
            "message": f"Started agents for project {project_id}",
            "results": results
        }
    except Exception as e:
        logger.error(f"Failed to start agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/agents/stop")
async def stop_project_agents(project_id: str) -> Dict[str, Any]:
    """Stop all agents for a project"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    agent_manager = get_agent_manager()
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not available")
    
    try:
        results = agent_manager.stop_project_agents(project_id)
        return {
            "success": True,
            "message": f"Stopped agents for project {project_id}",
            "results": results
        }
    except Exception as e:
        logger.error(f"Failed to stop agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/agents/{agent_id}/start")
async def start_single_agent(project_id: str, agent_id: str) -> Dict[str, Any]:
    """Start a single agent"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    agent_manager = get_agent_manager()
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not available")
    
    # Get project info to resolve path
    if project_id not in config.projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_info = config.projects[project_id]
    project_path = config.home_directory / project_info.path
    project_config = ProjectConfig.load(project_path)
    
    if not project_config:
        raise HTTPException(status_code=404, detail="Project configuration not found")
    
    if agent_id not in project_config.active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Start just this agent
    try:
        agent_info = project_config.active_agents[agent_id]
        env = os.environ.copy()
        env['DEVTEAM_PROJECT_ID'] = project_id
        env['DEVTEAM_AGENT_ID'] = agent_id
        env['DEVTEAM_AGENT_ROLE'] = agent_info.role
        env['DEVTEAM_AGENT_NAME'] = agent_info.name
        env['DEVTEAM_HOME'] = str(config.home_directory)
        
        # Pass API key if available
        if config.tokens.anthropic_api_key:
            env['ANTHROPIC_API_KEY'] = config.tokens.anthropic_api_key
        
        # Allocate port dynamically
        if project_id not in agent_manager.allocated_ports:
            agent_manager.allocated_ports[project_id] = {}
        
        # Try to reuse previously allocated port or get a new one
        if agent_id in agent_manager.allocated_ports[project_id]:
            port = agent_manager.allocated_ports[project_id][agent_id]
            # Verify it's still available
            import socket
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
            except OSError:
                # Port is taken, allocate a new one
                port = agent_manager._find_available_port()
                agent_manager.allocated_ports[project_id][agent_id] = port
        else:
            port = agent_manager._find_available_port()
            agent_manager.allocated_ports[project_id][agent_id] = port
        
        env['AGENT_PORT'] = str(port)
        agent_manager._save_port_file()
        
        # Start agent process
        log_file = config.home_directory / "logs" / f"{project_id}_{agent_id}.log"
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'w') as log:
            # Get the devteam directory
            devteam_dir = Path(__file__).parent.parent
            # Use the poetry environment Python
            python_path = devteam_dir / '.venv' / 'bin' / 'python'
            if not python_path.exists():
                python_path = 'python'
            process = subprocess.Popen(
                [str(python_path), 'agents/run_project_agent.py'],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=str(devteam_dir)
            )
        
        # Track the process
        if project_id not in agent_manager.running_processes:
            agent_manager.running_processes[project_id] = {}
        agent_manager.running_processes[project_id][agent_id] = process
        agent_manager._save_pid_file()
        
        # Start Telegram bridge if configured and not already running
        if (project_config.telegram_config.bot_token and 
            project_config.telegram_config.enabled and
            "telegram_bridge" not in agent_manager.running_processes.get(project_id, {})):
            try:
                agent_manager._start_telegram_bridge(project_id, project_config)
                logger.info(f"Started Telegram bridge for project {project_id}")
            except Exception as e:
                logger.error(f"Failed to start Telegram bridge: {e}")
                # Don't fail the agent start if telegram fails
        
        return {
            "success": True,
            "pid": process.pid,
            "message": f"Agent {agent_info.name} started successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start agent: {str(e)}")


@router.post("/projects/{project_id}/agents/{agent_id}/stop")
async def stop_single_agent(project_id: str, agent_id: str) -> Dict[str, Any]:
    """Stop a single agent"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    agent_manager = get_agent_manager()
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not available")
    
    # Stop just this agent
    if project_id not in agent_manager.running_processes:
        return {
            "success": True,
            "message": "Agent was not running"
        }
    
    if agent_id not in agent_manager.running_processes[project_id]:
        return {
            "success": True,
            "message": "Agent was not running"
        }
    
    try:
        process = agent_manager.running_processes[project_id][agent_id]
        if hasattr(process, 'terminate'):
            process.terminate()
            # Wait a bit for graceful shutdown
            import time
            time.sleep(0.5)
            if process.poll() is None:
                process.kill()
        elif isinstance(process, int):
            # It's a PID
            os.kill(process, 15)  # SIGTERM
            import time
            time.sleep(0.5)
            try:
                os.kill(process, 9)  # SIGKILL if still running
            except ProcessLookupError:
                pass
        
        # Remove from tracking
        del agent_manager.running_processes[project_id][agent_id]
        if not agent_manager.running_processes[project_id]:
            del agent_manager.running_processes[project_id]
        
        agent_manager._save_pid_file()
        
        return {
            "success": True,
            "message": "Agent stopped successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop agent: {str(e)}")


@router.get("/projects/{project_id}/agents/status")
async def get_project_agents_status(project_id: str) -> Dict[str, Any]:
    """Get status of all agents in a project"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    agent_manager = get_agent_manager()
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not available")
    
    status = agent_manager.get_project_status(project_id)
    return {
        "project_id": project_id,
        "agents": status
    }


@router.get("/agents/status")
async def get_all_agents_status() -> Dict[str, Any]:
    """Get status of all agents across all projects"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    agent_manager = get_agent_manager()
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not available")
    
    status = agent_manager.get_all_projects_status()
    return {
        "projects": status
    }


@router.get("/projects/{project_id}/agents/{agent_id}/logs")
async def get_agent_logs(project_id: str, agent_id: str, lines: int = 100) -> Dict[str, Any]:
    """Get logs for a specific agent"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    # Construct log file path
    log_file = config.home_directory / "logs" / f"{project_id}_{agent_id}.log"
    
    if not log_file.exists():
        return {
            "exists": False,
            "content": "",
            "message": "Log file not found"
        }
    
    try:
        # Read last N lines
        with open(log_file, 'r') as f:
            log_lines = f.readlines()
            
        # Get last N lines
        last_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines
        
        return {
            "exists": True,
            "content": "".join(last_lines),
            "total_lines": len(log_lines),
            "returned_lines": len(last_lines)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {str(e)}")


class TelegramConfigRequest(BaseModel):
    """Request model for updating Telegram configuration"""
    bot_token: str
    group_id: str
    enabled: bool


class ProjectConfigRequest(BaseModel):
    """Request model for updating project configuration"""
    name: str
    description: str
    folder_name: Optional[str] = None


@router.put("/projects/{project_id}/telegram")
async def update_project_telegram(project_id: str, request: TelegramConfigRequest) -> Dict[str, Any]:
    """Update Telegram configuration for a project"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    project_manager = ProjectManager(config)
    project_config = project_manager.get_project(project_id)
    
    if not project_config:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update telegram config
    project_config.telegram_config.bot_token = request.bot_token
    project_config.telegram_config.group_id = request.group_id
    project_config.telegram_config.enabled = request.enabled
    
    # Save project config
    project_config.save()
    
    return {
        "success": True,
        "message": "Telegram configuration updated"
    }


@router.put("/projects/{project_id}/config")
async def update_project_config(project_id: str, request: ProjectConfigRequest) -> Dict[str, Any]:
    """Update project configuration"""
    config = get_app_config()
    if not config:
        raise HTTPException(status_code=400, detail="Application not initialized")
    
    project_manager = ProjectManager(config)
    project_config = project_manager.get_project(project_id)
    
    if not project_config:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update project config
    project_config.project_name = request.name
    project_config.description = request.description
    if request.folder_name is not None:
        project_config.folder_name = request.folder_name
    
    # Save project config
    project_config.save()
    
    # Also update in app config
    if project_id in config.projects:
        config.projects[project_id].name = request.name
        # Note: We don't move the actual folder here, that would require additional logic
        config.save()
    
    return {
        "success": True,
        "message": "Project configuration updated"
    }