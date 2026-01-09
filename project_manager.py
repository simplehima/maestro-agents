import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

PROJECTS_DIR = Path(__file__).parent / "projects"

class Project:
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.config_path = path / "project.json"
        self.agents_dir = path / "agents"
        self.logs_dir = path / "logs"
        self.output_dir = path / "output"
        
        self.config: Dict = {}
        self._load_config()
    
    def _load_config(self):
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "name": self.name,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "objective": "",
                "status": "new",
                "tasks": [],
                "current_task_index": 0,
                "agents": {
                    "orchestrator": {"model": "llama3:70b", "status": "idle"},
                    "ui_ux": {"model": "deepseek-coder:33b", "status": "idle"},
                    "developer": {"model": "codellama:34b", "status": "idle"},
                    "qa": {"model": "llama3:8b", "status": "idle"}
                }
            }
    
    def save(self):
        self.config["updated_at"] = datetime.now().isoformat()
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def set_objective(self, objective: str):
        self.config["objective"] = objective
        self.config["status"] = "planning"
        self.save()
    
    def add_tasks(self, tasks: List[str]):
        self.config["tasks"] = tasks
        self.config["status"] = "in_progress"
        self.save()
    
    def complete_task(self, index: int):
        if index < len(self.config["tasks"]):
            self.config["current_task_index"] = index + 1
            if self.config["current_task_index"] >= len(self.config["tasks"]):
                self.config["status"] = "completed"
            self.save()
    
    def get_agent_log_path(self, agent_name: str) -> Path:
        agent_dir = self.agents_dir / agent_name.lower().replace(" ", "_").replace("/", "")
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"


class ProjectManager:
    def __init__(self):
        PROJECTS_DIR.mkdir(exist_ok=True)
        self.current_project: Optional[Project] = None
    
    def list_projects(self) -> List[Dict]:
        projects = []
        for item in PROJECTS_DIR.iterdir():
            if item.is_dir() and (item / "project.json").exists():
                with open(item / "project.json", 'r') as f:
                    config = json.load(f)
                    projects.append({
                        "name": config.get("name", item.name),
                        "path": str(item),
                        "status": config.get("status", "unknown"),
                        "updated_at": config.get("updated_at", "unknown"),
                        "objective": config.get("objective", "")[:100]
                    })
        return sorted(projects, key=lambda x: x.get("updated_at", ""), reverse=True)
    
    def create_project(self, name: str) -> Project:
        # Sanitize name for filesystem
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_path = PROJECTS_DIR / f"{safe_name}_{timestamp}"
        
        # Create directory structure
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "agents").mkdir(exist_ok=True)
        (project_path / "logs").mkdir(exist_ok=True)
        (project_path / "output").mkdir(exist_ok=True)
        
        project = Project(name, project_path)
        project.save()
        
        self.current_project = project
        return project
    
    def open_project(self, path: str) -> Project:
        project_path = Path(path)
        if not project_path.exists():
            raise FileNotFoundError(f"Project not found: {path}")
        
        with open(project_path / "project.json", 'r') as f:
            config = json.load(f)
        
        project = Project(config.get("name", project_path.name), project_path)
        self.current_project = project
        return project
    
    def delete_project(self, path: str):
        project_path = Path(path)
        if project_path.exists():
            shutil.rmtree(project_path)
    
    def get_current_project(self) -> Optional[Project]:
        return self.current_project


# Global instance
project_manager = ProjectManager()
