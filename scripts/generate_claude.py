#!/usr/bin/env python3
"""Generate CLAUDE.md files for different roles"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_common_template() -> str:
    """Load the common CLAUDE.md template"""
    template_path = Path(__file__).parent.parent / "templates" / "claude_common.md"
    return template_path.read_text()


def load_role_templates() -> Dict[str, Any]:
    """Load role-specific templates from YAML"""
    template_path = Path(__file__).parent.parent / "templates" / "claude_roles.yaml"
    with open(template_path, 'r') as f:
        return yaml.safe_load(f)


def generate_claude_file(role: str, output_dir: Path) -> Path:
    """Generate a CLAUDE.md file for a specific role"""
    common = load_common_template()
    roles = load_role_templates()
    
    if role not in roles:
        raise ValueError(f"Unknown role: {role}")
    
    role_content = roles[role]["description"]
    
    # Combine common and role-specific content
    full_content = f"{common}\n\n{role_content}"
    
    # Write to file
    output_file = output_dir / f"claude-{role}.md"
    output_file.write_text(full_content)
    
    return output_file


def generate_all_claude_files(output_dir: Path) -> None:
    """Generate CLAUDE.md files for all roles"""
    roles = load_role_templates()
    
    for role in roles:
        output_file = generate_claude_file(role, output_dir)
        print(f"Generated: {output_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate CLAUDE.md files")
    parser.add_argument("--role", help="Generate for specific role")
    parser.add_argument("--output-dir", default="config", help="Output directory")
    parser.add_argument("--all", action="store_true", help="Generate for all roles")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    if args.all:
        generate_all_claude_files(output_dir)
    elif args.role:
        output_file = generate_claude_file(args.role, output_dir)
        print(f"Generated: {output_file}")
    else:
        parser.print_help()