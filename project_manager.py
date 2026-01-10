import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# Fix for PyInstaller persistent storage path
def get_executable_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

import sys
PROJECTS_DIR = get_executable_dir() / "projects"

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
    
    def import_existing_project(self, external_path: str, name: str = None) -> Project:
        """Import an existing external project directory (Flutter, React, Python, etc.)"""
        external_path = Path(external_path)
        if not external_path.exists():
            raise FileNotFoundError(f"Directory not found: {external_path}")
        
        # Use directory name if no name provided
        if not name:
            name = external_path.name
        
        # Analyze project type
        project_type = self._analyze_project_type(external_path)
        
        # Create a Maestro project config in the external directory
        maestro_config_path = external_path / ".maestro"
        maestro_config_path.mkdir(exist_ok=True)
        
        # Create directories for Maestro to use
        (maestro_config_path / "agents").mkdir(exist_ok=True)
        (maestro_config_path / "logs").mkdir(exist_ok=True)
        
        # Create project with external path
        project = Project(name, external_path)
        project.config["is_external"] = True
        project.config["project_type"] = project_type
        project.config["external_path"] = str(external_path)
        project.config["maestro_dir"] = str(maestro_config_path)
        
        # Adjust paths for external project
        project.agents_dir = maestro_config_path / "agents"
        project.logs_dir = maestro_config_path / "logs"
        project.config_path = maestro_config_path / "project.json"
        
        # Analyze existing files for context
        project.config["file_structure"] = self._get_file_structure(external_path)
        
        project.save()
        self.current_project = project
        return project
    
    def _analyze_project_type(self, path: Path) -> dict:
        """Analyze the type of existing project"""
        project_type = {
            "framework": "unknown",
            "language": "unknown",
            "build_system": [],
            "detected_files": []
        }
        
        # Check for common project files
        indicators = {
            # Flutter/Dart
            "pubspec.yaml": ("Flutter", "Dart"),
            "pubspec.lock": ("Flutter", "Dart"),
            # Node.js/JavaScript
            "package.json": ("Node.js", "JavaScript/TypeScript"),
            # Python
            "requirements.txt": ("Python", "Python"),
            "pyproject.toml": ("Python", "Python"),
            "setup.py": ("Python", "Python"),
            # React
            "next.config.js": ("Next.js", "JavaScript/TypeScript"),
            "vite.config.ts": ("Vite", "TypeScript"),
            "vite.config.js": ("Vite", "JavaScript"),
            # Android
            "build.gradle": ("Android", "Kotlin/Java"),
            "settings.gradle": ("Android", "Kotlin/Java"),
            # iOS
            "Podfile": ("iOS", "Swift/Objective-C"),
            # Rust
            "Cargo.toml": ("Rust", "Rust"),
            # Go
            "go.mod": ("Go", "Go"),
            # .NET
            "*.csproj": ("C#/.NET", "C#"),
            "*.sln": ("C#/.NET", "C#"),
            # PHP/Laravel
            "composer.json": ("PHP/Laravel", "PHP"),
            "artisan": ("Laravel", "PHP"),
        }
        
        for indicator, (framework, language) in indicators.items():
            if "*" in indicator:
                # Glob pattern
                if list(path.glob(indicator)):
                    project_type["framework"] = framework
                    project_type["language"] = language
                    project_type["detected_files"].append(indicator)
            elif (path / indicator).exists():
                project_type["framework"] = framework
                project_type["language"] = language
                project_type["detected_files"].append(indicator)
        
        return project_type
    
    def _get_file_structure(self, path: Path, max_depth: int = 3, current_depth: int = 0) -> list:
        """Get simplified file structure for context"""
        if current_depth >= max_depth:
            return []
        
        structure = []
        ignore_dirs = {'.git', '.idea', 'node_modules', '__pycache__', '.dart_tool', 
                       'build', 'dist', '.maestro', 'venv', '.venv', 'target'}
        ignore_extensions = {'.pyc', '.pyo', '.class', '.o', '.obj'}
        
        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith('.') and item.name != '.env.example':
                    continue
                if item.name in ignore_dirs:
                    continue
                if item.suffix in ignore_extensions:
                    continue
                
                if item.is_dir():
                    children = self._get_file_structure(item, max_depth, current_depth + 1)
                    structure.append({"name": item.name, "type": "dir", "children": children})
                else:
                    structure.append({"name": item.name, "type": "file", "size": item.stat().st_size})
        except PermissionError:
            pass
        
        return structure[:50]  # Limit to prevent huge structures
    
    def delete_project(self, path: str):
        project_path = Path(path)
        if project_path.exists():
            shutil.rmtree(project_path)
    
    def get_current_project(self) -> Optional[Project]:
        return self.current_project


# Global instance
project_manager = ProjectManager()
