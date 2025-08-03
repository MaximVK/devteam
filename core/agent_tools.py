#!/usr/bin/env python3
"""Tools for agents to interact with the file system and execute commands"""

import os
import subprocess
import json
from typing import Dict, Any, List, Optional
from pathlib import Path


class AgentTools:
    """File system and command execution tools for agents"""
    
    def __init__(self, workspace_path: str, allowed_paths: List[str] = None, allowed_commands: List[str] = None):
        self.workspace_path = Path(workspace_path)
        self.allowed_paths = allowed_paths or []
        self.allowed_commands = allowed_commands or []
        
    def _validate_path(self, path: str) -> Path:
        """Validate that path is within allowed workspace"""
        # Convert to Path object
        input_path = Path(path)
        
        # If path is absolute, use it directly
        if input_path.is_absolute():
            resolved_path = input_path.resolve()
        else:
            # If relative path, first try to resolve from workspace
            full_path = self.workspace_path / path
            try:
                resolved_path = full_path.resolve()
            except Exception:
                # If that fails, try as absolute path
                try:
                    resolved_path = Path(path).resolve()
                except Exception as e:
                    raise ValueError(f"Invalid path: {path} - {str(e)}")
            
        # Resolve workspace for comparison
        try:
            resolved_workspace = self.workspace_path.resolve()
        except Exception as e:
            raise ValueError(f"Invalid workspace path: {self.workspace_path} - {str(e)}")
            
        # Check if the resolved path is within the workspace
        try:
            resolved_path.relative_to(resolved_workspace)
            return resolved_path
        except ValueError:
            # Not in workspace, check allowed paths
            pass
            
        # Check if path is in allowed paths
        for allowed_path in self.allowed_paths:
            try:
                allowed_resolved = Path(allowed_path).resolve()
                # Check if resolved_path is within this allowed path
                resolved_path.relative_to(allowed_resolved)
                return resolved_path
            except ValueError:
                continue
            except Exception:
                # Skip invalid allowed paths
                continue
        
        # Special case: if the path itself is in allowed_paths
        if str(resolved_path) in self.allowed_paths:
            return resolved_path
            
        raise ValueError(f"Path {path} is outside workspace and not in allowed paths. Agent can access: {self.workspace_path} and {self.allowed_paths}")
    
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
        # Use instance allowed commands or default safe commands
        if self.allowed_commands:
            allowed_commands = self.allowed_commands
        else:
            allowed_commands = [
                'git', 'ls', 'cat', 'grep', 'find', 'npm', 'yarn', 'python', 'node', 
                'mkdir', 'touch', 'rm', 'cp', 'mv',
                # Test-related commands
                'pytest', 'python -m pytest', 'poetry', 'pip',
                'jest', 'mocha', 'vitest',  # JS test runners
                'go', 'cargo',  # For Go and Rust tests
                'make', 'bash', 'sh',  # For running test scripts
                'coverage', 'nyc',  # Coverage tools
                'tox', 'nox',  # Python test automation
                'phpunit', 'rspec',  # PHP and Ruby tests
                'dotnet', 'mvn', 'gradle'  # .NET, Java build tools
            ]
        cmd_parts = command.split()
        if not cmd_parts:
            raise ValueError("Empty command")
            
        # Check if the command starts with any allowed command
        cmd_start = cmd_parts[0]
        
        # Also check for multi-word commands like "python -m pytest"
        if len(cmd_parts) >= 3 and cmd_parts[0] == "python" and cmd_parts[1] == "-m":
            cmd_start = "python -m " + cmd_parts[2]
        
        # Check if command is allowed
        is_allowed = False
        for allowed in allowed_commands:
            if cmd_start == allowed or (allowed in ['python', 'node', 'poetry', 'pip', 'npm', 'yarn'] and cmd_start == allowed):
                is_allowed = True
                break
                
        if not is_allowed:
            raise ValueError(f"Command not allowed: {cmd_start}")
        
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