"""Agent process management for multi-project system"""

import subprocess
import psutil
import signal
import os
import json
import socket
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import logging

from .app_config import AppConfig
from .project_config import ProjectConfig


logger = logging.getLogger(__name__)


class AgentManager:
    """Manages agent processes across all projects"""
    
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config
        self.running_processes: Dict[str, Dict[str, subprocess.Popen]] = {}
        # Track PIDs in a file for recovery after restart
        self.pid_file = app_config.home_directory / ".agent_pids.json"
        # Track port allocations
        self.port_file = app_config.home_directory / ".agent_ports.json"
        self.allocated_ports: Dict[str, Dict[str, int]] = {}  # project_id -> {agent_id -> port}
        self._load_pid_file()
        self._load_port_file()
    
    def _load_pid_file(self):
        """Load running agent PIDs from file"""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    pid_data = json.load(f)
                # Verify PIDs are still running
                for project_id, agents in pid_data.items():
                    for agent_id, pid in agents.items():
                        if self._is_process_running(pid):
                            # Process still exists, track it
                            if project_id not in self.running_processes:
                                self.running_processes[project_id] = {}
                            # We can't recover the Popen object, but we can track the PID
                            self.running_processes[project_id][agent_id] = pid
            except Exception as e:
                logger.error(f"Failed to load PID file: {e}")
    
    def _load_port_file(self):
        """Load allocated ports from file"""
        if self.port_file.exists():
            try:
                with open(self.port_file, 'r') as f:
                    self.allocated_ports = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load port file: {e}")
                self.allocated_ports = {}
    
    def _save_pid_file(self):
        """Save running agent PIDs to file"""
        pid_data = {}
        for project_id, agents in self.running_processes.items():
            pid_data[project_id] = {}
            for agent_id, process in agents.items():
                if isinstance(process, int):
                    pid_data[project_id][agent_id] = process
                elif hasattr(process, 'pid'):
                    pid_data[project_id][agent_id] = process.pid
        
        try:
            with open(self.pid_file, 'w') as f:
                json.dump(pid_data, f)
        except Exception as e:
            logger.error(f"Failed to save PID file: {e}")
    
    def _save_port_file(self):
        """Save allocated ports to file"""
        try:
            with open(self.port_file, 'w') as f:
                json.dump(self.allocated_ports, f)
        except Exception as e:
            logger.error(f"Failed to save port file: {e}")
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is still running"""
        try:
            process = psutil.Process(pid)
            # Check if the process is running and is a Python process (our agents)
            if process.is_running():
                # Additional check to ensure it's one of our agent processes
                try:
                    cmdline = process.cmdline()
                    is_agent = any('run_project_agent.py' in arg or 'start_project_bridge.py' in arg 
                                  for arg in cmdline)
                    if not is_agent:
                        logger.debug(f"Process {pid} is running but not an agent: {cmdline}")
                    return is_agent
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    # If we can't access cmdline, assume it's running
                    logger.debug(f"Cannot access cmdline for process {pid}, assuming it's running")
                    return True
            return False
        except psutil.NoSuchProcess:
            return False
    
    def _find_available_port(self, start_port: int = 8301, end_port: int = 8399) -> int:
        """Find an available port in the specified range"""
        
        # Collect all currently allocated ports
        used_ports = set()
        for project_ports in self.allocated_ports.values():
            used_ports.update(project_ports.values())
        
        # Try to find an available port
        for port in range(start_port, end_port + 1):
            if port in used_ports:
                continue
                
            # Check if port is actually available
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                # Port is in use
                continue
        
        raise RuntimeError(f"No available ports in range {start_port}-{end_port}")
    
    def start_project_agents(self, project_id: str) -> Dict[str, str]:
        """Start all agents for a project"""
        results = {}
        
        if project_id not in self.app_config.projects:
            raise ValueError(f"Project {project_id} not found")
        
        # Get the actual project path from app config
        project_info = self.app_config.projects[project_id]
        project_path = self.app_config.home_directory / project_info.path
        project_config = ProjectConfig.load(project_path)
        
        # Stop any existing agents for this project
        self.stop_project_agents(project_id)
        
        # Create project process tracking
        self.running_processes[project_id] = {}
        
        # Start each active agent
        for agent_id, agent_info in project_config.active_agents.items():
            try:
                # Prepare environment
                env = os.environ.copy()
                env['DEVTEAM_PROJECT_ID'] = project_id
                env['DEVTEAM_AGENT_ID'] = agent_id
                env['DEVTEAM_AGENT_ROLE'] = agent_info.role
                env['DEVTEAM_AGENT_NAME'] = agent_info.name
                env['DEVTEAM_HOME'] = str(self.app_config.home_directory)
                
                # Pass API key if available
                if self.app_config.tokens.anthropic_api_key:
                    env['ANTHROPIC_API_KEY'] = self.app_config.tokens.anthropic_api_key
                
                # Allocate port dynamically
                if project_id not in self.allocated_ports:
                    self.allocated_ports[project_id] = {}
                
                # Try to reuse previously allocated port or get a new one
                if agent_id in self.allocated_ports[project_id]:
                    port = self.allocated_ports[project_id][agent_id]
                    # Verify it's still available
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.bind(('', port))
                    except OSError:
                        # Port is taken, allocate a new one
                        port = self._find_available_port()
                        self.allocated_ports[project_id][agent_id] = port
                else:
                    port = self._find_available_port()
                    self.allocated_ports[project_id][agent_id] = port
                
                env['AGENT_PORT'] = str(port)
                
                # Start agent process
                log_file = self.app_config.home_directory / "logs" / f"{project_id}_{agent_id}.log"
                log_file.parent.mkdir(exist_ok=True)
                
                with open(log_file, 'w') as log:
                    # Get the devteam directory (where this script is located)
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
                
                self.running_processes[project_id][agent_id] = process
                results[agent_id] = "started"
                logger.info(f"Started agent {agent_id} for project {project_id} on port {port}")
                
            except Exception as e:
                logger.error(f"Failed to start agent {agent_id}: {e}")
                results[agent_id] = f"failed: {str(e)}"
        
        # Start Telegram bridge if configured and enabled
        if project_config.telegram_config.bot_token and project_config.telegram_config.enabled:
            try:
                self._start_telegram_bridge(project_id, project_config)
                results["telegram_bridge"] = "started"
            except Exception as e:
                logger.error(f"Failed to start Telegram bridge: {e}")
                results["telegram_bridge"] = f"failed: {str(e)}"
        
        self._save_pid_file()
        self._save_port_file()
        return results
    
    def stop_project_agents(self, project_id: str) -> Dict[str, str]:
        """Stop all agents for a project"""
        results = {}
        
        if project_id not in self.running_processes:
            return {"status": "no agents running"}
        
        for agent_id, process in self.running_processes[project_id].items():
            try:
                if isinstance(process, int):
                    # Just have PID, use psutil
                    try:
                        p = psutil.Process(process)
                        p.terminate()
                        p.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        p.kill()
                    except psutil.NoSuchProcess:
                        pass
                elif hasattr(process, 'terminate'):
                    # It's a Popen-like object
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                
                results[agent_id] = "stopped"
                logger.info(f"Stopped agent {agent_id} for project {project_id}")
                
            except Exception as e:
                logger.error(f"Failed to stop agent {agent_id}: {e}")
                results[agent_id] = f"failed: {str(e)}"
        
        # Clean up tracking
        del self.running_processes[project_id]
        if project_id in self.allocated_ports:
            del self.allocated_ports[project_id]
        self._save_pid_file()
        self._save_port_file()
        
        return results
    
    def get_project_status(self, project_id: str) -> Dict[str, Dict[str, any]]:
        """Get status of all agents in a project"""
        status = {}
        
        if project_id not in self.running_processes:
            return {"status": "no agents running"}
        
        for agent_id, process in self.running_processes[project_id].items():
            try:
                if isinstance(process, int):
                    is_running = self._is_process_running(process)
                    pid = process
                    logger.debug(f"Agent {agent_id}: PID {pid}, running: {is_running}")
                elif hasattr(process, 'poll'):
                    is_running = process.poll() is None
                    pid = process.pid
                    logger.debug(f"Agent {agent_id}: Popen PID {pid}, running: {is_running}")
                else:
                    # Unknown process type
                    is_running = False
                    pid = None
                    logger.warning(f"Agent {agent_id}: Unknown process type {type(process)}")
                
                # Initialize status with basic info
                agent_status = {
                    "running": is_running,
                    "pid": pid
                }
                
                # If agent is running, try to fetch additional info from its API
                if is_running:
                    try:
                        # Get allocated port for this agent
                        port = None
                        if project_id in self.allocated_ports and agent_id in self.allocated_ports[project_id]:
                            port = self.allocated_ports[project_id][agent_id]
                        if port:
                            # Try to fetch status from agent
                            import httpx
                            with httpx.Client(timeout=2.0) as client:
                                agent_url = f"http://localhost:{port}/status"
                                logger.info(f"Fetching status from agent {agent_id} at {agent_url}")
                                response = client.get(agent_url)
                                if response.status_code == 200:
                                    agent_data = response.json()
                                    logger.info(f"Agent {agent_id} status data: {agent_data}")
                                    # Add branch info if available
                                    if "branch" in agent_data:
                                        agent_status["branch"] = agent_data["branch"]
                                    if "has_changes" in agent_data:
                                        agent_status["has_changes"] = agent_data["has_changes"]
                                else:
                                    logger.warning(f"Agent {agent_id} returned status {response.status_code}")
                        else:
                            logger.debug(f"No port mapping for agent {agent_id}")
                    except Exception as e:
                        logger.debug(f"Could not fetch additional info from agent {agent_id}: {e}")
                
                status[agent_id] = agent_status
            except Exception as e:
                logger.error(f"Error checking status for agent {agent_id}: {e}")
                status[agent_id] = {
                    "running": False,
                    "error": str(e)
                }
        
        return status
    
    def get_all_projects_status(self) -> Dict[str, Dict[str, any]]:
        """Get status of all projects and their agents"""
        all_status = {}
        
        for project_id in self.app_config.projects:
            project_status = self.get_project_status(project_id)
            all_status[project_id] = {
                "agents": project_status,
                "total_agents": len(project_status),
                "running_agents": sum(1 for a in project_status.values() 
                                    if isinstance(a, dict) and a.get("running", False))
            }
        
        return all_status
    
    def stop_all_agents(self):
        """Stop all agents across all projects"""
        for project_id in list(self.running_processes.keys()):
            self.stop_project_agents(project_id)
    
    
    def _start_telegram_bridge(self, project_id: str, project_config: ProjectConfig):
        """Start Telegram bridge for a project"""
        env = os.environ.copy()
        env['DEVTEAM_PROJECT_ID'] = project_id
        env['DEVTEAM_HOME'] = str(self.app_config.home_directory)
        env['TELEGRAM_BOT_TOKEN'] = project_config.telegram_config.bot_token
        
        if project_config.telegram_config.group_id:
            env['TELEGRAM_GROUP_ID'] = project_config.telegram_config.group_id
        
        log_file = self.app_config.home_directory / "logs" / f"{project_id}_telegram.log"
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'w') as log:
            # Get the devteam directory
            devteam_dir = Path(__file__).parent.parent
            # Use the poetry environment Python
            python_path = devteam_dir / '.venv' / 'bin' / 'python'
            if not python_path.exists():
                python_path = 'python'
            process = subprocess.Popen(
                [str(python_path), 'telegram_bridge/start_project_bridge.py'],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=str(devteam_dir)
            )
        
        # Track as special "telegram" agent
        self.running_processes[project_id]["telegram_bridge"] = process
        logger.info(f"Started Telegram bridge for project {project_id}")