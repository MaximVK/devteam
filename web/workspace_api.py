"""API endpoints for workspace management"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import os

from core.workspace_config import WorkspaceConfig, GitConfig, TokenConfig
from core.workspace_manager import WorkspaceManager
from core.template_manager import TemplateManager


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class WorkspaceInitRequest(BaseModel):
    """Request model for workspace initialization"""
    working_folder: str
    repository_url: str
    base_branch: str = "main-agents"
    anthropic_api_key: str
    github_token: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_channel_id: Optional[str] = None
    git_user_name: str = "DevTeam Agents"
    git_user_email: str = "agents@devteam.local"


class WorkspaceStatusResponse(BaseModel):
    """Response model for workspace status"""
    initialized: bool
    working_folder: Optional[str] = None
    maestro_exists: bool = False
    available_roles: List[str] = Field(default_factory=list)
    active_agents: Dict[str, Any] = Field(default_factory=dict)


class CreateAgentRequest(BaseModel):
    """Request model for creating an agent"""
    role: str
    custom_description: Optional[str] = None


class RoleTemplateInfo(BaseModel):
    """Information about a role template"""
    role: str
    source: str  # "system" or "project"
    has_template: bool


@router.post("/check-directory")
async def check_directory(path: str = Body(...)) -> Dict[str, Any]:
    """Check if a directory exists and is writable"""
    try:
        directory = Path(path)
        exists = directory.exists()
        is_dir = directory.is_dir() if exists else False
        
        # Try to check if writable by creating parent dirs
        if not exists:
            try:
                # Check if parent directory is writable
                parent = directory.parent
                if parent.exists():
                    # Can we write to parent?
                    test_file = parent / f".devteam_test_{os.getpid()}"
                    try:
                        test_file.touch()
                        test_file.unlink()
                        writable = True
                    except:
                        writable = False
                else:
                    writable = False
            except:
                writable = False
        else:
            writable = os.access(str(directory), os.W_OK)
        
        return {
            "exists": exists,
            "is_directory": is_dir,
            "writable": writable,
            "path": str(directory),
            "parent": str(directory.parent),
            "suggestion": str(directory) if not exists else None
        }
    except Exception as e:
        return {
            "exists": False,
            "is_directory": False,
            "writable": False,
            "error": str(e)
        }


@router.get("/status")
async def get_workspace_status() -> WorkspaceStatusResponse:
    """Get current workspace status"""
    # Try to find existing workspace config
    home_workspace = Path.home() / "devteam-workspace"
    config = WorkspaceConfig.load(home_workspace)
    
    if config and config.is_initialized():
        template_manager = TemplateManager(config)
        return WorkspaceStatusResponse(
            initialized=True,
            working_folder=str(config.working_folder),
            maestro_exists=config.maestro_path.exists(),
            available_roles=template_manager.get_available_roles(),
            active_agents=config.active_agents
        )
    
    return WorkspaceStatusResponse(initialized=False)


@router.post("/initialize")
async def initialize_workspace(request: WorkspaceInitRequest) -> Dict[str, Any]:
    """Initialize a new workspace"""
    try:
        # Create configuration
        git_config = GitConfig(
            repository_url=request.repository_url,
            base_branch=request.base_branch,
            user_name=request.git_user_name,
            user_email=request.git_user_email
        )
        
        token_config = TokenConfig(
            anthropic_api_key=request.anthropic_api_key,
            github_token=request.github_token,
            telegram_bot_token=request.telegram_bot_token,
            telegram_channel_id=request.telegram_channel_id
        )
        
        config = WorkspaceConfig(
            working_folder=Path(request.working_folder),
            git_config=git_config,
            tokens=token_config
        )
        
        # Save configuration
        config.save()
        
        # Initialize maestro workspace
        workspace_manager = WorkspaceManager(config)
        if not workspace_manager.initialize_maestro():
            raise HTTPException(status_code=500, detail="Failed to initialize maestro workspace")
        
        # Get available roles
        template_manager = TemplateManager(config)
        available_roles = template_manager.get_available_roles()
        
        return {
            "success": True,
            "message": "Workspace initialized successfully",
            "working_folder": str(config.working_folder),
            "available_roles": available_roles
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles")
async def get_available_roles() -> List[RoleTemplateInfo]:
    """Get list of available roles and their templates"""
    # Load configuration
    home_workspace = Path.home() / "devteam-workspace"
    config = WorkspaceConfig.load(home_workspace)
    
    if not config:
        raise HTTPException(status_code=400, detail="Workspace not initialized")
    
    template_manager = TemplateManager(config)
    template_info = template_manager.get_template_info()
    
    roles = []
    for role, info in template_info.items():
        roles.append(RoleTemplateInfo(
            role=role,
            source=info["source"],
            has_template=True
        ))
    
    return roles


@router.post("/agents/create")
async def create_agent(request: CreateAgentRequest) -> Dict[str, Any]:
    """Create a new agent workspace"""
    # Load configuration
    home_workspace = Path.home() / "devteam-workspace"
    config = WorkspaceConfig.load(home_workspace)
    
    if not config:
        raise HTTPException(status_code=400, detail="Workspace not initialized")
    
    workspace_manager = WorkspaceManager(config)
    template_manager = TemplateManager(config)
    
    # Check if custom description provided for new role
    if request.custom_description and request.role not in template_manager.get_available_roles():
        # Create custom role template
        if not template_manager.create_custom_role(request.role, request.custom_description):
            raise HTTPException(status_code=500, detail="Failed to create custom role")
    
    # Initialize agent workspace
    if not workspace_manager.initialize_agent_workspace(request.role):
        raise HTTPException(status_code=500, detail="Failed to create agent workspace")
    
    # Update active agents in config
    config.active_agents[request.role] = {
        "workspace": str(config.get_agent_workspace(request.role)),
        "status": "active"
    }
    config.save()
    
    return {
        "success": True,
        "message": f"Agent workspace for {request.role} created successfully",
        "workspace_path": str(config.get_agent_workspace(request.role))
    }


@router.delete("/agents/{role}")
async def remove_agent(role: str) -> Dict[str, Any]:
    """Remove an agent workspace"""
    # Load configuration
    home_workspace = Path.home() / "devteam-workspace"
    config = WorkspaceConfig.load(home_workspace)
    
    if not config:
        raise HTTPException(status_code=400, detail="Workspace not initialized")
    
    workspace_manager = WorkspaceManager(config)
    
    # Remove agent workspace
    if not workspace_manager.cleanup_agent_workspace(role):
        raise HTTPException(status_code=500, detail="Failed to remove agent workspace")
    
    # Update config
    if role in config.active_agents:
        del config.active_agents[role]
        config.save()
    
    return {
        "success": True,
        "message": f"Agent workspace for {role} removed successfully"
    }


@router.post("/roles/create")
async def create_custom_role(
    role_name: str = Body(...),
    description: str = Body(...)
) -> Dict[str, Any]:
    """Create a custom role template"""
    # Load configuration
    home_workspace = Path.home() / "devteam-workspace"
    config = WorkspaceConfig.load(home_workspace)
    
    if not config:
        raise HTTPException(status_code=400, detail="Workspace not initialized")
    
    template_manager = TemplateManager(config)
    
    if not template_manager.create_custom_role(role_name, description):
        raise HTTPException(status_code=500, detail="Failed to create custom role")
    
    return {
        "success": True,
        "message": f"Custom role {role_name} created successfully"
    }