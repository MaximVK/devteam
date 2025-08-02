#!/usr/bin/env python3
"""Set up an agent's workspace with cloned repo and CLAUDE.md file"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse


def setup_agent_workspace(agent_role: str, workspace_base: str, repo_url: str = None):
    """Set up a complete workspace for an agent"""
    
    # Define paths
    workspace_path = Path(workspace_base) / agent_role
    claude_templates_dir = Path(__file__).parent.parent / "claude_agents"
    
    print(f"🚀 Setting up workspace for {agent_role} agent...")
    
    # Create workspace directory
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created workspace directory: {workspace_path}")
    
    # Clone repository if URL provided and directory doesn't exist
    repo_path = workspace_path / "devteam"
    if repo_url and not repo_path.exists():
        print(f"📦 Cloning repository...")
        subprocess.run(
            ["git", "clone", repo_url, str(repo_path)],
            check=True
        )
        print(f"✅ Cloned repository to: {repo_path}")
    elif repo_path.exists():
        print(f"ℹ️  Repository already exists at: {repo_path}")
    else:
        # Copy current devteam directory if no repo URL
        current_devteam = Path(__file__).parent.parent
        print(f"📋 Copying local devteam to workspace...")
        shutil.copytree(current_devteam, repo_path, dirs_exist_ok=True)
        print(f"✅ Copied devteam to: {repo_path}")
    
    # Create CLAUDE.md file
    claude_file = repo_path / "CLAUDE.md"
    common_template = claude_templates_dir / "CLAUDE.md.common"
    role_template = claude_templates_dir / f"CLAUDE.md.{agent_role}"
    
    if not common_template.exists():
        print(f"❌ Common template not found: {common_template}")
        return False
    
    if not role_template.exists():
        print(f"❌ Role template not found: {role_template}")
        return False
    
    # Combine templates
    print(f"📝 Creating CLAUDE.md file...")
    with open(claude_file, 'w') as f:
        # Write common content
        f.write(common_template.read_text())
        f.write("\n\n")
        f.write("=" * 80)
        f.write("\n\n")
        # Write role-specific content
        f.write(role_template.read_text())
        f.write("\n\n")
        f.write("=" * 80)
        f.write("\n\n")
        # Add codebase structure
        f.write("## Codebase Structure\n\n")
        f.write("```\n")
        # Add tree view of important directories
        for item in sorted(repo_path.iterdir()):
            if item.name.startswith('.') or item.name in ['__pycache__', 'logs', '.venv']:
                continue
            if item.is_dir():
                f.write(f"{item.name}/\n")
                # Show first level of subdirectories
                for subitem in sorted(item.iterdir())[:5]:
                    if subitem.name.startswith('.') or subitem.name == '__pycache__':
                        continue
                    f.write(f"  {subitem.name}\n")
            else:
                f.write(f"{item.name}\n")
        f.write("```\n")
    
    print(f"✅ Created CLAUDE.md at: {claude_file}")
    
    # Create agent-specific directories if needed
    if agent_role == "frontend":
        frontend_workspace = repo_path / "web" / "frontend"
        print(f"📁 Frontend agent will work in: {frontend_workspace}")
    elif agent_role == "backend":
        backend_workspace = repo_path / "web" / "backend"
        print(f"📁 Backend agent will work in: {backend_workspace}")
    
    print(f"\n✨ Workspace setup complete for {agent_role} agent!")
    print(f"📍 Workspace location: {workspace_path}")
    print(f"📄 CLAUDE.md location: {claude_file}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Set up agent workspace")
    parser.add_argument("role", help="Agent role (backend, frontend, database, qa, ba, teamlead)")
    parser.add_argument("--workspace", default="/Users/maxim/dev/agent-workspace", 
                       help="Base workspace directory")
    parser.add_argument("--repo-url", help="Git repository URL to clone")
    
    args = parser.parse_args()
    
    success = setup_agent_workspace(args.role, args.workspace, args.repo_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()