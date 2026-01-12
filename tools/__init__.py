"""
Maestro V3 - Tool System
========================
Extensible tool system for agent capabilities.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class ToolResult:
    """Result from a tool execution"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }


class BaseTool(ABC):
    """Base class for all tools"""
    
    name: str = "base_tool"
    description: str = "Base tool"
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def get_schema(self) -> Dict:
        """Return the tool's parameter schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {}
        }


class ToolRegistry:
    """Registry for managing tools"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, BaseTool] = {}
        return cls._instance
    
    def register(self, tool: BaseTool):
        """Register a tool"""
        self._tools[tool.name] = tool
        
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def get_all(self) -> List[BaseTool]:
        """Get all registered tools"""
        return list(self._tools.values())
    
    def get_schemas(self) -> List[Dict]:
        """Get schemas for all tools"""
        return [tool.get_schema() for tool in self._tools.values()]


# Global tool registry
tool_registry = ToolRegistry()
