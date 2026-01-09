import json
import asyncio
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
from pathlib import Path

from config import (
    OLLAMA_API_URL, OLLAMA_CHAT_URL, DEFAULT_MODEL, 
    get_model_for_role, get_available_models, set_model_preset,
    is_cloud_model, get_provider_for_model, ModelProvider,
    OPENAI_API_KEY, ANTHROPIC_API_KEY, CLOUD_CONFIGS
)
from project_manager import project_manager, Project
from memory_store import MemoryStore

app = FastAPI(title="Maestro V2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
active_projects: Dict[str, dict] = {}

class ObjectiveRequest(BaseModel):
    objective: str
    project_name: Optional[str] = None

class GuidanceRequest(BaseModel):
    project_id: str
    text: str

class ProjectRequest(BaseModel):
    name: str

class ModelPresetRequest(BaseModel):
    preset: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# API for LLM calls
async def call_llm(model: str, prompt: str, system_prompt: str = "") -> str:
    """Universal LLM caller supporting Ollama and cloud providers"""
    if is_cloud_model(model):
        return await call_cloud_llm(model, prompt, system_prompt)
    return await call_ollama(model, prompt, system_prompt)

async def call_ollama(model: str, prompt: str, system_prompt: str = "") -> str:
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    payload = {"model": model, "prompt": full_prompt, "stream": False}
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(OLLAMA_API_URL, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            return f"Error: {str(e)}"

async def call_cloud_llm(model: str, prompt: str, system_prompt: str = "") -> str:
    provider = get_provider_for_model(model)
    
    if provider == ModelProvider.OPENAI:
        return await call_openai(model, prompt, system_prompt)
    elif provider == ModelProvider.ANTHROPIC:
        return await call_anthropic(model, prompt, system_prompt)
    return "Error: Unknown cloud provider"

async def call_openai(model: str, prompt: str, system_prompt: str = "") -> str:
    if not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY not set"
    
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {"model": model, "messages": messages}
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(CLOUD_CONFIGS["openai"]["base_url"], json=payload, headers=headers)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error: {str(e)}"

async def call_anthropic(model: str, prompt: str, system_prompt: str = "") -> str:
    if not ANTHROPIC_API_KEY:
        return "Error: ANTHROPIC_API_KEY not set"
    
    headers = {"x-api-key": ANTHROPIC_API_KEY, "Content-Type": "application/json", "anthropic-version": "2023-06-01"}
    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": system_prompt if system_prompt else "You are a helpful assistant.",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(CLOUD_CONFIGS["anthropic"]["base_url"], json=payload, headers=headers)
            response.raise_for_status()
            return response.json()["content"][0]["text"]
        except Exception as e:
            return f"Error: {str(e)}"

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "guidance":
                project_id = msg.get("projectId")
                if project_id in active_projects:
                    active_projects[project_id]["guidance"].append(msg.get("text"))
                    await manager.broadcast({
                        "type": "log", "projectId": project_id,
                        "agent": "User", "text": f"Guidance: {msg.get('text')}"
                    })
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Project Management Endpoints
@app.get("/projects")
async def list_projects():
    return {"projects": project_manager.list_projects()}

@app.post("/projects/create")
async def create_project(req: ProjectRequest):
    project = project_manager.create_project(req.name)
    return {"success": True, "path": str(project.path), "name": project.name}

@app.post("/projects/open")
async def open_project(path: str):
    try:
        project = project_manager.open_project(path)
        return {"success": True, "project": project.config}
    except FileNotFoundError as e:
        return {"success": False, "error": str(e)}

@app.delete("/projects/{path:path}")
async def delete_project(path: str):
    project_manager.delete_project(path)
    return {"success": True}

# Model Configuration Endpoints
@app.get("/models/presets")
async def get_model_presets():
    return {"presets": get_available_models()}

@app.post("/models/preset")
async def set_preset(req: ModelPresetRequest):
    success = set_model_preset(req.preset)
    return {"success": success}

# Orchestration Endpoints
@app.post("/start")
async def start_project(req: ObjectiveRequest):
    project_id = str(uuid.uuid4())
    
    # Create or use project
    if req.project_name:
        project = project_manager.create_project(req.project_name)
    else:
        project = project_manager.create_project(f"Project_{project_id[:8]}")
    
    project.set_objective(req.objective)
    memory_store = MemoryStore(project.path)
    
    active_projects[project_id] = {
        "project": project,
        "memory_store": memory_store,
        "objective": req.objective,
        "tasks": [],
        "results": [],
        "guidance": [],
        "status": "starting"
    }
    
    asyncio.create_task(run_orchestration(project_id))
    return {"projectId": project_id, "projectPath": str(project.path)}

async def log_to_gui(project_id: str, agent: str, text: str, status: str = "running"):
    # Also log to memory store
    if project_id in active_projects:
        memory = active_projects[project_id]["memory_store"]
        agent_memory = memory.get_agent_memory(agent)
        agent_memory.log("output", text)
    
    await manager.broadcast({
        "type": "log", "projectId": project_id,
        "agent": agent, "text": text, "status": status
    })

async def run_orchestration(project_id: str):
    ctx = active_projects[project_id]
    project = ctx["project"]
    memory = ctx["memory_store"]
    objective = ctx["objective"]
    
    # Get agent memories
    orch_mem = memory.get_agent_memory("Orchestrator")
    
    await log_to_gui(project_id, "Orchestrator", f"Analyzing objective: {objective}")
    orch_mem.think(f"Breaking down objective: {objective}")
    
    # Phase 1: Break down objective
    model = get_model_for_role("orchestrator")
    system_prompt = """You are the Orchestrator. Break down the objective into specific tasks.
Categorize each task by who should do it: UI/UX, Developer, or QA.
Output ONLY a JSON array of objects: [{"task": "...", "assignee": "UI/UX|Developer|QA"}, ...]"""
    
    response = await call_llm(model, f"Objective: {objective}", system_prompt)
    orch_mem.decide(f"Task breakdown complete")
    
    # Parse tasks
    try:
        clean = response.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0]
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0]
        tasks = json.loads(clean)
    except:
        tasks = [{"task": line.strip(), "assignee": "Developer"} for line in response.split('\n') if line.strip()]
    
    ctx["tasks"] = tasks
    project.add_tasks([t.get("task", str(t)) for t in tasks])
    await log_to_gui(project_id, "Orchestrator", f"Identified {len(tasks)} tasks")
    
    # Phase 2: Execute tasks in parallel groups
    results = []
    
    # Group tasks by assignee for parallel execution
    ui_tasks = [(i, t) for i, t in enumerate(tasks) if t.get("assignee") == "UI/UX"]
    dev_tasks = [(i, t) for i, t in enumerate(tasks) if t.get("assignee") == "Developer"]
    qa_tasks = [(i, t) for i, t in enumerate(tasks) if t.get("assignee") == "QA"]
    
    # Execute UI and Dev tasks in parallel
    async def execute_task(idx: int, task_info: dict, agent_name: str):
        task = task_info.get("task", str(task_info))
        agent_mem = memory.get_agent_memory(agent_name)
        
        # Check for guidance
        guidance = ""
        if ctx["guidance"]:
            guidance = f"\nUser Guidance: {ctx['guidance'][-1]}"
            await log_to_gui(project_id, "System", f"Applying guidance to Task {idx + 1}")
        
        # Get context from other agents
        project_ctx = memory.get_project_context()
        
        await log_to_gui(project_id, agent_name, f"Working on Task {idx + 1}: {task[:50]}...")
        agent_mem.think(f"Starting task: {task}")
        
        model = get_model_for_role(agent_name)
        system_prompt = f"""You are a {agent_name}. Complete the task thoroughly.
Project Context:
{project_ctx}
{guidance}"""
        
        result = await call_llm(model, task, system_prompt)
        agent_mem.output(result[:500])
        await log_to_gui(project_id, agent_name, f"Completed Task {idx + 1}", status="done")
        
        return (idx, result)
    
    # Run UI/UX and Dev tasks in parallel
    parallel_tasks = []
    for idx, task in ui_tasks:
        parallel_tasks.append(execute_task(idx, task, "UI/UX Designer"))
    for idx, task in dev_tasks:
        parallel_tasks.append(execute_task(idx, task, "Developer"))
    
    if parallel_tasks:
        completed = await asyncio.gather(*parallel_tasks)
        results.extend(completed)
    
    # Run QA tasks after (they need outputs to verify)
    for idx, task in qa_tasks:
        result = await execute_task(idx, task, "QA Tester")
        results.append(result)
    
    # Sort results by original index
    results.sort(key=lambda x: x[0])
    result_texts = [r[1] for r in results]
    
    # Phase 3: Refine
    await log_to_gui(project_id, "Refiner", "Synthesizing final output...")
    refiner_mem = memory.get_agent_memory("Refiner")
    
    model = get_model_for_role("refiner")
    context = "\n\n".join([f"--- Result {i+1} ---\n{r}" for i, r in enumerate(result_texts)])
    system_prompt = f"""You are the Refiner. Synthesize all agent outputs into a polished final deliverable.
Original Objective: {objective}
"""
    
    final_output = await call_llm(model, f"Synthesize these results:\n{context}", system_prompt)
    refiner_mem.output(final_output)
    
    # Save to project
    output_path = project.output_dir / "final_output.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Final Output\n\n{final_output}")
    
    project.config["status"] = "completed"
    project.save()
    
    await manager.broadcast({
        "type": "final_output",
        "projectId": project_id,
        "text": final_output,
        "outputPath": str(output_path)
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
