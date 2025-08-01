#!/usr/bin/env python3
"""Conversation history management for agents"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path


class ConversationHistory:
    """Manages conversation history for agents"""
    
    def __init__(self, storage_dir: str = "data/conversations"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def get_agent_history_file(self, agent_role: str) -> Path:
        """Get the history file path for an agent"""
        return self.storage_dir / f"{agent_role}_history.json"
    
    def add_message(self, agent_role: str, user_message: str, agent_response: str, 
                   context: Optional[Dict[str, Any]] = None) -> None:
        """Add a message exchange to agent's history"""
        history_file = self.get_agent_history_file(agent_role)
        
        # Load existing history
        history = self.load_agent_history(agent_role)
        
        # Add new message
        message_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "agent_response": agent_response,
            "context": context or {}
        }
        
        history.append(message_entry)
        
        # Keep only last 50 messages to prevent unlimited growth
        if len(history) > 50:
            history = history[-50:]
        
        # Save updated history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def load_agent_history(self, agent_role: str) -> List[Dict[str, Any]]:
        """Load conversation history for an agent"""
        history_file = self.get_agent_history_file(agent_role)
        
        if not history_file.exists():
            return []
        
        try:
            with open(history_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def get_recent_context(self, agent_role: str, hours: int = 24) -> str:
        """Get recent conversation context for an agent"""
        history = self.load_agent_history(agent_role)
        
        if not history:
            return "No previous conversation history."
        
        # Filter messages from the last N hours
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_messages = []
        
        for entry in history:
            try:
                msg_time = datetime.fromisoformat(entry["timestamp"])
                if msg_time > cutoff_time:
                    recent_messages.append(entry)
            except (ValueError, KeyError):
                continue
        
        if not recent_messages:
            return f"No conversation history in the last {hours} hours."
        
        # Format context for the agent
        context_parts = ["## Recent Conversation History\n"]
        
        for entry in recent_messages[-10:]:  # Last 10 messages
            timestamp = entry.get("timestamp", "unknown")
            user_msg = entry.get("user_message", "")
            agent_resp = entry.get("agent_response", "")
            
            # Truncate long messages
            if len(user_msg) > 200:
                user_msg = user_msg[:200] + "..."
            if len(agent_resp) > 300:
                agent_resp = agent_resp[:300] + "..."
            
            context_parts.append(f"**{timestamp}**")
            context_parts.append(f"User: {user_msg}")
            context_parts.append(f"You responded: {agent_resp}")
            context_parts.append("---")
        
        return "\n".join(context_parts)
    
    def get_task_context(self, agent_role: str) -> str:
        """Get context about ongoing tasks and recent work"""
        history = self.load_agent_history(agent_role)
        
        if not history:
            return "No task history available."
        
        # Look for task-related keywords in recent messages
        task_keywords = ["task", "implement", "create", "fix", "update", "change", "feature", "bug"]
        task_messages = []
        
        for entry in history[-20:]:  # Check last 20 messages
            user_msg = entry.get("user_message", "").lower()
            agent_resp = entry.get("agent_response", "").lower()
            
            if any(keyword in user_msg or keyword in agent_resp for keyword in task_keywords):
                task_messages.append(entry)
        
        if not task_messages:
            return "No recent task-related conversation found."
        
        # Format task context
        context_parts = ["## Recent Task Context\n"]
        
        for entry in task_messages[-5:]:  # Last 5 task-related messages
            timestamp = entry.get("timestamp", "unknown")
            user_msg = entry.get("user_message", "")
            
            context_parts.append(f"**{timestamp}**: {user_msg}")
        
        return "\n".join(context_parts)
    
    def clear_agent_history(self, agent_role: str) -> None:
        """Clear conversation history for an agent"""
        history_file = self.get_agent_history_file(agent_role)
        if history_file.exists():
            history_file.unlink()
    
    def get_all_agents_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all agents' recent activity"""
        summary = {}
        
        for history_file in self.storage_dir.glob("*_history.json"):
            agent_role = history_file.stem.replace("_history", "")
            history = self.load_agent_history(agent_role)
            
            if history:
                last_message = history[-1]
                summary[agent_role] = {
                    "last_activity": last_message.get("timestamp"),
                    "message_count": len(history),
                    "last_user_message": last_message.get("user_message", "")[:100] + "..." if len(last_message.get("user_message", "")) > 100 else last_message.get("user_message", "")
                }
            else:
                summary[agent_role] = {
                    "last_activity": None,
                    "message_count": 0,
                    "last_user_message": "No messages"
                }
        
        return summary