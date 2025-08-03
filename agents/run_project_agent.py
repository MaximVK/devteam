#!/usr/bin/env python3
"""Run an agent with project context"""

import os
import sys
import asyncio
from pathlib import Path
import json
import logging
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from core.app_config import AppConfig
from core.project_config import ProjectConfig
from core.agent_tools import AgentTools
from core.git_helper import GitHelper


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up command logger - logs only commands executed by the agent
command_logger = logging.getLogger('agent_commands')
command_handler = logging.FileHandler(
    Path.home() / 'devteam-home' / 'logs' / 'agent_commands.log'
)
command_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
command_logger.addHandler(command_handler)
command_logger.setLevel(logging.INFO)


class ProjectAgent(BaseAgent):
    """Agent that operates within a project context"""
    
    def __init__(self, project_id: str, agent_id: str, role: str, name: str, 
                 app_config: AppConfig, project_config: ProjectConfig):
        self.project_id = project_id
        self.agent_id = agent_id
        self.role = role
        self.name = name
        self.app_config = app_config
        self.project_config = project_config
        
        # Get workspace path
        workspace_path = project_config.get_agent_workspace(agent_id)
        
        # Get port from environment or default
        port = int(os.environ.get('AGENT_PORT', '8301'))
        
        # Get the actual project source location (where git repo is)
        project_src = project_config.config_path.parent / "agents" / agent_id
        
        # Load agent configuration
        agent_config = project_config.get_agent_configuration(agent_id)
        
        # Initialize tools with the project source directory and allowed paths/commands
        self.tools = AgentTools(
            str(project_src),
            allowed_paths=agent_config.permissions.allowed_paths,
            allowed_commands=agent_config.permissions.allowed_commands
        )
        
        # Initialize git helper with project config
        git_config = {
            "default_branch": project_config.repository.base_branch,
            "remote_url": project_config.repository.url
        }
        self.git_helper = GitHelper(str(project_src), git_config)
        
        super().__init__(
            agent_name=f"{role}-{name}",
            port=port,
            workspace_path=workspace_path
        )
        
        # Add enhanced status endpoint after initialization
        # Remove the existing status route
        routes_to_remove = []
        for i, route in enumerate(self.app.routes):
            if hasattr(route, 'path') and route.path == "/status" and hasattr(route, 'methods') and "GET" in route.methods:
                routes_to_remove.append(i)
        
        # Remove in reverse order to maintain indices
        for i in reversed(routes_to_remove):
            self.app.routes.pop(i)
        
        # Add our enhanced status endpoint
        @self.app.get("/status")
        async def status():
            branch_info = self.git_helper.get_branch_status()
            return {
                "agent": self.agent_name,
                "status": "healthy",
                "port": self.port,
                "branch": branch_info.get("current_branch", "unknown"),
                "has_changes": branch_info.get("has_uncommitted_changes", False)
            }
    
    def get_system_prompt(self) -> str:
        """Get system prompt with project context"""
        # Load CLAUDE.md from agent workspace
        claude_md_path = self.workspace_path / "CLAUDE.md"
        if claude_md_path.exists():
            return claude_md_path.read_text()
        
        # Get the actual project source code location
        project_src = self.project_config.config_path.parent / "agents" / self.agent_id
        
        # Default prompt
        prompt = f"""You are {self.name}, a {self.role} agent working on {self.project_config.project_name}.

Project: {self.project_config.project_name}
Repository: {self.project_config.repository.url}
Repository base branch: {self.project_config.repository.base_branch}
Working directory (with git repo): {project_src}
Personal workspace (for notes/drafts): {self.workspace_path}

You are currently working in: {project_src}

You have access to the following tools:

1. File Operations:
   - Read files: {{"tool": "read_file", "path": "path/to/file"}}
   - Write files: {{"tool": "write_file", "path": "path/to/file", "content": "content"}}
   - List files: {{"tool": "list_files", "directory": "path/to/dir"}}
   - Get file info: {{"tool": "get_file_info", "path": "path/to/file"}}

2. Command Execution:
   - Execute commands: {{"tool": "execute_command", "command": "git status"}}
   - Allowed commands: git, ls, cat, grep, find, npm, yarn, python, node

3. Search:
   - Search in files: {{"tool": "search_files", "pattern": "search pattern", "file_pattern": "*.py"}}

4. Git Operations:
   - Create branch: {{"tool": "create_branch", "task_id": "task-id", "task_title": "Feature title"}}
   - Commit changes: {{"tool": "commit_changes", "title": "Commit title", "description": "Description"}}
   - Push branch: {{"tool": "push_branch", "branch_name": "branch-name"}}
   - Get branch status: {{"tool": "get_branch_status"}}

To use a tool, include the tool request in your response on its own line as a JSON object. For example:
{{"tool": "list_files", "directory": "."}}

Or for commands:
{{"tool": "execute_command", "command": "git status"}}

IMPORTANT: Put each tool request on its own line with no other text on that line.

You are part of a multi-agent development team. Work collaboratively and communicate through the task system.
"""
        return prompt
    
    async def process_message(self, message: str, from_user: Optional[str] = None, 
                            context: Optional[Dict[str, Any]] = None) -> str:
        """Process message and handle tool requests"""
        # First get the base response
        response = await super().process_message(message, from_user, context)
        
        logger.info(f"Raw response from Claude (length: {len(response)}):\n{response}")
        
        # Check if response contains tool requests
        tool_executed = False
        final_response_lines = []
        
        # For multi-line JSON, we need a more sophisticated approach
        import re
        
        # Find all potential JSON tool requests
        potential_jsons = []
        
        # Pattern to find JSON tool requests - now handles multi-line
        current_pos = 0
        while True:
            start = response.find('{"tool":', current_pos)
            if start == -1:
                break
                
            # Find the matching closing brace
            brace_count = 0
            in_string = False
            escape_next = False
            end = start
            
            for i in range(start, len(response)):
                char = response[i]
                
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            potential_jsons.append((start, end, response[start:end]))
                            break
            
            current_pos = end if end > start else start + 1
        
        # Process the response, executing tools as we find them
        last_end = 0
        for json_start, json_end, json_str in potential_jsons:
            # Add any text before this JSON
            if json_start > last_end:
                prefix = response[last_end:json_start].strip()
                if prefix:
                    final_response_lines.append(prefix)
            
            try:
                # Try to fix common JSON issues before parsing
                # Handle unescaped newlines in content by looking for common patterns
                if '"content":' in json_str:
                    # Extract the content part more carefully
                    import re
                    # Match content field with proper handling of nested quotes
                    content_match = re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', json_str, re.DOTALL)
                    if content_match:
                        original_content = content_match.group(1)
                        # Check if content has unescaped newlines
                        if '\n' in original_content and '\\n' not in original_content:
                            # Replace actual newlines with escaped ones
                            fixed_content = original_content.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                            json_str = json_str.replace(original_content, fixed_content)
                
                tool_request = json.loads(json_str)
                if "tool" in tool_request:
                    logger.info(f"Executing tool: {tool_request['tool']}")
                    result = await self.execute_tool(
                        tool_request["tool"], 
                        tool_request
                    )
                    logger.info(f"Tool result: {result}")
                    tool_executed = True
                    
                    # Format tool result
                    if tool_request["tool"] == "execute_command":
                        if result.get("success"):
                            if result.get("stdout"):
                                final_response_lines.append(f"\n```\n{result['stdout'].strip()}\n```")
                            else:
                                final_response_lines.append("\n✓ Command executed successfully")
                        else:
                            error_msg = result.get("stderr", result.get("error", "Unknown error"))
                            final_response_lines.append(f"\n⚠️ Command failed: {error_msg}")
                    elif tool_request["tool"] == "list_files":
                        if isinstance(result, list):
                            final_response_lines.append("\nFiles found:")
                            for f in result[:20]:  # Limit output
                                final_response_lines.append(f"  - {f}")
                            if len(result) > 20:
                                final_response_lines.append(f"  ... and {len(result) - 20} more files")
                        else:
                            final_response_lines.append(f"\n{result}")
                    elif tool_request["tool"] == "write_file":
                        if isinstance(result, str) and "written" in result:
                            final_response_lines.append(f"\n✓ {result}")
                        else:
                            final_response_lines.append(f"\n⚠️ Write failed: {result}")
                    elif tool_request["tool"] == "create_branch":
                        # Store the actual branch name for later use
                        if isinstance(result, str):
                            self._current_branch = result
                            final_response_lines.append(f"\n🌿 Created new branch: {result}")
                            final_response_lines.append(f"📍 Switched to branch: {result}")
                        else:
                            final_response_lines.append(f"\n⚠️ Branch creation failed: {result}")
                    elif tool_request["tool"] == "commit_changes":
                        if result is True:
                            final_response_lines.append(f"\n✓ Changes committed successfully")
                        else:
                            final_response_lines.append(f"\n⚠️ No changes to commit")
                    elif tool_request["tool"] == "push_branch":
                        if result is True:
                            branch = tool_request.get("branch_name", self._current_branch if hasattr(self, '_current_branch') else "current branch")
                            final_response_lines.append(f"\n✓ Pushed branch '{branch}' to remote")
                        else:
                            final_response_lines.append(f"\n⚠️ Failed to push branch")
                    elif tool_request["tool"] == "get_branch_status":
                        if isinstance(result, dict) and "current_branch" in result:
                            final_response_lines.append(f"\n🌿 Current branch: {result['current_branch']}")
                            if result.get("has_uncommitted_changes"):
                                final_response_lines.append("🔴 Has uncommitted changes")
                            else:
                                final_response_lines.append("🟢 Working tree clean")
                        else:
                            final_response_lines.append(f"\n{result}")
                    else:
                        # For other tools, format appropriately
                        if isinstance(result, dict) and "error" in result:
                            final_response_lines.append(f"\n⚠️ {result['error']}")
                        else:
                            final_response_lines.append(f"\n{result}")
                    
                    last_end = json_end
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Failed JSON string: {json_str}")
                # Try to extract just the tool name for a partial execution message
                import re
                tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', json_str)
                if tool_match:
                    tool_name = tool_match.group(1)
                    final_response_lines.append(f"\n⚠️ Failed to parse {tool_name} tool request (JSON error)")
                else:
                    final_response_lines.append(f"\n⚠️ Failed to parse tool request (JSON error)")
                last_end = json_end
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                final_response_lines.append(f"\n⚠️ Tool error: {str(e)}")
                last_end = json_end
        
        # Add any remaining text after the last JSON
        if last_end < len(response):
            remaining = response[last_end:].strip()
            if remaining:
                final_response_lines.append(remaining)
        
        # If no tools were found, return the original response
        if not tool_executed:
            return response
            
        return '\n'.join(final_response_lines)
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool with given parameters"""
        try:
            if tool_name == "read_file":
                return self.tools.read_file(params["path"])
            elif tool_name == "write_file":
                command_logger.info(f"[{self.name}] write_file {params['path']}")
                return self.tools.write_file(params["path"], params["content"])
            elif tool_name == "list_files":
                return self.tools.list_files(params.get("directory", "."))
            elif tool_name == "execute_command":
                command_logger.info(f"[{self.name}] $ {params['command']}")
                return self.tools.execute_command(params["command"], params.get("cwd"))
            elif tool_name == "search_files":
                return self.tools.search_files(params["pattern"], params.get("file_pattern", "*"))
            elif tool_name == "get_file_info":
                return self.tools.get_file_info(params["path"])
            elif tool_name == "create_branch":
                branch_name = self.git_helper.create_feature_branch(
                    self.role,
                    params.get("task_id", "task"),
                    params.get("task_title")
                )
                command_logger.info(f"[{self.name}] git checkout -b {branch_name}")
                return branch_name
            elif tool_name == "commit_changes":
                command_logger.info(f"[{self.name}] git add .")
                command_logger.info(f"[{self.name}] git commit -m '{params['title']}'")
                return self.git_helper.commit_changes(
                    params["title"],
                    params["description"],
                    self.role,
                    params.get("task_id", "task")
                )
            elif tool_name == "push_branch":
                branch = params.get("branch_name", "current")
                command_logger.info(f"[{self.name}] git push -u origin {branch}")
                return self.git_helper.push_branch(params.get("branch_name"))
            elif tool_name == "get_branch_status":
                command_logger.info(f"[{self.name}] git status")
                return self.git_helper.get_branch_status()
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        except Exception as e:
            return {"error": str(e)}


async def main():
    """Main entry point"""
    # Get configuration from environment
    project_id = os.environ.get('DEVTEAM_PROJECT_ID')
    agent_id = os.environ.get('DEVTEAM_AGENT_ID')
    role = os.environ.get('DEVTEAM_AGENT_ROLE')
    name = os.environ.get('DEVTEAM_AGENT_NAME')
    home_dir = Path(os.environ.get('DEVTEAM_HOME', Path.home() / 'devteam-home'))
    
    if not all([project_id, agent_id, role, name]):
        logger.error("Missing required environment variables")
        sys.exit(1)
    
    try:
        # Load configurations
        app_config = AppConfig.load(home_dir)
        if not app_config:
            logger.error(f"Failed to load app config from {home_dir}")
            sys.exit(1)
            
        # Get the actual project path from app config
        if project_id not in app_config.projects:
            logger.error(f"Project {project_id} not found in app config")
            sys.exit(1)
            
        project_info = app_config.projects[project_id]
        project_path = app_config.home_directory / project_info.path
        project_config = ProjectConfig.load(project_path)
        
        if not project_config:
            logger.error(f"Failed to load project config from {project_path}")
            sys.exit(1)
        
        # Create and run agent
        agent = ProjectAgent(
            project_id=project_id,
            agent_id=agent_id,
            role=role,
            name=name,
            app_config=app_config,
            project_config=project_config
        )
        
        logger.info(f"Starting {role} agent '{name}' for project {project_id}")
        await agent.run()
        
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())