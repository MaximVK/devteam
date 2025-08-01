import asyncio
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from unittest.mock import patch

from pydantic import BaseModel, Field
import httpx
import yaml

from core.claude_agent import AgentRole, AgentSettings
from core.telegram_bridge import TelegramBridge, TelegramSettings
from core.github_sync import GitHubSync, GitHubSettings


logger = logging.getLogger(__name__)


class PortConfig(BaseModel):
    start_port: int = 8300
    max_agents: int = 20
    allocated_ports: Dict[str, int] = {}
    
    def allocate_port(self, role: str) -> int:
        if role in self.allocated_ports:
            return self.allocated_ports[role]
            
        used_ports = set(self.allocated_ports.values())
        for port in range(self.start_port, self.start_port + self.max_agents):
            if port not in used_ports:
                self.allocated_ports[role] = port
                return port
                
        raise ValueError("No available ports")
        
    def release_port(self, role: str) -> None:
        if role in self.allocated_ports:
            del self.allocated_ports[role]


class AgentProcess(BaseModel):
    role: AgentRole
    port: int
    pid: Optional[int] = None
    env_file: str
    start_time: datetime = Field(default_factory=datetime.now)
    status: str = "stopped"


class AgentOrchestrator:
    def __init__(self, config_dir: Path = Path("config")):
        self.config_dir = config_dir
        self.config_dir.mkdir(exist_ok=True)
        
        self.port_config = PortConfig()
        self.agents: Dict[str, AgentProcess] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        
        self.telegram_bridge: Optional[TelegramBridge] = None
        self.github_sync: Optional[GitHubSync] = None
        
        self.client = httpx.AsyncClient(timeout=10.0)
        
    async def initialize(self, telegram_settings: Optional[TelegramSettings] = None,
                        github_settings: Optional[GitHubSettings] = None) -> None:
        """Initialize orchestrator with optional integrations"""
        if telegram_settings:
            self.telegram_bridge = TelegramBridge(telegram_settings)
            await self.telegram_bridge.start()
            
        if github_settings:
            self.github_sync = GitHubSync(github_settings)
            
    async def create_agent(self, role: AgentRole, model: str = "claude-3-sonnet-20240229",
                          github_repo: Optional[str] = None,
                          telegram_channel_id: Optional[str] = None) -> AgentProcess:
        """Create and start a new agent"""
        role_str = role.value if isinstance(role, AgentRole) else role
        
        if role_str in self.agents:
            raise ValueError(f"Agent with role {role_str} already exists")
            
        # Allocate port
        port = self.port_config.allocate_port(role_str)
        
        # Create environment files
        env_file = self.config_dir / f".env.{role_str}"
        self._create_env_file(env_file, role_str, port, model, github_repo, telegram_channel_id)
        
        # Create CLAUDE.md file
        claude_file = self.config_dir / f"claude-{role_str}.md"
        self._create_claude_file(claude_file, role_str)
        
        # Create agent process info
        agent = AgentProcess(
            role=role,
            port=port,
            env_file=str(env_file)
        )
        
        # Start the agent
        await self.start_agent(role.value if isinstance(role, AgentRole) else role)
        
        self.agents[role.value if isinstance(role, AgentRole) else role] = agent
        
        # Register with Telegram bridge
        if self.telegram_bridge:
            self.telegram_bridge.register_agent(role_str, port)
            
        return agent
        
    def _create_env_file(self, path: Path, role: str, port: int, model: str,
                        github_repo: Optional[str], telegram_channel_id: Optional[str]) -> None:
        """Create environment file for agent"""
        env_content = f"""ROLE={role}
PORT={port}
MODEL={model}
CLAUDE_FILE=config/claude-{role}.md
ANTHROPIC_API_KEY=${{ANTHROPIC_API_KEY}}
"""
        
        if github_repo:
            env_content += f"GITHUB_REPO={github_repo}\n"
            
        if telegram_channel_id:
            env_content += f"TELEGRAM_CHANNEL_ID={telegram_channel_id}\n"
            
        path.write_text(env_content)
        
    def _create_claude_file(self, path: Path, role: str) -> None:
        """Create CLAUDE.md file for agent role"""
        from core.claude_agent import ClaudeAgent, AgentSettings
        
        # Create a temporary agent to get the default prompt
        temp_settings = AgentSettings(
            role=role,
            port=8000,
            anthropic_api_key="temp"
        )
        
        # Mock the Anthropic client to avoid initialization
        with patch('anthropic.Anthropic'):
            temp_agent = ClaudeAgent(temp_settings)
            prompt = temp_agent._generate_default_prompt()
        
        path.write_text(prompt)
        
    async def start_agent(self, role: str) -> None:
        """Start an agent process"""
        if role not in self.agents:
            raise ValueError(f"Agent {role} not found")
            
        agent = self.agents[role]
        
        if role in self.processes:
            logger.warning(f"Agent {role} is already running")
            return
            
        # Start the agent process
        cmd = [
            "python", "-m", "agents.api",
            "--env-file", agent.env_file
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**subprocess.os.environ, "PYTHONPATH": str(Path.cwd())}
        )
        
        self.processes[role] = process
        agent.pid = process.pid
        agent.status = "running"
        
        # Wait for agent to be ready
        await self._wait_for_agent(agent.port)
        
        logger.info(f"Started agent {role} on port {agent.port} (PID: {process.pid})")
        
    async def _wait_for_agent(self, port: int, timeout: int = 30) -> None:
        """Wait for agent to be ready"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                response = await self.client.get(f"http://localhost:{port}/status")
                if response.status_code == 200:
                    return
            except:
                pass
                
            await asyncio.sleep(0.5)
            
        raise TimeoutError(f"Agent on port {port} did not start within {timeout} seconds")
        
    async def stop_agent(self, role: str) -> None:
        """Stop an agent process"""
        if role not in self.processes:
            logger.warning(f"Agent {role} is not running")
            return
            
        process = self.processes[role]
        process.terminate()
        
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            
        del self.processes[role]
        
        if role in self.agents:
            self.agents[role].status = "stopped"
            self.agents[role].pid = None
            
        logger.info(f"Stopped agent {role}")
        
    async def restart_agent(self, role: str) -> None:
        """Restart an agent"""
        await self.stop_agent(role)
        await asyncio.sleep(1)
        await self.start_agent(role)
        
    async def get_agent_status(self, role: str) -> Dict[str, Any]:
        """Get status of a specific agent"""
        if role not in self.agents:
            return {"error": "Agent not found"}
            
        agent = self.agents[role]
        
        try:
            response = await self.client.get(f"http://localhost:{agent.port}/status")
            if response.status_code == 200:
                status = response.json()
                status["process"] = {
                    "pid": agent.pid,
                    "status": agent.status,
                    "uptime": (datetime.now() - agent.start_time).total_seconds()
                }
                return status
        except:
            pass
            
        return {
            "role": role,
            "status": "offline",
            "process": {
                "pid": agent.pid,
                "status": agent.status
            }
        }
        
    async def get_all_agents_status(self) -> List[Dict[str, Any]]:
        """Get status of all agents"""
        statuses = []
        
        for role in self.agents:
            status = await self.get_agent_status(role)
            statuses.append(status)
            
        return statuses
        
    async def assign_github_tasks(self) -> None:
        """Fetch and assign GitHub tasks to agents"""
        if not self.github_sync:
            logger.warning("GitHub sync not initialized")
            return
            
        for role in self.agents:
            if self.agents[role].status != "running":
                continue
                
            # Fetch tasks for this role
            tasks = await self.github_sync.get_tasks_for_role(role)
            
            for task in tasks:
                # Check if task is already assigned
                if task.assignee:
                    continue
                    
                # Assign task to agent
                try:
                    response = await self.client.post(
                        f"http://localhost:{self.agents[role].port}/assign",
                        json={
                            "id": f"github-{task.issue_number}",
                            "title": task.title,
                            "description": task.body,
                            "github_issue_number": task.issue_number
                        }
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"Assigned GitHub issue #{task.issue_number} to {role}")
                        
                        # Update issue assignee
                        await self.github_sync.update_issue_status(
                            task.issue_number,
                            "open",
                            f"Task assigned to {role} agent"
                        )
                        
                        # Notify via Telegram
                        if self.telegram_bridge:
                            await self.telegram_bridge.send_message(
                                f"📋 Assigned issue #{task.issue_number} to {role}:\n{task.title}",
                                role
                            )
                            
                except Exception as e:
                    logger.error(f"Failed to assign task to {role}: {e}")
                    
    async def shutdown(self) -> None:
        """Shutdown all agents and cleanup"""
        # Stop all agents
        for role in list(self.processes.keys()):
            await self.stop_agent(role)
            
        # Stop Telegram bridge
        if self.telegram_bridge:
            await self.telegram_bridge.stop()
            
        # Close HTTP client
        await self.client.aclose()
        
        logger.info("Orchestrator shutdown complete")