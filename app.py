import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import uuid

# Import our agent logic
from maestro import Orchestrator, Worker, Refiner, MaestroAgent

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active projects
projects: Dict[str, dict] = {}

class ObjectiveRequest(BaseModel):
    objective: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming guidance if needed
            msg = json.loads(data)
            if msg.get("type") == "guidance":
                project_id = msg.get("projectId")
                if project_id in projects:
                    projects[project_id]["guidance"].append(msg.get("text"))
                    await manager.broadcast({
                        "type": "log",
                        "projectId": project_id,
                        "agent": "User",
                        "text": f"Guidance received: {msg.get('text')}"
                    })
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/start")
async def start_project(req: ObjectiveRequest):
    project_id = str(uuid.uuid4())
    projects[project_id] = {
        "objective": req.objective,
        "tasks": [],
        "results": [],
        "guidance": [],
        "status": "starting"
    }
    
    # Start the orchestration in the background
    asyncio.create_task(run_orchestrator_flow(project_id, req.objective))
    
    return {"projectId": project_id}

async def log_to_gui(project_id, agent_name, text, status="running"):
    await manager.broadcast({
        "type": "log",
        "projectId": project_id,
        "agent": agent_name,
        "text": text,
        "status": status
    })

async def run_orchestrator_flow(project_id, objective):
    orchestrator = Orchestrator()
    worker = Worker()
    refiner = Refiner()

    await log_to_gui(project_id, "Orchestrator", f"Breaking down objective: {objective}")
    
    try:
        # Run synchronous breaking down in a separate thread
        tasks = await asyncio.to_thread(orchestrator.break_down_objective, objective)
        projects[project_id]["tasks"] = tasks
        await log_to_gui(project_id, "Orchestrator", f"Identified {len(tasks)} tasks.")
        
        results = []
        for i, task in enumerate(tasks):
            # Check for user guidance before each task
            if projects[project_id]["guidance"]:
                latest_guidance = projects[project_id]["guidance"][-1]
                task = f"{task} (User Guidance: {latest_guidance})"
                await log_to_gui(project_id, "System", f"Applying guidance to Task {i+1}")

            await log_to_gui(project_id, "Worker", f"Executing Task {i+1}/{len(tasks)}: {task}")
            
            # Run synchronous execution in a separate thread
            result, agent_name = await asyncio.to_thread(worker.execute_task, task)
            results.append(result)
            await log_to_gui(project_id, agent_name, f"Completed Task {i+1}", status="done")

        await log_to_gui(project_id, "Refiner", "Refining final output...")
        
        # Run synchronous refinement in a separate thread
        final_output = await asyncio.to_thread(refiner.refine_results, objective, results)
        
        await manager.broadcast({
            "type": "final_output",
            "projectId": project_id,
            "text": final_output
        })
        
    except Exception as e:
        await log_to_gui(project_id, "System", f"Error: {str(e)}", status="error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
