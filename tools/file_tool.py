"""
File Operations Tool
====================
Tool for reading and writing files.
"""

import os
from pathlib import Path
from typing import Optional
from . import BaseTool, ToolResult


class FileReadTool(BaseTool):
    """Tool for reading file contents"""
    
    name = "file_read"
    description = "Read the contents of a file"
    
    def __init__(self, allowed_paths: list = None):
        self.allowed_paths = allowed_paths or []
    
    def _is_path_allowed(self, file_path: str) -> bool:
        """Check if the path is within allowed directories"""
        if not self.allowed_paths:
            return True
        
        abs_path = os.path.abspath(file_path)
        for allowed in self.allowed_paths:
            if abs_path.startswith(os.path.abspath(allowed)):
                return True
        return False
    
    async def execute(self, file_path: str, encoding: str = "utf-8") -> ToolResult:
        try:
            if not self._is_path_allowed(file_path):
                return ToolResult(success=False, error="Path not allowed")
            
            if not os.path.exists(file_path):
                return ToolResult(success=False, error=f"File not found: {file_path}")
            
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return ToolResult(success=True, data={
                "path": file_path,
                "content": content,
                "size": len(content)
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def get_schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to read"},
                    "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"}
                },
                "required": ["file_path"]
            }
        }


class FileWriteTool(BaseTool):
    """Tool for writing file contents"""
    
    name = "file_write"
    description = "Write content to a file"
    
    def __init__(self, allowed_paths: list = None):
        self.allowed_paths = allowed_paths or []
    
    def _is_path_allowed(self, file_path: str) -> bool:
        """Check if the path is within allowed directories"""
        if not self.allowed_paths:
            return True
        
        abs_path = os.path.abspath(file_path)
        for allowed in self.allowed_paths:
            if abs_path.startswith(os.path.abspath(allowed)):
                return True
        return False
    
    async def execute(self, file_path: str, content: str, encoding: str = "utf-8", append: bool = False) -> ToolResult:
        try:
            if not self._is_path_allowed(file_path):
                return ToolResult(success=False, error="Path not allowed")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            mode = 'a' if append else 'w'
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
            
            return ToolResult(success=True, data={
                "path": file_path,
                "bytes_written": len(content),
                "mode": "append" if append else "write"
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def get_schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to write to"},
                    "content": {"type": "string", "description": "Content to write"},
                    "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"},
                    "append": {"type": "boolean", "description": "Append instead of overwrite", "default": False}
                },
                "required": ["file_path", "content"]
            }
        }


class FileListTool(BaseTool):
    """Tool for listing directory contents"""
    
    name = "file_list"
    description = "List files and directories in a path"
    
    def __init__(self, allowed_paths: list = None):
        self.allowed_paths = allowed_paths or []
    
    def _is_path_allowed(self, dir_path: str) -> bool:
        if not self.allowed_paths:
            return True
        
        abs_path = os.path.abspath(dir_path)
        for allowed in self.allowed_paths:
            if abs_path.startswith(os.path.abspath(allowed)):
                return True
        return False
    
    async def execute(self, directory: str, pattern: str = "*", recursive: bool = False) -> ToolResult:
        try:
            if not self._is_path_allowed(directory):
                return ToolResult(success=False, error="Path not allowed")
            
            if not os.path.exists(directory):
                return ToolResult(success=False, error=f"Directory not found: {directory}")
            
            path = Path(directory)
            if recursive:
                files = list(path.rglob(pattern))
            else:
                files = list(path.glob(pattern))
            
            result = []
            for f in files[:100]:  # Limit to 100 entries
                result.append({
                    "name": f.name,
                    "path": str(f),
                    "is_dir": f.is_dir(),
                    "size": f.stat().st_size if f.is_file() else None
                })
            
            return ToolResult(success=True, data={
                "directory": directory,
                "count": len(result),
                "files": result
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


def register_file_tools(allowed_paths: list = None):
    """Register all file tools with the tool registry"""
    from . import tool_registry
    
    tool_registry.register(FileReadTool(allowed_paths))
    tool_registry.register(FileWriteTool(allowed_paths))
    tool_registry.register(FileListTool(allowed_paths))
