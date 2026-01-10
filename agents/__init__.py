"""
Maestro V2 - Advanced Agent Architecture
=========================================
Modular agent system with specialized agents for different tasks.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
import json


class AgentCapability(Enum):
    """Capabilities that agents can have"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DESIGN = "design"
    TESTING = "testing"
    RESEARCH = "research"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    OPTIMIZATION = "optimization"
    WEB_SEARCH = "web_search"
    FILE_OPERATIONS = "file_operations"


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    name: str
    role: str
    description: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: List[str] = field(default_factory=list)


@dataclass
class AgentMessage:
    """Message passed between agents"""
    from_agent: str
    to_agent: str
    content: str
    message_type: str = "info"  # info, request, response, error
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base class for all Maestro agents.
    Provides common functionality and interface.
    """
    
    def __init__(self, config: AgentConfig, llm_caller: Callable = None):
        self.config = config
        self.name = config.name
        self.role = config.role
        self.capabilities = config.capabilities
        self.status = AgentStatus.IDLE
        self.llm_caller = llm_caller
        self.tools: Dict[str, Any] = {}
        self.message_inbox: List[AgentMessage] = []
        self.execution_history: List[Dict] = []
        
    @abstractmethod
    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        """Execute a task and return the result"""
        pass
    
    def can_handle(self, task: str) -> float:
        """
        Returns a confidence score (0-1) for how well this agent can handle the task.
        Used for intelligent task routing.
        """
        task_lower = task.lower()
        score = 0.0
        
        # Check capabilities against task keywords
        capability_keywords = {
            AgentCapability.CODE_GENERATION: ["implement", "create", "build", "code", "develop", "function", "class"],
            AgentCapability.CODE_REVIEW: ["review", "check", "analyze", "inspect", "evaluate"],
            AgentCapability.DESIGN: ["design", "ui", "ux", "layout", "interface", "style", "css", "visual"],
            AgentCapability.TESTING: ["test", "verify", "validate", "qa", "bug", "fix", "debug"],
            AgentCapability.RESEARCH: ["research", "find", "search", "look up", "investigate", "explore"],
            AgentCapability.SECURITY: ["security", "vulnerability", "secure", "protect", "authentication", "authorization"],
            AgentCapability.DOCUMENTATION: ["document", "readme", "docs", "explain", "comment", "describe"],
            AgentCapability.OPTIMIZATION: ["optimize", "performance", "speed", "efficiency", "improve", "refactor"],
        }
        
        for capability in self.capabilities:
            if capability in capability_keywords:
                for keyword in capability_keywords[capability]:
                    if keyword in task_lower:
                        score += 0.2
        
        return min(score, 1.0)
    
    def register_tool(self, name: str, tool: Any):
        """Register a tool for this agent to use"""
        self.tools[name] = tool
        
    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        """Use a registered tool"""
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found"}
        
        tool = self.tools[tool_name]
        try:
            if hasattr(tool, 'execute'):
                return await tool.execute(**kwargs)
            elif callable(tool):
                return tool(**kwargs)
            return {"error": f"Tool '{tool_name}' is not callable"}
        except Exception as e:
            return {"error": str(e)}
    
    def receive_message(self, message: AgentMessage):
        """Receive a message from another agent"""
        self.message_inbox.append(message)
        
    def get_pending_messages(self) -> List[AgentMessage]:
        """Get and clear pending messages"""
        messages = self.message_inbox.copy()
        self.message_inbox.clear()
        return messages
    
    def create_message(self, to_agent: str, content: str, message_type: str = "info") -> AgentMessage:
        """Create a message to send to another agent"""
        return AgentMessage(
            from_agent=self.name,
            to_agent=to_agent,
            content=content,
            message_type=message_type
        )
    
    async def think(self, prompt: str, context: str = "") -> str:
        """Use LLM for reasoning"""
        if not self.llm_caller:
            return "Error: No LLM caller configured"
        
        self.status = AgentStatus.THINKING
        full_system_prompt = f"{self.config.system_prompt}\n\n{context}" if context else self.config.system_prompt
        
        try:
            result = await self.llm_caller(
                model=None,  # Will use role-based model selection
                prompt=prompt,
                system_prompt=full_system_prompt
            )
            return result
        finally:
            self.status = AgentStatus.IDLE
    
    def get_status_dict(self) -> Dict[str, Any]:
        """Get agent status as a dictionary"""
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "capabilities": [c.value for c in self.capabilities],
            "pending_messages": len(self.message_inbox),
            "tools": list(self.tools.keys())
        }


class AgentRegistry:
    """Registry for managing and discovering agents"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents: Dict[str, BaseAgent] = {}
        return cls._instance
    
    def register(self, agent: BaseAgent):
        """Register an agent"""
        self._agents[agent.name] = agent
        
    def get(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name"""
        return self._agents.get(name)
    
    def get_all(self) -> List[BaseAgent]:
        """Get all registered agents"""
        return list(self._agents.values())
    
    def find_best_agent(self, task: str) -> Optional[BaseAgent]:
        """Find the best agent for a task based on capabilities"""
        best_agent = None
        best_score = 0.0
        
        for agent in self._agents.values():
            score = agent.can_handle(task)
            if score > best_score:
                best_score = score
                best_agent = agent
                
        return best_agent
    
    def broadcast_message(self, message: AgentMessage):
        """Broadcast a message to all agents except the sender"""
        for name, agent in self._agents.items():
            if name != message.from_agent:
                agent.receive_message(message)
    
    def send_message(self, message: AgentMessage):
        """Send a message to a specific agent"""
        if message.to_agent in self._agents:
            self._agents[message.to_agent].receive_message(message)


# Global registry instance
agent_registry = AgentRegistry()
