import json
import asyncio
import httpx
import os
import sys
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
from pathlib import Path

# Fix for PyInstaller path handling
def get_base_path():
    if getattr(sys, 'frozen', False):
        # Running in a bundle
        return Path(sys._MEIPASS)
    else:
        # Running in normal Python environment
        return Path(__file__).parent

def get_executable_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

BASE_DIR = get_base_path()

# Import from local modules
sys.path.append(str(BASE_DIR))
from config import (
    OLLAMA_API_URL, OLLAMA_CHAT_URL, DEFAULT_MODEL, 
    get_model_for_role, get_available_models, set_model_preset,
    is_cloud_model, get_provider_for_model, ModelProvider,
    OPENAI_API_KEY, ANTHROPIC_API_KEY, CLOUD_CONFIGS, NOCOST_API_URL
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

# --- [API Endpoints Placeholder] ---
# (I'll keep the logic but move static files to the end)

# ... (rest of the code remains same until uvicorn.run)

# [KEEP ALL PREVIOUS FUNCTIONS: call_llm, call_ollama, etc.]
# (I'm skipping them for the diff block but they are there)

# ... [insert previous functions here] ...
# (Wait, I need to provide the FULL replacement content or chunks. I'll use chunks.)

class ObjectiveRequest(BaseModel):
    objective: str
    project_name: Optional[str] = None

class GuidanceRequest(BaseModel):
    project_id: str
    text: str

class ProjectRequest(BaseModel):
    name: str

class ImportProjectRequest(BaseModel):
    path: str
    name: Optional[str] = None

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
    elif provider == ModelProvider.NOCOST:
        return await call_nocost_api(model, prompt, system_prompt)
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

async def call_nocost_api(model: str, prompt: str, system_prompt: str = "") -> str:
    """Call the free no-cost API using ollamafreeapi library"""
    import asyncio
    
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    
    def sync_call():
        try:
            from ollamafreeapi import OllamaFreeAPI
            api = OllamaFreeAPI()
            response = api.chat(model_name=model, prompt=full_prompt, temperature=0.7)
            return response
        except Exception as e:
            return f"Error calling free API: {str(e)}"
    
    # Run the synchronous API call in a thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_call)

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

@app.post("/projects/import")
async def import_existing_project(req: ImportProjectRequest):
    """Import an existing external project directory"""
    try:
        project = project_manager.import_existing_project(req.path, req.name)
        return {
            "success": True,
            "path": str(project.path),
            "name": project.name,
            "project_type": project.config.get("project_type", {}),
            "is_external": True
        }
    except FileNotFoundError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/projects/analyze")
async def analyze_project_path(req: ImportProjectRequest):
    """Analyze a directory to detect project type without importing"""
    try:
        path = Path(req.path)
        if not path.exists():
            return {"success": False, "error": "Directory not found"}
        
        project_type = project_manager._analyze_project_type(path)
        return {
            "success": True,
            "path": str(path),
            "project_type": project_type
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/projects/{path:path}")
async def delete_project(path: str):
    """Delete a project"""
    try:
        import shutil
        project_path = Path(path)
        if project_path.exists():
            shutil.rmtree(project_path)
            return {"success": True, "message": "Project deleted"}
        return {"success": False, "error": "Project not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/files")
async def list_project_files():
    """List all files in current project"""
    if not project_manager.current_project:
        return {"files": [], "error": "No project open"}
    
    try:
        files = []
        project_path = project_manager.current_project.path
        output_dir = project_path / "output"
        
        if output_dir.exists():
            for item in output_dir.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(project_path)
                    files.append({
                        "name": item.name,
                        "path": str(rel_path),
                        "full_path": str(item),
                        "size": item.stat().st_size,
                        "ext": item.suffix
                    })
        
        return {"files": files, "project": project_manager.current_project.name}
    except Exception as e:
        return {"files": [], "error": str(e)}

@app.get("/files/{file_path:path}")
async def get_file_content(file_path: str):
    """Get content of a specific file"""
    if not project_manager.current_project:
        return {"content": "", "error": "No project open"}
    
    try:
        full_path = project_manager.current_project.path / file_path
        if full_path.exists() and full_path.is_file():
            # Check file size (limit to 500KB for preview)
            if full_path.stat().st_size > 500000:
                return {"content": "File too large to preview", "truncated": True}
            
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return {"content": content, "path": file_path}
        return {"content": "", "error": "File not found"}
    except Exception as e:
        return {"content": "", "error": str(e)}

@app.get("/logs/{agent}")
async def get_agent_logs(agent: str):
    try:
        if not project_manager.current_project:
            return {"logs": "No active project. Start or open a project first."}
        
        # Initialize MemoryStore with the current project path
        memory = MemoryStore(project_manager.current_project.path)
        # Fetch logs for the specified agent
        # We use a naming mapping for frontend to internal agent names if needed
        agent_map = {
            "orchestrator": "Orchestrator",
            "research": "Research",
            "uiux": "UI/UX Designer",
            "developer": "Developer",
            "security": "Security",
            "qa": "QA Tester",
            "documentation": "Documentation",
            "refiner": "Refiner"
        }
        target_agent = agent_map.get(agent.lower(), agent.title())
        content = memory.read_other_agent_logs(target_agent, limit=5)
        
        return {"logs": content if content else f"No logs found for {target_agent} yet."}
    except Exception as e:
        return {"logs": f"Error loading logs: {str(e)}"}

# Model Configuration Endpoints
@app.get("/models/presets")
async def get_model_presets():
    return {"presets": get_available_models()}

@app.post("/models/preset")
async def set_preset(req: ModelPresetRequest):
    success = set_model_preset(req.preset)
    return {"success": success}

# Ollama Management Endpoints
@app.get("/ollama/status")
async def get_ollama_status():
    """Check if Ollama server is running and get version"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_API_URL.replace('/api/generate', '')}")
            if response.status_code == 200:
                return {"online": True, "message": "Ollama is running"}
            return {"online": False, "message": f"Ollama returned status {response.status_code}"}
    except Exception as e:
        return {"online": False, "message": f"Ollama not reachable: {str(e)}"}

@app.get("/ollama/models")
async def list_ollama_models():
    """Get list of downloaded Ollama models"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_API_URL.replace('/api/generate', '/api/tags')}")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                return {
                    "success": True,
                    "models": [
                        {
                            "name": m.get("name", "unknown"),
                            "size": m.get("size", 0),
                            "modified": m.get("modified_at", "")
                        }
                        for m in models
                    ]
                }
            return {"success": False, "models": [], "error": "Failed to fetch models"}
    except Exception as e:
        return {"success": False, "models": [], "error": str(e)}

class ModelPullRequest(BaseModel):
    name: str

@app.post("/ollama/pull")
async def pull_ollama_model(req: ModelPullRequest):
    """Start downloading an Ollama model"""
    import subprocess
    try:
        # Start ollama pull in background
        process = subprocess.Popen(
            ["ollama", "pull", req.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return {"success": True, "message": f"Started downloading {req.name}"}
    except FileNotFoundError:
        return {"success": False, "error": "Ollama not found. Please install Ollama first."}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/ollama/start")
async def start_ollama_server():
    """Try to start Ollama server"""
    import subprocess
    try:
        # Try to start ollama serve in background
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return {"success": True, "message": "Ollama server starting..."}
    except FileNotFoundError:
        return {"success": False, "error": "Ollama not found. Please install from https://ollama.ai"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/ollama/models-path")
async def get_ollama_models_path():
    """Get the path to Ollama models folder for backup"""
    import os
    # Ollama stores models in user home directory
    if sys.platform == "win32":
        models_path = os.path.expanduser("~\\.ollama\\models")
    else:
        models_path = os.path.expanduser("~/.ollama/models")
    return {"path": models_path, "exists": os.path.exists(models_path)}

@app.post("/ollama/open-models-folder")
async def open_ollama_models_folder():
    """Open Ollama models folder in file explorer"""
    import os
    import subprocess
    
    if sys.platform == "win32":
        models_path = os.path.expanduser("~\\.ollama\\models")
        if os.path.exists(models_path):
            subprocess.Popen(f'explorer "{models_path}"')
            return {"success": True}
    else:
        models_path = os.path.expanduser("~/.ollama/models")
        if os.path.exists(models_path):
            subprocess.Popen(['xdg-open', models_path])
            return {"success": True}
    return {"success": False, "error": "Models folder not found"}

# No-Cost Free API Endpoints
@app.get("/nocost/status")
async def get_nocost_status():
    """Check if the no-cost free API is available"""
    import asyncio
    
    def check_status():
        try:
            from ollamafreeapi import OllamaFreeAPI
            api = OllamaFreeAPI()
            models = api.list_models()
            if models and len(models) > 0:
                return {"online": True, "message": f"Free API is available ({len(models)} models)", "model_count": len(models)}
            return {"online": False, "message": "No models available"}
        except Exception as e:
            return {"online": False, "message": f"Free API error: {str(e)}"}
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, check_status)

@app.get("/nocost/models")
async def list_nocost_models():
    """Get list of available models from the no-cost free API"""
    import asyncio
    
    def get_models():
        try:
            from ollamafreeapi import OllamaFreeAPI
            api = OllamaFreeAPI()
            models = api.list_models()
            # Deduplicate and limit to 20 models
            unique_models = list(dict.fromkeys(models))[:20]
            return {
                "success": True,
                "models": [{"name": m, "size": 0, "modified": ""} for m in unique_models],
                "total_available": len(models)
            }
        except Exception as e:
            # Fallback to static list from config
            from config import CLOUD_CONFIGS
            nocost_models = CLOUD_CONFIGS.get("nocost", {}).get("models", [])
            return {
                "success": True,
                "models": [{"name": m, "size": 0, "modified": ""} for m in nocost_models],
                "source": "config",
                "error": str(e)
            }
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_models)

# Orchestration Endpoints
@app.post("/start")
async def start_project(req: ObjectiveRequest):
    project_id = str(uuid.uuid4())
    
    # Check if we should use existing project
    project = None
    if project_manager.current_project:
        # Use current project if name matches or no name specified
        current_name = project_manager.current_project.name
        if not req.project_name or req.project_name == current_name:
            project = project_manager.current_project
    
    # Create new project only if needed
    if not project:
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
        
        await log_to_gui(project_id, agent_name, f"Working on Task {idx + 1}: {task[:50]}...", status="running")
        agent_mem.think(f"Starting task: {task}")
        
        model = get_model_for_role(agent_name)
        
        # Updated prompt to generate actual code files
        code_instruction = """
IMPORTANT: Generate ACTUAL CODE, not descriptions. Wrap each file in markers:
<<<FILE: path/to/filename.ext>>>
[actual code here]
<<<END_FILE>>>

For Android apps, generate Kotlin (.kt) and XML layout files.
For iOS apps, generate Swift (.swift) files.
For web apps, generate HTML, CSS, and JavaScript files.
For Flutter apps, generate Dart (.dart) files.
"""
        
        system_prompt = f"""You are a {agent_name} who writes PRODUCTION-READY CODE.
{code_instruction}
Project Context:
{project_ctx}
{guidance}"""
        
        result = await call_llm(model, task, system_prompt)
        
        # Extract and write code files from response
        files_written = await extract_and_write_files(result, project.output_dir, project_id, agent_name)
        
        agent_mem.output(f"Generated {files_written} code files")
        await log_to_gui(project_id, agent_name, f"Completed Task {idx + 1} ({files_written} files)", status="complete")
        
        return (idx, result)
    
    async def extract_and_write_files(response: str, output_dir: Path, project_id: str, agent: str) -> int:
        """Extract code files from agent response and write them to disk"""
        import re
        
        files_written = 0
        
        # Method 1: Look for explicit FILE markers
        pattern = r'<<<FILE:\s*([^>]+)>>>(.*?)<<<END_FILE>>>'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for filepath, content in matches:
            filepath = filepath.strip()
            content = content.strip()
            
            full_path = output_dir / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_written += 1
                await log_to_gui(project_id, agent, f"Created: {filepath}", status="file_created")
            except Exception as e:
                await log_to_gui(project_id, agent, f"Error writing {filepath}: {e}", status="error")
        
        # Method 2: Fallback - extract from markdown code blocks if no FILE markers found
        if files_written == 0:
            lang_ext_map = {
                'kotlin': '.kt', 'kt': '.kt',
                'java': '.java',
                'swift': '.swift',
                'dart': '.dart',
                'python': '.py', 'py': '.py',
                'javascript': '.js', 'js': '.js',
                'typescript': '.ts', 'ts': '.ts',
                'xml': '.xml',
                'html': '.html',
                'css': '.css',
                'json': '.json',
                'yaml': '.yaml', 'yml': '.yml',
                'gradle': '.gradle',
            }
            
            # Find all code blocks with language
            code_pattern = r'```(\w+)\n(.*?)```'
            code_matches = re.findall(code_pattern, response, re.DOTALL)
            
            for i, (lang, code) in enumerate(code_matches):
                lang_lower = lang.lower()
                if lang_lower in lang_ext_map:
                    ext = lang_ext_map[lang_lower]
                    # Generate filename from code or use counter
                    if lang_lower in ['kotlin', 'kt', 'java', 'swift']:
                        # Try to extract class/file name from code
                        class_match = re.search(r'class\s+(\w+)', code)
                        if class_match:
                            filename = f"{class_match.group(1)}{ext}"
                        else:
                            filename = f"file_{i+1}{ext}"
                    elif lang_lower == 'xml':
                        if 'layout' in code.lower() or 'LinearLayout' in code or 'ConstraintLayout' in code:
                            filename = f"layout_main_{i+1}.xml"
                        else:
                            filename = f"resource_{i+1}.xml"
                    else:
                        filename = f"file_{i+1}{ext}"
                    
                    full_path = output_dir / "src" / filename
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    try:
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(code.strip())
                        files_written += 1
                        await log_to_gui(project_id, agent, f"Created: src/{filename}", status="file_created")
                    except Exception as e:
                        await log_to_gui(project_id, agent, f"Error writing {filename}: {e}", status="error")
        
        return files_written
    
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

# --- Static File Serving ---
# Find frontend/dist relative to BASE_DIR (works for both dev and prod)
frontend_dist = BASE_DIR / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Serve index.html for any unknown route to support SPA if needed
        # but check if it's an API route first
        if full_path.startswith("api/") or full_path in ["projects", "projects/create", "projects/open", "start", "models/presets", "models/preset"]:
            return None # Fastapi will handle it
        
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
else:
    print(f"Warning: Frontend dist directory not found at {frontend_dist}")

if __name__ == "__main__":
    import uvicorn
    import logging
    import webbrowser
    import socket
    
    # Setup logging to file for easier debugging of the executable
    log_file = get_executable_dir() / "maestro_v2.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("uvicorn")
    logger.info(f"Starting Maestro V2 from {BASE_DIR}")
    logger.info(f"Frontend dist: {frontend_dist}")
    
    # Function to find an available port
    def find_free_port(start_port=8000, max_attempts=10):
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('0.0.0.0', port))
                    return port
                except OSError:
                    continue
        return None

    target_port = find_free_port(8000)
    if not target_port:
        logger.error("Could not find an available port. Please close other applications.")
        if getattr(sys, 'frozen', False):
            input("Press Enter to exit...")
        sys.exit(1)
    
    url = f"http://localhost:{target_port}"
    logger.info(f"Maestro V2 will be available at: {url}")
    
    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(url)
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=target_port, log_level="info")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        if getattr(sys, 'frozen', False):
            input("Press Enter to exit...")
