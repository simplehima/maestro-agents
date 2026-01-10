"""
Workflow Engine
===============
Advanced DAG-based workflow orchestration for Maestro V2.
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Set
from enum import Enum
import json
from datetime import datetime


class TaskStatus(Enum):
    """Status of a workflow task"""
    PENDING = "pending"
    READY = "ready"  # All dependencies met
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class WorkflowTask:
    """A single task in the workflow"""
    id: str
    name: str
    description: str
    assignee: str  # Agent name
    priority: int = 3  # 1-5, 1 is highest
    depends_on: List[str] = field(default_factory=list)  # Task IDs
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retries: int = 0
    max_retries: int = 2
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "assignee": self.assignee,
            "priority": self.priority,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "result": self.result[:200] if self.result else None,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class Workflow:
    """A workflow containing multiple tasks"""
    id: str
    name: str
    objective: str
    tasks: Dict[str, WorkflowTask] = field(default_factory=dict)
    status: str = "created"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def add_task(self, task: WorkflowTask):
        """Add a task to the workflow"""
        self.tasks[task.id] = task
    
    def get_ready_tasks(self) -> List[WorkflowTask]:
        """Get tasks that are ready to execute (all dependencies completed)"""
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            deps_met = True
            for dep_id in task.depends_on:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    deps_met = False
                    break
            
            if deps_met:
                task.status = TaskStatus.READY
                ready.append(task)
        
        # Sort by priority (lower number = higher priority)
        ready.sort(key=lambda t: t.priority)
        return ready
    
    def is_complete(self) -> bool:
        """Check if all tasks are completed or failed"""
        for task in self.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING]:
                return False
        return True
    
    def get_results(self) -> Dict[str, str]:
        """Get results from all completed tasks"""
        return {
            task_id: task.result
            for task_id, task in self.tasks.items()
            if task.status == TaskStatus.COMPLETED and task.result
        }
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "objective": self.objective,
            "status": self.status,
            "tasks": [t.to_dict() for t in self.tasks.values()],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class WorkflowEngine:
    """
    Advanced workflow execution engine.
    Supports DAG-based execution, parallel tasks, and error handling.
    """
    
    def __init__(self, 
                 agent_executor: Callable = None,
                 max_parallel: int = 4,
                 on_task_update: Callable = None,
                 on_workflow_update: Callable = None):
        self.agent_executor = agent_executor
        self.max_parallel = max_parallel
        self.on_task_update = on_task_update
        self.on_workflow_update = on_workflow_update
        self.active_workflows: Dict[str, Workflow] = {}
        self._cancelled: Set[str] = set()
    
    def create_workflow(self, workflow_id: str, name: str, objective: str) -> Workflow:
        """Create a new workflow"""
        workflow = Workflow(id=workflow_id, name=name, objective=objective)
        self.active_workflows[workflow_id] = workflow
        return workflow
    
    def create_tasks_from_plan(self, workflow: Workflow, task_plan: List[Dict]) -> List[WorkflowTask]:
        """Create tasks from an orchestrator's plan"""
        tasks = []
        for i, task_data in enumerate(task_plan):
            task_id = f"task_{i+1}"
            task = WorkflowTask(
                id=task_id,
                name=task_data.get("task", f"Task {i+1}")[:100],
                description=task_data.get("task", ""),
                assignee=task_data.get("assignee", "Developer"),
                priority=task_data.get("priority", 3),
                depends_on=task_data.get("depends_on", []),
            )
            workflow.add_task(task)
            tasks.append(task)
        return tasks
    
    async def execute_workflow(self, workflow: Workflow) -> Dict:
        """Execute a workflow using DAG-based scheduling"""
        workflow.status = "running"
        
        if self.on_workflow_update:
            await self._safe_callback(self.on_workflow_update, workflow, "started")
        
        while not workflow.is_complete():
            # Check for cancellation
            if workflow.id in self._cancelled:
                workflow.status = "cancelled"
                break
            
            # Get ready tasks
            ready_tasks = workflow.get_ready_tasks()
            
            if not ready_tasks:
                # No ready tasks but workflow not complete - might be stuck
                pending = [t for t in workflow.tasks.values() 
                          if t.status in [TaskStatus.PENDING, TaskStatus.READY]]
                if pending:
                    # Check if we have failed dependencies
                    for task in pending:
                        has_failed_dep = any(
                            workflow.tasks.get(dep_id, WorkflowTask(id="", name="", description="", assignee="")).status == TaskStatus.FAILED
                            for dep_id in task.depends_on
                        )
                        if has_failed_dep:
                            task.status = TaskStatus.SKIPPED
                            task.error = "Dependency failed"
                else:
                    break
                continue
            
            # Execute tasks in parallel (up to max_parallel)
            batch = ready_tasks[:self.max_parallel]
            await asyncio.gather(*[
                self._execute_task(workflow, task)
                for task in batch
            ])
        
        # Finalize workflow
        workflow.completed_at = datetime.now().isoformat()
        
        failed_tasks = [t for t in workflow.tasks.values() if t.status == TaskStatus.FAILED]
        if failed_tasks:
            workflow.status = "completed_with_errors"
        elif workflow.id in self._cancelled:
            workflow.status = "cancelled"
        else:
            workflow.status = "completed"
        
        if self.on_workflow_update:
            await self._safe_callback(self.on_workflow_update, workflow, workflow.status)
        
        return workflow.get_results()
    
    async def _execute_task(self, workflow: Workflow, task: WorkflowTask):
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        
        if self.on_task_update:
            await self._safe_callback(self.on_task_update, workflow, task, "started")
        
        try:
            # Build context from completed dependencies
            context = {}
            for dep_id in task.depends_on:
                dep_task = workflow.tasks.get(dep_id)
                if dep_task and dep_task.result:
                    context[dep_id] = dep_task.result
            
            # Execute via agent
            if self.agent_executor:
                result = await self.agent_executor(
                    agent_name=task.assignee,
                    task=task.description,
                    context=context
                )
                task.result = result
                task.status = TaskStatus.COMPLETED
            else:
                task.result = f"[Mock] Completed: {task.name}"
                task.status = TaskStatus.COMPLETED
                
        except Exception as e:
            task.error = str(e)
            task.retries += 1
            
            if task.retries < task.max_retries:
                task.status = TaskStatus.PENDING
            else:
                task.status = TaskStatus.FAILED
        
        task.completed_at = datetime.now().isoformat()
        
        if self.on_task_update:
            await self._safe_callback(self.on_task_update, workflow, task, task.status.value)
    
    async def _safe_callback(self, callback: Callable, *args, **kwargs):
        """Safely execute a callback"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception:
            pass  # Don't let callback errors affect workflow
    
    def cancel_workflow(self, workflow_id: str):
        """Cancel a running workflow"""
        self._cancelled.add(workflow_id)
    
    def pause_workflow(self, workflow_id: str):
        """Pause a workflow (new tasks won't be started)"""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].status = "paused"
    
    def resume_workflow(self, workflow_id: str):
        """Resume a paused workflow"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            if workflow.status == "paused":
                workflow.status = "running"
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get the status of a workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            return workflow.to_dict()
        return None


# Global workflow engine instance
workflow_engine = WorkflowEngine()
