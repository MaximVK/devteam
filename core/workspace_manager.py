"""Workspace manager for multi-agent system"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from .workspace_config import WorkspaceConfig, GitConfig


logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages workspaces for agents and maestro"""
    
    def __init__(self, config: WorkspaceConfig):
        self.config = config
    
    def initialize_maestro(self) -> bool:
        """Initialize the maestro (human) workspace"""
        try:
            maestro_path = self.config.maestro_path
            maestro_path.mkdir(parents=True, exist_ok=True)
            
            if not (maestro_path / ".git").exists():
                logger.info(f"Cloning repository to maestro workspace: {maestro_path}")
                
                # Clone the repository
                subprocess.run(
                    ["git", "clone", self.config.git_config.repository_url, str(maestro_path)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                # Configure git
                self._configure_git(maestro_path, is_maestro=True)
                
                # Check if base branch exists, create if not
                self._ensure_base_branch(maestro_path)
                
                logger.info("Maestro workspace initialized successfully")
            else:
                logger.info("Maestro workspace already initialized")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to initialize maestro workspace: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            return False
    
    def _ensure_base_branch(self, repo_path: Path) -> None:
        """Ensure the base branch for agents exists"""
        base_branch = self.config.git_config.base_branch
        
        # Check if branch exists
        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if f"origin/{base_branch}" not in result.stdout:
            logger.info(f"Creating base branch: {base_branch}")
            
            # Create and push the base branch
            subprocess.run(
                ["git", "checkout", "-b", base_branch],
                cwd=repo_path,
                check=True
            )
            
            # Create initial commit if needed
            readme_path = repo_path / "README_AGENTS.md"
            readme_path.write_text(
                f"# Agent Workspace Branch\n\n"
                f"This is the base branch ({base_branch}) for agent workspaces.\n"
                f"Agents will create feature branches from this branch.\n"
            )
            
            subprocess.run(
                ["git", "add", "README_AGENTS.md"],
                cwd=repo_path,
                check=True
            )
            
            subprocess.run(
                ["git", "commit", "-m", f"Initialize {base_branch} branch for agents"],
                cwd=repo_path,
                check=True
            )
            
            subprocess.run(
                ["git", "push", "-u", "origin", base_branch],
                cwd=repo_path,
                check=True
            )
            
            # Switch back to main
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=repo_path,
                check=True
            )
    
    def initialize_agent_workspace(self, role: str) -> bool:
        """Initialize workspace for a specific agent"""
        try:
            agent_workspace = self.config.get_agent_workspace(role)
            agent_repo_path = self.config.get_agent_repo_path(role)
            
            agent_workspace.mkdir(parents=True, exist_ok=True)
            
            if not agent_repo_path.exists():
                logger.info(f"Creating workspace for {role} agent")
                
                # Clone the repository
                subprocess.run(
                    ["git", "clone", 
                     "-b", self.config.git_config.base_branch,
                     self.config.git_config.repository_url, 
                     str(agent_repo_path)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                # Configure git for agent
                self._configure_git(agent_repo_path, is_maestro=False)
                
                # Create CLAUDE.md for agent
                self._create_agent_claude_md(role, agent_repo_path)
                
                logger.info(f"Agent workspace for {role} initialized successfully")
            else:
                logger.info(f"Agent workspace for {role} already exists")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to initialize agent workspace: {e}")
            return False
    
    def _configure_git(self, repo_path: Path, is_maestro: bool = False) -> None:
        """Configure git for a repository"""
        git_config = self.config.git_config
        
        # Set user name and email
        user_name = "Human Developer" if is_maestro else git_config.user_name
        user_email = "human@devteam.local" if is_maestro else git_config.user_email
        
        subprocess.run(
            ["git", "config", "user.name", user_name],
            cwd=repo_path,
            check=True
        )
        
        subprocess.run(
            ["git", "config", "user.email", user_email],
            cwd=repo_path,
            check=True
        )
    
    def _create_agent_claude_md(self, role: str, agent_repo_path: Path) -> None:
        """Create CLAUDE.md file for agent from templates"""
        from .template_manager import TemplateManager
        
        template_manager = TemplateManager(self.config)
        content = template_manager.generate_claude_md(role)
        
        claude_md_path = agent_repo_path / "CLAUDE.md"
        claude_md_path.write_text(content)
        logger.info(f"Created CLAUDE.md for {role} agent")
    
    def get_available_roles(self) -> List[str]:
        """Get list of available roles from templates"""
        from .template_manager import TemplateManager
        
        template_manager = TemplateManager(self.config)
        return template_manager.get_available_roles()
    
    def cleanup_agent_workspace(self, role: str) -> bool:
        """Remove an agent's workspace"""
        try:
            agent_workspace = self.config.get_agent_workspace(role)
            if agent_workspace.exists():
                shutil.rmtree(agent_workspace)
                logger.info(f"Removed workspace for {role} agent")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup agent workspace: {e}")
            return False