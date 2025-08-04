"""Project manager for handling multi-project operations"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from .app_config import AppConfig, TokenConfig
from .project_config import ProjectConfig, GitConfig, Repository
from .workspace_manager import WorkspaceManager
from .template_manager import TemplateManager


logger = logging.getLogger(__name__)


class ProjectManager:
    """Manages multiple DevTeam projects"""
    
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config
    
    def create_project(self, 
                      project_name: str,
                      repository_url: str,
                      description: str = "",
                      base_branch: str = "main-agents",
                      git_config: Optional[GitConfig] = None,
                      initial_agents: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Create a new project
        
        Args:
            project_name: Name of the project
            repository_url: Git repository URL
            description: Project description
            base_branch: Base branch for agents
            git_config: Optional git configuration (uses global if not provided)
            initial_agents: List of initial agents to create [{"role": "backend", "name": "Alex"}]
        
        Returns:
            project_id: The ID of the created project
        """
        # Create project configuration
        project_config = ProjectConfig.create(
            project_name=project_name,
            repository_url=repository_url,
            description=description,
            folder_name=None,  # Will be set based on project name
            base_branch=base_branch,
            git_config=git_config
        )
        
        # Create project directory using the project's folder name
        project_path = self.app_config.projects_directory / project_config.folder_name
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Set config path and save
        project_config.set_config_path(project_path / "project.config.json")
        project_config.save()
        
        # Create project subdirectories
        (project_path / "maestro").mkdir(exist_ok=True)
        (project_path / "agents").mkdir(exist_ok=True)
        (project_path / "templates").mkdir(exist_ok=True)
        
        # Add to app config
        self.app_config.add_project(
            project_config.project_id,
            project_name,
            f"projects/{project_config.folder_name}"
        )
        
        # Initialize maestro workspace
        try:
            self._initialize_maestro(project_path, project_config)
        except Exception as e:
            logger.error(f"Failed to initialize maestro: {e}")
            # Clean up on failure
            shutil.rmtree(project_path, ignore_errors=True)
            raise
        
        # Create initial agents if specified
        if initial_agents:
            for agent_spec in initial_agents:
                try:
                    self.create_agent(
                        project_config.project_id,
                        agent_spec["role"],
                        agent_spec["name"]
                    )
                except Exception as e:
                    logger.error(f"Failed to create agent {agent_spec}: {e}")
        
        return project_config.project_id
    
    def _initialize_maestro(self, project_path: Path, project_config: ProjectConfig) -> None:
        """Initialize the maestro workspace for a project"""
        maestro_path = project_path / "maestro"
        
        # Clone repository
        logger.info(f"Cloning repository to {maestro_path}")
        result = subprocess.run(
            ["git", "clone", project_config.repository.url, str(maestro_path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Failed to clone repository: {result.stderr}")
        
        # Configure git
        git_config = project_config.git_config or GitConfig(
            user_name=self.app_config.global_settings.default_git_config["user_name"],
            user_email=self.app_config.global_settings.default_git_config["user_email"]
        )
        
        subprocess.run(
            ["git", "config", "user.name", git_config.user_name],
            cwd=maestro_path,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.email", git_config.user_email],
            cwd=maestro_path,
            check=True
        )
        
        # Ensure base branch exists
        self._ensure_base_branch(maestro_path, project_config.repository.base_branch)
    
    def _ensure_base_branch(self, repo_path: Path, base_branch: str) -> None:
        """Ensure the base branch exists in the repository"""
        # Check if branch exists
        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        remote_branches = result.stdout.strip().split('\n')
        if f"origin/{base_branch}" in remote_branches:
            # Checkout existing branch
            subprocess.run(
                ["git", "checkout", base_branch],
                cwd=repo_path,
                check=True
            )
        else:
            # Create new branch
            subprocess.run(
                ["git", "checkout", "-b", base_branch],
                cwd=repo_path,
                check=True
            )
            subprocess.run(
                ["git", "push", "-u", "origin", base_branch],
                cwd=repo_path,
                check=True
            )
    
    def get_project(self, project_id: str) -> Optional[ProjectConfig]:
        """Get a project configuration by ID"""
        if project_id not in self.app_config.projects:
            return None
        
        project_path = self.app_config.home_directory / self.app_config.projects[project_id].path
        return ProjectConfig.load(project_path)
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects with their information"""
        projects = []
        for project_id, project_info in self.app_config.projects.items():
            project_path = self.app_config.home_directory / project_info.path
            project_config = ProjectConfig.load(project_path)
            
            if project_config:
                projects.append({
                    "id": project_id,
                    "name": project_info.name,
                    "description": project_config.description,
                    "created_at": project_info.created_at,
                    "last_accessed": project_info.last_accessed,
                    "agent_count": len(project_config.active_agents),
                    "status": project_config.project_metadata.status,
                    "is_current": project_id == self.app_config.current_project,
                    "repository_url": project_config.repository.url
                })
        
        return projects
    
    def switch_project(self, project_id: str) -> bool:
        """Switch to a different project"""
        if project_id not in self.app_config.projects:
            return False
        
        self.app_config.set_current_project(project_id)
        return True
    
    def create_agent(self, project_id: str, role: str, name: str) -> Optional[str]:
        """Create an agent for a project"""
        project_config = self.get_project(project_id)
        if not project_config:
            return None
        
        project_path = self.app_config.home_directory / self.app_config.projects[project_id].path
        
        # Generate agent workspace path
        agent_id = f"{role}-{name.lower().replace(' ', '-')}"
        agent_workspace = project_path / "agents" / agent_id
        
        # Clone repository for agent
        try:
            agent_workspace.mkdir(parents=True, exist_ok=True)
            
            # Clone from maestro (faster than remote)
            maestro_path = project_path / "maestro"
            result = subprocess.run(
                ["git", "clone", str(maestro_path), str(agent_workspace)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Fallback to cloning from remote
                result = subprocess.run(
                    ["git", "clone", project_config.repository.url, str(agent_workspace)],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    raise Exception(f"Failed to clone repository: {result.stderr}")
            
            # Configure git for agent
            git_config = project_config.git_config or GitConfig(
                user_name=f"{name} (DevTeam Agent)",
                user_email=f"{agent_id}@devteam.local"
            )
            
            subprocess.run(
                ["git", "config", "user.name", git_config.user_name],
                cwd=agent_workspace,
                check=True
            )
            subprocess.run(
                ["git", "config", "user.email", git_config.user_email],
                cwd=agent_workspace,
                check=True
            )
            
            # Checkout base branch
            subprocess.run(
                ["git", "checkout", project_config.repository.base_branch],
                cwd=agent_workspace,
                check=True
            )
            
            # Create CLAUDE.md for agent
            self._create_agent_claude_md(project_path, agent_workspace, role, name)
            
            # Add agent to project config
            final_agent_id = project_config.add_agent(role, name, f"agents/{agent_id}")
            
            return final_agent_id
            
        except Exception as e:
            logger.error(f"Failed to create agent workspace: {e}")
            shutil.rmtree(agent_workspace, ignore_errors=True)
            return None
    
    def _create_agent_claude_md(self, project_path: Path, agent_workspace: Path, role: str, name: str) -> None:
        """Create CLAUDE.md file for an agent"""
        # Look for template
        template_content = None
        
        # Check project templates first
        project_template = project_path / "templates" / f"{role}.md"
        if project_template.exists():
            template_content = project_template.read_text()
        else:
            # Check system templates
            system_template = self.app_config.system_templates_directory / f"{role}.md"
            if system_template.exists():
                template_content = system_template.read_text()
        
        # Create CLAUDE.md
        claude_md_path = agent_workspace / "CLAUDE.md"
        
        if template_content:
            # Customize template with agent name
            content = template_content.replace("{{AGENT_NAME}}", name)
            content = content.replace("{{ROLE}}", role)
        else:
            # Default content
            content = f"""# CLAUDE.md

You are {name}, a DevTeam agent specializing in {role} development.

## Your Role

You are responsible for {role} development tasks in this project. Work collaboratively with other agents and follow the project's coding standards.

## Key Responsibilities

- Implement {role} features and fixes
- Review and optimize {role} code
- Collaborate with other agents through clear commits and documentation
- Follow project conventions and patterns

## Important Guidelines

- Always create feature branches from the base branch
- Write clear, descriptive commit messages
- Test your changes thoroughly
- Document any significant changes or decisions
"""
        
        claude_md_path.write_text(content)
    
    def remove_agent(self, project_id: str, agent_id: str) -> bool:
        """Remove an agent from a project"""
        project_config = self.get_project(project_id)
        if not project_config or agent_id not in project_config.active_agents:
            return False
        
        agent_info = project_config.active_agents[agent_id]
        project_path = self.app_config.home_directory / self.app_config.projects[project_id].path
        agent_workspace = project_path / agent_info.workspace
        
        # Remove workspace
        if agent_workspace.exists():
            shutil.rmtree(agent_workspace, ignore_errors=True)
        
        # Remove from config
        project_config.remove_agent(agent_id)
        
        return True
    
    def archive_project(self, project_id: str) -> bool:
        """Archive a project (mark as archived, don't delete)"""
        project_config = self.get_project(project_id)
        if not project_config:
            return False
        
        project_config.project_metadata.status = "archived"
        project_config.save()
        
        # If it's the current project, clear it
        if self.app_config.current_project == project_id:
            self.app_config.current_project = None
            self.app_config.save()
        
        return True