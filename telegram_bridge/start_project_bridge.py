#!/usr/bin/env python3
"""Project-specific Telegram bridge"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional
import json
import ssl
import certifi

# Set SSL certificate bundle path for macOS
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# Disable SSL warnings for development
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure httpx to disable SSL verification globally for this process
import httpx

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.app_config import AppConfig
from core.project_config import ProjectConfig
from telegram_bridge.bridge import TelegramBridge


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProjectTelegramBridge(TelegramBridge):
    """Telegram bridge for a specific project"""
    
    def __init__(self, project_id: str, project_config: ProjectConfig, app_config: AppConfig):
        self.project_id = project_id
        self.project_config = project_config
        self.app_config = app_config
        
        # Initialize with project-specific token
        super().__init__(
            bot_token=project_config.telegram_config.bot_token,
            channel_id=project_config.telegram_config.group_id
        )
        
        # Set project context in messages
        self.context_prefix = f"[{project_config.project_name}] "
    
    async def send_message(self, text: str, reply_to: Optional[int] = None) -> None:
        """Send message with project context"""
        # Add project context to message
        text_with_context = f"{self.context_prefix}{text}"
        await super().send_message(text_with_context, reply_to)
    
    def get_agent_urls(self) -> Dict[str, str]:
        """Get URLs for agents in this project"""
        urls = {}
        
        # Try to load port mappings from the agent manager's port file
        try:
            home_dir = Path(os.environ.get('DEVTEAM_HOME', Path.home() / 'devteam-home'))
            port_file = home_dir / '.agent_ports.json'
            
            if port_file.exists():
                with open(port_file) as f:
                    port_data = json.load(f)
                    
                # Get ports for this project
                if self.project_id in port_data:
                    project_ports = port_data[self.project_id]
                    
                    for agent_id, agent_info in self.project_config.active_agents.items():
                        if agent_id in project_ports:
                            port = project_ports[agent_id]
                            urls[agent_info.name] = f"http://localhost:{port}/ask"
                            logger.info(f"Found port {port} for agent {agent_info.name}")
                        else:
                            logger.warning(f"No port found for agent {agent_id}")
            else:
                logger.warning(f"Port file not found: {port_file}")
                            
        except Exception as e:
            logger.error(f"Error loading agent ports: {e}")
        
        return urls
    


async def main():
    """Main entry point"""
    # Get configuration from environment
    project_id = os.environ.get('DEVTEAM_PROJECT_ID')
    home_dir = Path(os.environ.get('DEVTEAM_HOME', Path.home() / 'devteam-home'))
    
    if not project_id:
        logger.error("DEVTEAM_PROJECT_ID not set")
        sys.exit(1)
    
    try:
        # Load configurations
        app_config = AppConfig.load(home_dir)
        if not app_config:
            logger.error("App configuration not found")
            sys.exit(1)
        
        # Get the actual project path from app config
        if project_id not in app_config.projects:
            logger.error(f"Project {project_id} not found in app config")
            sys.exit(1)
            
        project_info = app_config.projects[project_id]
        project_path = app_config.home_directory / project_info.path
        project_config = ProjectConfig.load(project_path)
        if not project_config:
            logger.error(f"Project configuration not found at {project_path}")
            sys.exit(1)
        
        # Verify Telegram is configured
        if not project_config.telegram_config.bot_token:
            logger.error("Telegram bot token not configured for project")
            sys.exit(1)
        
        # Create and run bridge
        bridge = ProjectTelegramBridge(project_id, project_config, app_config)
        
        logger.info(f"Starting Telegram bridge for project: {project_config.project_name}")
        await bridge.start()
        
    except KeyboardInterrupt:
        logger.info("Telegram bridge stopped by user")
    except Exception as e:
        logger.error(f"Telegram bridge failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())