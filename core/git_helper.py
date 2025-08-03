#!/usr/bin/env python3
"""Git operations helper for workspace-aware agents"""

import os
import subprocess
import json
from typing import Dict, Any, Optional
from pathlib import Path


class GitHelper:
    """Helper class for git operations in agent workspace"""
    
    def __init__(self, workspace_path: str, git_config: Dict[str, Any]):
        self.workspace_path = Path(workspace_path)
        self.git_config = git_config
        self.setup_git_config()
    
    def setup_git_config(self):
        """Configure git user settings for the workspace"""
        commands = [
            ["git", "config", "user.name", self.git_config.get("user_name", "DevTeam Agent")],
            ["git", "config", "user.email", self.git_config.get("user_email", "agent@devteam.local")]
        ]
        
        for cmd in commands:
            try:
                subprocess.run(cmd, cwd=self.workspace_path, check=True, capture_output=True)
            except subprocess.CalledProcessError:
                pass  # Ignore config errors
    
    def create_feature_branch(self, agent_role: str, task_id: str, task_title: str = None) -> str:
        """Create a new feature branch for the agent task"""
        # Generate branch name using pattern
        branch_prefix = self.git_config.get("branch_prefix", "agent/")
        if task_title:
            # Use task title if provided, sanitized
            safe_title = "".join(c for c in task_title.lower().replace(" ", "-") if c.isalnum() or c in "-_")[:30]
            branch_name = f"{branch_prefix}{agent_role}/{safe_title}"
        else:
            branch_name = f"{branch_prefix}{agent_role}/{task_id}"
        
        try:
            # Ensure we're on main/default branch first
            default_branch = self.git_config.get("default_branch", "main")
            subprocess.run(["git", "checkout", default_branch], 
                         cwd=self.workspace_path, check=True, capture_output=True)
            
            # Pull latest changes
            subprocess.run(["git", "pull", "origin", default_branch], 
                         cwd=self.workspace_path, check=True, capture_output=True)
            
            # Create and checkout new branch
            subprocess.run(["git", "checkout", "-b", branch_name], 
                         cwd=self.workspace_path, check=True, capture_output=True)
            
            # Push the new branch to remote with upstream tracking
            subprocess.run(["git", "push", "-u", "origin", branch_name], 
                         cwd=self.workspace_path, check=True, capture_output=True)
            
            return branch_name
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to create branch {branch_name}: {e}")
    
    def commit_changes(self, task_title: str, description: str, agent_role: str, task_id: str) -> bool:
        """Commit changes with structured message"""
        try:
            # Add all changes
            subprocess.run(["git", "add", "."], 
                         cwd=self.workspace_path, check=True, capture_output=True)
            
            # Check if there are changes to commit
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  cwd=self.workspace_path, capture_output=True, text=True)
            if not result.stdout.strip():
                return False  # No changes to commit
            
            # Create commit message
            commit_msg = f"{task_title}\n\n{description}\n\nAgent: {agent_role}\nTask ID: {task_id}"
            
            # Commit changes
            subprocess.run(["git", "commit", "-m", commit_msg], 
                         cwd=self.workspace_path, check=True, capture_output=True)
            
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to commit changes: {e}")
    
    def push_branch(self, branch_name: str = None) -> bool:
        """Push the current branch to origin"""
        try:
            # If no branch name provided, use current branch
            if not branch_name:
                branch_name = self.get_current_branch()
                
            # First try to push the specified branch
            result = subprocess.run(["git", "push", "-u", "origin", branch_name], 
                                  cwd=self.workspace_path, capture_output=True, text=True)
            
            if result.returncode != 0:
                # If that fails, try pushing the current branch
                current_branch = self.get_current_branch()
                if current_branch != branch_name:
                    result = subprocess.run(["git", "push", "-u", "origin", current_branch], 
                                          cwd=self.workspace_path, capture_output=True, text=True)
                    if result.returncode == 0:
                        return True
                raise subprocess.CalledProcessError(result.returncode, result.args, 
                                                  output=result.stdout, stderr=result.stderr)
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to push branch {branch_name}: {e}")
    
    def get_current_branch(self) -> str:
        """Get the current branch name"""
        try:
            result = subprocess.run(["git", "branch", "--show-current"], 
                                  cwd=self.workspace_path, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"
    
    def get_branch_status(self) -> Dict[str, Any]:
        """Get detailed status of the current branch"""
        try:
            # Get current branch
            current_branch = self.get_current_branch()
            
            # Get status
            status_result = subprocess.run(["git", "status", "--porcelain"], 
                                         cwd=self.workspace_path, capture_output=True, text=True, check=True)
            
            # Get ahead/behind info
            tracking_result = subprocess.run(["git", "status", "-b", "--porcelain"], 
                                           cwd=self.workspace_path, capture_output=True, text=True, check=True)
            
            has_changes = bool(status_result.stdout.strip())
            
            return {
                "current_branch": current_branch,
                "has_uncommitted_changes": has_changes,
                "status_output": status_result.stdout,
                "tracking_info": tracking_result.stdout.split('\n')[0] if tracking_result.stdout else ""
            }
        except subprocess.CalledProcessError as e:
            return {"error": str(e)}
    
    def create_github_pr(self, branch_name: str, title: str, description: str, 
                        changes: str, test_plan: str, agent_role: str) -> Optional[str]:
        """Create a GitHub pull request using gh CLI"""
        try:
            # Format PR body using template
            pr_body = f"""## Summary

{description}

## Changes

{changes}

## Testing

{test_plan}

---
Created by {agent_role} agent"""
            
            # Create PR using gh CLI
            result = subprocess.run([
                "gh", "pr", "create",
                "--title", title,
                "--body", pr_body,
                "--head", branch_name
            ], cwd=self.workspace_path, capture_output=True, text=True, check=True)
            
            # Extract PR URL from output
            pr_url = result.stdout.strip()
            return pr_url
            
        except subprocess.CalledProcessError as e:
            # PR creation failed, but that's okay - the branch is still pushed
            print(f"Warning: Could not create PR automatically: {e}")
            return None