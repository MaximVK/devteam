from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn

from core.claude_agent import ClaudeAgent, AgentSettings, Task, TaskStatus


class MessageRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class TaskRequest(BaseModel):
    id: str
    title: str
    description: str
    github_issue_number: Optional[int] = None


class AgentAPI:
    def __init__(self, agent: ClaudeAgent):
        self.agent = agent
        self.app = FastAPI(title=f"Claude Agent - {agent.settings.role}")
        self._setup_routes()
        
    def _setup_routes(self):
        @self.app.get("/")
        async def root():
            return {"agent": self.agent.settings.role, "status": "running"}
            
        @self.app.get("/status")
        async def get_status():
            return self.agent.get_status()
            
        @self.app.post("/ask")
        async def ask_agent(request: MessageRequest):
            response = await self.agent.process_message(request.message, request.context)
            return {"response": response}
            
        @self.app.post("/assign")
        async def assign_task(request: TaskRequest):
            task = Task(
                id=request.id,
                title=request.title,
                description=request.description,
                github_issue_number=request.github_issue_number
            )
            await self.agent.assign_task(task)
            return {"status": "assigned", "task": task.model_dump()}
            
        @self.app.post("/complete")
        async def complete_task():
            completed = await self.agent.complete_task()
            if completed:
                return {"status": "completed", "task": completed.model_dump()}
            else:
                raise HTTPException(status_code=400, detail="No active task to complete")
                
        @self.app.get("/history")
        async def get_history():
            return {
                "task_history": [task.model_dump() for task in self.agent.state.task_history],
                "message_history": self.agent.state.messages[-50:]  # Last 50 messages
            }
            
    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.agent.settings.port)


def create_agent_api(env_file: str = ".env") -> AgentAPI:
    settings = AgentSettings(_env_file=env_file)
    agent = ClaudeAgent(settings)
    return AgentAPI(agent)


if __name__ == "__main__":
    api = create_agent_api()
    api.run()