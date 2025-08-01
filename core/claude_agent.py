import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

import anthropic
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings


class AgentRole(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    QA = "qa"
    BA = "ba"
    TEAMLEAD = "teamlead"


class AgentSettings(BaseSettings):
    role: AgentRole
    port: int
    model: str = "claude-3-5-sonnet-20241022"
    claude_file: str = "claude.md"
    telegram_channel_id: Optional[str] = None
    github_repo: Optional[str] = None
    anthropic_api_key: str
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class Task(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.TODO
    assigned_to: Optional[str] = None
    github_issue_number: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    
class AgentState(BaseModel):
    current_task: Optional[Task] = None
    task_history: List[Task] = []
    last_activity: datetime = Field(default_factory=datetime.now)
    total_tokens_used: int = 0
    messages: List[Dict[str, Any]] = []


class ClaudeAgent:
    def __init__(self, settings: AgentSettings):
        self.settings = settings
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        self.state = AgentState()
        self._system_prompt: Optional[str] = None
        
    @property
    def system_prompt(self) -> str:
        if self._system_prompt is None:
            self._load_system_prompt()
        return self._system_prompt or ""
        
    def _load_system_prompt(self) -> None:
        prompt_path = Path(self.settings.claude_file)
        if prompt_path.exists():
            self._system_prompt = prompt_path.read_text()
        else:
            self._system_prompt = self._generate_default_prompt()
            
    def _generate_default_prompt(self) -> str:
        common = """# COMMON

You are an AI developer agent in a simulated software team. 
Follow these principles:
- Stay within your assigned role
- Communicate through GitHub PRs, Issues, and Telegram
- Write clean, testable code
- Commit incrementally
- Follow project conventions
"""
        
        role_specific = {
            AgentRole.BACKEND: """
# ROLE: backend

Responsibilities:
- Implement FastAPI services
- Work with asyncpg and PostgreSQL
- Create PRs and assign them to QA
- Respond to GitHub Issue tasks
- Write unit and integration tests

Do not write frontend code or perform QA duties.
""",
            AgentRole.FRONTEND: """
# ROLE: frontend

Responsibilities:
- Implement React components and TypeScript
- Create responsive UI/UX
- Integrate with backend APIs
- Handle state management
- Write component tests

Do not write backend code or database migrations.
""",
            AgentRole.DATABASE: """
# ROLE: database

Responsibilities:
- Design database schemas
- Write and review migrations
- Optimize queries
- Ensure data integrity
- Document database structure

Focus only on database-related tasks.
""",
            AgentRole.QA: """
# ROLE: qa

Responsibilities:
- Review PRs for code quality
- Write and execute test cases
- Report bugs via GitHub Issues
- Verify fixes
- Ensure test coverage

Do not write feature code, only tests and reviews.
""",
            AgentRole.BA: """
# ROLE: ba

Responsibilities:
- Transform business requirements into technical tasks
- Create detailed GitHub Issues
- Clarify requirements
- Prioritize features
- Document acceptance criteria

Do not write code, focus on specifications.
""",
            AgentRole.TEAMLEAD: """
# ROLE: teamlead

Responsibilities:
- Review and prioritize tasks
- Coordinate between team members
- Make architectural decisions
- Resolve blockers
- Ensure code quality standards

Guide the team but avoid implementing features directly.
"""
        }
        
        return common + role_specific.get(self.settings.role, "")
        
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        try:
            messages = [
                {"role": "user", "content": message}
            ]
            
            if context and "task" in context:
                task_context = f"\n\nCurrent task: {context['task'].title}\nDescription: {context['task'].description}"
                messages[0]["content"] = task_context + "\n\n" + message
                
            response = self.client.messages.create(
                model=self.settings.model,
                max_tokens=4000,
                temperature=0.7,
                system=self.system_prompt,
                messages=messages
            )
            
            self.state.total_tokens_used += response.usage.input_tokens + response.usage.output_tokens
            self.state.last_activity = datetime.now()
            self.state.messages.append({
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "assistant_response": response.content[0].text,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens
            })
            
            return response.content[0].text
            
        except Exception as e:
            return f"Error processing message: {str(e)}"
            
    async def assign_task(self, task: Task) -> None:
        self.state.current_task = task
        task.assigned_to = self.settings.role
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.now()
        
    async def complete_task(self) -> Optional[Task]:
        if self.state.current_task:
            self.state.current_task.status = TaskStatus.DONE
            self.state.current_task.updated_at = datetime.now()
            self.state.task_history.append(self.state.current_task)
            completed = self.state.current_task
            self.state.current_task = None
            return completed
        return None
        
    def get_status(self) -> Dict[str, Any]:
        return {
            "role": self.settings.role,
            "port": self.settings.port,
            "model": self.settings.model,
            "current_task": self.state.current_task.model_dump() if self.state.current_task else None,
            "task_history_count": len(self.state.task_history),
            "last_activity": self.state.last_activity.isoformat(),
            "total_tokens_used": self.state.total_tokens_used,
            "health": "active" if (datetime.now() - self.state.last_activity).seconds < 300 else "idle"
        }