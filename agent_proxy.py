#!/usr/bin/env python3
"""Simple proxy to expose running agents to the web UI"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from typing import List, Dict, Any

app = FastAPI(title="DevTeam Agent Proxy")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agent configuration
AGENTS = [
    {"role": "backend", "port": 8301, "status": "unknown"},
    {"role": "frontend", "port": 8302, "status": "unknown"},
    {"role": "database", "port": 8303, "status": "unknown"},
    {"role": "qa", "port": 8304, "status": "unknown"},
    {"role": "ba", "port": 8305, "status": "unknown"},
    {"role": "teamlead", "port": 8306, "status": "unknown"}
]

async def check_agent_status(agent: Dict[str, Any]) -> Dict[str, Any]:
    """Check if an agent is running"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:{agent['port']}/", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                return {
                    "role": agent["role"],
                    "port": agent["port"],
                    "status": "running",
                    "url": f"http://localhost:{agent['port']}",
                    "data": data
                }
    except:
        pass
    
    return {
        "role": agent["role"],
        "port": agent["port"],
        "status": "offline",
        "url": f"http://localhost:{agent['port']}"
    }

@app.get("/")
async def root():
    return {"message": "DevTeam Agent Proxy", "agents_count": len(AGENTS)}

@app.get("/agents")
async def get_agents() -> List[Dict[str, Any]]:
    """Get all agents and their current status"""
    tasks = [check_agent_status(agent) for agent in AGENTS]
    results = await asyncio.gather(*tasks)
    return results

@app.get("/agents/{role}")
async def get_agent(role: str):
    """Get specific agent info"""
    agent = next((a for a in AGENTS if a["role"] == role), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return await check_agent_status(agent)

@app.post("/agents/{role}/ask")
async def ask_agent(role: str, message: dict):
    """Forward a message to an agent"""
    agent = next((a for a in AGENTS if a["role"] == role), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:{agent['port']}/ask",
                json=message,
                timeout=30.0
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Agent communication failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)