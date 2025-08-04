#!/usr/bin/env python3
"""Test agent sandboxing to ensure agents cannot access files outside their workspace"""

import pytest
import tempfile
import os
from pathlib import Path
from core.agent_tools import AgentTools


def test_agent_sandboxing():
    """Test that agents cannot access files outside their workspace"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create agent workspace
        workspace = Path(tmpdir) / "agent_workspace"
        workspace.mkdir(exist_ok=True)
        
        # Create a file outside the workspace
        outside_file = Path(tmpdir) / "outside_file.txt"
        outside_file.write_text("This should not be accessible")
        
        # Initialize agent tools
        tools = AgentTools(str(workspace))
        
        # Test various path traversal attempts
        test_cases = [
            "../outside_file.txt",
            "../../outside_file.txt",
            "../../../../../../../etc/passwd",
            str(outside_file),  # Absolute path outside workspace
            f"{workspace}/../outside_file.txt",
            "subdir/../../outside_file.txt",
            "./../../outside_file.txt",
        ]
        
        for path in test_cases:
            # Should raise ValueError for paths outside workspace
            with pytest.raises(ValueError) as exc_info:
                tools._validate_path(path)
            assert "outside workspace" in str(exc_info.value)
            
            # Test with read_file
            with pytest.raises(ValueError) as exc_info:
                tools.read_file(path)
            assert "outside workspace" in str(exc_info.value)
            
            # Test with write_file
            with pytest.raises(ValueError) as exc_info:
                tools.write_file(path, "test content")
            assert "outside workspace" in str(exc_info.value)


def test_agent_can_access_workspace():
    """Test that agents can still access files within their workspace"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "agent_workspace"
        workspace.mkdir(exist_ok=True)
        
        tools = AgentTools(str(workspace))
        
        # Test creating and reading files in workspace
        test_file = "test.txt"
        test_content = "This is allowed"
        
        # Should work fine
        result = tools.write_file(test_file, test_content)
        assert "File written" in result
        
        # Should be able to read it back
        content = tools.read_file(test_file)
        assert content == test_content
        
        # Test subdirectories
        subdir_file = "subdir/test.txt"
        result = tools.write_file(subdir_file, test_content)
        assert "File written" in result
        
        content = tools.read_file(subdir_file)
        assert content == test_content


def test_symlink_escape_prevention():
    """Test that symlinks cannot be used to escape the workspace"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "agent_workspace"
        workspace.mkdir(exist_ok=True)
        
        # Create a file outside workspace
        outside_file = Path(tmpdir) / "outside_file.txt"
        outside_file.write_text("This should not be accessible")
        
        # Create a symlink inside workspace pointing outside
        symlink = workspace / "escape_link"
        try:
            symlink.symlink_to(outside_file)
        except OSError:
            # Skip test if symlinks not supported
            pytest.skip("Symlinks not supported on this system")
            
        tools = AgentTools(str(workspace))
        
        # Should not be able to access the file through the symlink
        with pytest.raises(ValueError) as exc_info:
            tools.read_file("escape_link")
        assert "outside workspace" in str(exc_info.value)


if __name__ == "__main__":
    test_agent_sandboxing()
    test_agent_can_access_workspace()
    test_symlink_escape_prevention()
    print("All sandboxing tests passed!")