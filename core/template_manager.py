"""Template manager for CLAUDE.md files"""

from pathlib import Path
from typing import List, Optional, Dict
import logging

from .workspace_config import WorkspaceConfig


logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages CLAUDE.md templates for agents"""
    
    def __init__(self, config: WorkspaceConfig):
        self.config = config
        self.system_templates_dir = Path(__file__).parent.parent / "claude_agents"
        self.project_templates_dir = config.maestro_path / "claude_agents"
    
    def get_available_roles(self) -> List[str]:
        """Get list of all available roles from both system and project templates"""
        roles = set()
        
        # Get roles from system templates
        if self.system_templates_dir.exists():
            for template_file in self.system_templates_dir.glob("CLAUDE.md.*"):
                if template_file.name != "CLAUDE.md.common":
                    role = template_file.name.split(".", 2)[2]
                    roles.add(role)
        
        # Get roles from project templates (if maestro is initialized)
        if self.project_templates_dir.exists():
            for template_file in self.project_templates_dir.glob("CLAUDE.md.*"):
                if template_file.name != "CLAUDE.md.common":
                    role = template_file.name.split(".", 2)[2]
                    roles.add(role)
        
        return sorted(list(roles))
    
    def get_template_path(self, role: str) -> Optional[Path]:
        """Get template path for a specific role, preferring project templates"""
        # Check project templates first
        project_template = self.project_templates_dir / f"CLAUDE.md.{role}"
        if project_template.exists():
            logger.info(f"Using project template for {role}")
            return project_template
        
        # Fall back to system templates
        system_template = self.system_templates_dir / f"CLAUDE.md.{role}"
        if system_template.exists():
            logger.info(f"Using system template for {role}")
            return system_template
        
        logger.warning(f"No template found for role: {role}")
        return None
    
    def get_common_template(self) -> str:
        """Get common template content"""
        # Check project common template first
        project_common = self.project_templates_dir / "CLAUDE.md.common"
        if project_common.exists():
            return project_common.read_text()
        
        # Fall back to system common template
        system_common = self.system_templates_dir / "CLAUDE.md.common"
        if system_common.exists():
            return system_common.read_text()
        
        # Default if no common template found
        return "# AI Agent\n\nYou are an AI agent in the DevTeam system.\n"
    
    def generate_claude_md(self, role: str) -> str:
        """Generate complete CLAUDE.md content for a role"""
        # Get common template
        common_content = self.get_common_template()
        
        # Get role-specific template
        role_template_path = self.get_template_path(role)
        if role_template_path:
            role_content = role_template_path.read_text()
        else:
            role_content = f"# {role.title()} Agent\n\nYou are the {role} agent.\n"
        
        # Add codebase structure
        codebase_structure = self._generate_codebase_structure()
        
        # Combine all parts
        full_content = f"{common_content}\n\n"
        full_content += "=" * 80 + "\n\n"
        full_content += f"{role_content}\n\n"
        full_content += "=" * 80 + "\n\n"
        full_content += codebase_structure
        
        return full_content
    
    def _generate_codebase_structure(self) -> str:
        """Generate codebase structure section"""
        maestro_path = self.config.maestro_path
        
        if not maestro_path.exists():
            return "## Codebase Structure\n\n*Codebase not yet initialized*\n"
        
        structure = "## Codebase Structure\n\n```\n"
        
        # Get top-level directories and files
        items = []
        for item in sorted(maestro_path.iterdir()):
            if item.name.startswith('.') or item.name in ['__pycache__', 'logs', '.venv', 'node_modules']:
                continue
            items.append(item)
        
        # Add items to structure
        for item in items[:20]:  # Limit to first 20 items
            if item.is_dir():
                structure += f"{item.name}/\n"
                # Show first level of subdirectories
                sub_items = []
                for subitem in sorted(item.iterdir())[:5]:
                    if not subitem.name.startswith('.') and subitem.name != '__pycache__':
                        sub_items.append(subitem)
                
                for subitem in sub_items:
                    structure += f"  {subitem.name}\n"
            else:
                structure += f"{item.name}\n"
        
        structure += "```\n"
        return structure
    
    def create_custom_role(self, role_name: str, description: str) -> bool:
        """Create a custom role template in the project"""
        try:
            # Ensure project templates directory exists
            self.project_templates_dir.mkdir(parents=True, exist_ok=True)
            
            # Create template file
            template_path = self.project_templates_dir / f"CLAUDE.md.{role_name}"
            template_path.write_text(description)
            
            logger.info(f"Created custom role template: {role_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create custom role: {e}")
            return False
    
    def get_template_info(self) -> Dict[str, Dict[str, str]]:
        """Get information about all available templates"""
        info = {}
        
        for role in self.get_available_roles():
            template_path = self.get_template_path(role)
            if template_path:
                source = "project" if str(self.project_templates_dir) in str(template_path) else "system"
                info[role] = {
                    "source": source,
                    "path": str(template_path)
                }
        
        return info