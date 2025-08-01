#!/usr/bin/env python3
"""Tools for agents to interact with the file system and execute commands"""

import os
import subprocess
import json
from typing import Dict, Any, List, Optional
from pathlib import Path


class AgentTools:
    """File system and command execution tools for agents"""
    
    def __init__(self, workspace_path: str, allowed_paths: List[str] = None):
        self.workspace_path = Path(workspace_path)
        self.allowed_paths = allowed_paths or []
        
    def _validate_path(self, path: str) -> Path:
        """Validate that path is within allowed workspace"""
        full_path = Path(path)
        if not full_path.is_absolute():
            full_path = self.workspace_path / path
            
        # Ensure path is within workspace
        try:
            full_path.relative_to(self.workspace_path)
        except ValueError:
            raise ValueError(f"Path {full_path} is outside workspace {self.workspace_path}")
            
        return full_path
    
    def read_file(self, file_path: str) -> str:
        """Read a file from the workspace"""
        path = self._validate_path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path.read_text()
    
    def write_file(self, file_path: str, content: str) -> str:
        """Write content to a file in the workspace"""
        path = self._validate_path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return f"File written: {path}"
    
    def list_files(self, directory: str = ".") -> List[str]:
        """List files in a directory"""
        path = self._validate_path(directory)
        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")
        
        files = []
        for item in path.iterdir():
            if item.is_file():
                files.append(str(item.relative_to(self.workspace_path)))
            elif item.is_dir() and not item.name.startswith('.'):
                files.append(str(item.relative_to(self.workspace_path)) + "/")
        
        return sorted(files)
    
    def execute_command(self, command: str, cwd: str = None) -> Dict[str, Any]:
        """Execute a shell command in the workspace"""
        # Only allow safe commands
        allowed_commands = ['git', 'ls', 'cat', 'grep', 'find', 'npm', 'yarn', 'python', 'node']
        cmd_parts = command.split()
        if not cmd_parts or cmd_parts[0] not in allowed_commands:
            raise ValueError(f"Command not allowed: {cmd_parts[0] if cmd_parts else 'empty'}")
        
        working_dir = self.workspace_path
        if cwd:
            working_dir = self._validate_path(cwd)
            
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out after 30 seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def search_files(self, pattern: str, file_pattern: str = "*") -> List[Dict[str, Any]]:
        """Search for a pattern in files"""
        try:
            result = subprocess.run(
                f"grep -r '{pattern}' --include='{file_pattern}' .",
                shell=True,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            matches = []
            for line in result.stdout.splitlines():
                if ':' in line:
                    file_path, content = line.split(':', 1)
                    matches.append({
                        "file": file_path.lstrip('./'),
                        "line": content.strip()
                    })
                    
            return matches[:20]  # Limit results
            
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about a file"""
        path = self._validate_path(file_path)
        if not path.exists():
            return {"exists": False}
            
        stat = path.stat()
        return {
            "exists": True,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "relative_path": str(path.relative_to(self.workspace_path))
        }