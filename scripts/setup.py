#!/usr/bin/env python3
"""Auto-setup script for DevTeam environment configuration"""

import os
import sys
from pathlib import Path
import json
import subprocess
import argparse
from typing import Dict, Any, Optional


class DevTeamSetup:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_dir = project_root / "config"
        self.config_dir.mkdir(exist_ok=True)
        
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        print("🔍 Checking dependencies...")
        
        # Check Python version
        if sys.version_info < (3, 11):
            print("❌ Python 3.11+ is required")
            return False
            
        # Check if poetry is installed
        try:
            subprocess.run(["poetry", "--version"], capture_output=True, check=True)
            print("✅ Poetry is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Poetry is not installed. Install it from https://python-poetry.org/")
            return False
            
        # Check if Node.js is installed
        try:
            subprocess.run(["node", "--version"], capture_output=True, check=True)
            print("✅ Node.js is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Node.js is not installed. Install it from https://nodejs.org/")
            return False
            
        return True
        
    def install_dependencies(self) -> bool:
        """Install Python and Node.js dependencies"""
        print("\n📦 Installing dependencies...")
        
        # Install Python dependencies
        try:
            print("Installing Python dependencies...")
            subprocess.run(["poetry", "install"], cwd=self.project_root, check=True)
            print("✅ Python dependencies installed")
        except subprocess.CalledProcessError:
            print("❌ Failed to install Python dependencies")
            return False
            
        # Install Node.js dependencies
        frontend_dir = self.project_root / "web" / "frontend"
        if frontend_dir.exists():
            try:
                print("Installing Node.js dependencies...")
                subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
                print("✅ Node.js dependencies installed")
            except subprocess.CalledProcessError:
                print("❌ Failed to install Node.js dependencies")
                return False
                
        return True
        
    def create_env_file(self, role: str, port: int, model: str = "claude-3-sonnet-20240229") -> Path:
        """Create environment file for an agent"""
        env_path = self.config_dir / f".env.{role}"
        
        env_content = f"""# DevTeam Agent Configuration
ROLE={role}
PORT={port}
MODEL={model}
CLAUDE_FILE=config/claude-{role}.md
ANTHROPIC_API_KEY=${{ANTHROPIC_API_KEY}}

# Optional integrations
# GITHUB_REPO=owner/repository
# TELEGRAM_CHANNEL_ID=123456789
"""
        
        env_path.write_text(env_content)
        print(f"✅ Created {env_path}")
        return env_path
        
    def generate_claude_files(self) -> None:
        """Generate CLAUDE.md files for all roles"""
        print("\n📝 Generating CLAUDE.md files...")
        
        script_path = self.project_root / "scripts" / "generate_claude.py"
        if script_path.exists():
            subprocess.run([
                sys.executable, 
                str(script_path), 
                "--all", 
                "--output-dir", 
                str(self.config_dir)
            ])
        else:
            print("⚠️  generate_claude.py not found, skipping CLAUDE.md generation")
            
    def create_example_config(self) -> None:
        """Create example configuration file"""
        example_config = {
            "system": {
                "anthropic_api_key": "YOUR_ANTHROPIC_API_KEY",
                "telegram_bot_token": "YOUR_TELEGRAM_BOT_TOKEN (optional)",
                "telegram_channel_id": "YOUR_TELEGRAM_CHANNEL_ID (optional)",
                "github_token": "YOUR_GITHUB_TOKEN (optional)",
                "github_repo": "owner/repository (optional)"
            },
            "agents": {
                "frontend": {
                    "port": 8301,
                    "model": "claude-3-sonnet-20240229"
                },
                "backend": {
                    "port": 8302,
                    "model": "claude-3-sonnet-20240229"
                },
                "database": {
                    "port": 8303,
                    "model": "claude-3-sonnet-20240229"
                },
                "qa": {
                    "port": 8304,
                    "model": "claude-3-sonnet-20240229"
                },
                "ba": {
                    "port": 8305,
                    "model": "claude-3-sonnet-20240229"
                },
                "teamlead": {
                    "port": 8306,
                    "model": "claude-3-opus-20240229"
                }
            }
        }
        
        config_path = self.config_dir / "config.example.json"
        config_path.write_text(json.dumps(example_config, indent=2))
        print(f"✅ Created {config_path}")
        
    def setup_agents(self, config_file: Optional[Path] = None) -> None:
        """Setup agent environment files based on configuration"""
        if config_file and config_file.exists():
            config = json.loads(config_file.read_text())
            agents_config = config.get("agents", {})
            
            for role, settings in agents_config.items():
                self.create_env_file(
                    role=role,
                    port=settings.get("port", 8300),
                    model=settings.get("model", "claude-3-sonnet-20240229")
                )
        else:
            # Create default agent configurations
            default_agents = [
                ("frontend", 8301),
                ("backend", 8302),
                ("database", 8303),
                ("qa", 8304),
                ("ba", 8305),
                ("teamlead", 8306)
            ]
            
            for role, port in default_agents:
                self.create_env_file(role, port)
                
    def create_startup_scripts(self) -> None:
        """Create convenience startup scripts"""
        # Create start_backend.sh
        backend_script = self.project_root / "start_backend.sh"
        backend_script.write_text("""#!/bin/bash
cd "$(dirname "$0")"
echo "Starting DevTeam Backend..."
poetry run python -m uvicorn web.backend:app --reload --port 8000
""")
        backend_script.chmod(0o755)
        
        # Create start_frontend.sh
        frontend_script = self.project_root / "start_frontend.sh"
        frontend_script.write_text("""#!/bin/bash
cd "$(dirname "$0")/web/frontend"
echo "Starting DevTeam Frontend..."
npm run dev
""")
        frontend_script.chmod(0o755)
        
        # Create start_agent.sh
        agent_script = self.project_root / "start_agent.sh"
        agent_script.write_text("""#!/bin/bash
if [ -z "$1" ]; then
    echo "Usage: ./start_agent.sh <role>"
    echo "Available roles: frontend, backend, database, qa, ba, teamlead"
    exit 1
fi

cd "$(dirname "$0")"
ENV_FILE="config/.env.$1"

if [ ! -f "$ENV_FILE" ]; then
    echo "Environment file not found: $ENV_FILE"
    exit 1
fi

echo "Starting $1 agent..."
poetry run python -m agents.api --env-file "$ENV_FILE"
""")
        agent_script.chmod(0o755)
        
        print("✅ Created startup scripts")
        
    def print_instructions(self) -> None:
        """Print setup completion instructions"""
        print("\n" + "="*60)
        print("🎉 DevTeam setup completed!")
        print("="*60)
        print("\n📋 Next steps:\n")
        print("1. Set your Anthropic API key:")
        print("   export ANTHROPIC_API_KEY='your-api-key-here'")
        print("\n2. Start the backend server:")
        print("   ./start_backend.sh")
        print("\n3. Start the frontend (in a new terminal):")
        print("   ./start_frontend.sh")
        print("\n4. Open http://localhost:3000 in your browser")
        print("\n5. Configure the system in Settings page")
        print("\n6. Create and start agents from the Agents page")
        print("\n" + "="*60)
        
    def run(self, config_file: Optional[Path] = None) -> None:
        """Run the complete setup process"""
        print("🚀 DevTeam Setup Script")
        print("="*60)
        
        if not self.check_dependencies():
            print("\n❌ Please install missing dependencies and run again.")
            sys.exit(1)
            
        if not self.install_dependencies():
            print("\n❌ Failed to install dependencies.")
            sys.exit(1)
            
        self.generate_claude_files()
        self.create_example_config()
        self.setup_agents(config_file)
        self.create_startup_scripts()
        self.print_instructions()


def main():
    parser = argparse.ArgumentParser(description="Setup DevTeam environment")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (JSON)"
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip dependency installation"
    )
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    setup = DevTeamSetup(project_root)
    
    if args.skip_install:
        setup.generate_claude_files()
        setup.create_example_config()
        setup.setup_agents(args.config)
        setup.create_startup_scripts()
        setup.print_instructions()
    else:
        setup.run(args.config)


if __name__ == "__main__":
    main()