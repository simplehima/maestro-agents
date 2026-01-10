"""
Tool Tests
==========
Unit tests for the tool system.
"""

import pytest
import asyncio
import sys
from pathlib import Path
import tempfile
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import BaseTool, ToolResult, ToolRegistry, tool_registry
from tools.file_tool import FileReadTool, FileWriteTool, FileListTool, register_file_tools
from tools.web_search_tool import WebSearchTool
from tools.code_executor import CodeExecutorTool


class TestToolResult:
    """Test ToolResult dataclass"""
    
    def test_success_result(self):
        result = ToolResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data["key"] == "value"
        assert result.error is None
    
    def test_error_result(self):
        result = ToolResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"
    
    def test_to_dict(self):
        result = ToolResult(success=True, data="test")
        d = result.to_dict()
        assert "success" in d
        assert "data" in d
        assert "error" in d


class TestFileTools:
    """Test file operation tools"""
    
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.mark.asyncio
    async def test_file_write_and_read(self, temp_dir):
        """Should write and read files"""
        write_tool = FileWriteTool([temp_dir])
        read_tool = FileReadTool([temp_dir])
        
        file_path = os.path.join(temp_dir, "test.txt")
        content = "Hello, Maestro!"
        
        # Write
        write_result = await write_tool.execute(file_path=file_path, content=content)
        assert write_result.success is True
        
        # Read
        read_result = await read_tool.execute(file_path=file_path)
        assert read_result.success is True
        assert read_result.data["content"] == content
    
    @pytest.mark.asyncio
    async def test_file_list(self, temp_dir):
        """Should list directory contents"""
        list_tool = FileListTool([temp_dir])
        
        # Create some files
        for i in range(3):
            with open(os.path.join(temp_dir, f"file{i}.txt"), 'w') as f:
                f.write(f"content {i}")
        
        result = await list_tool.execute(directory=temp_dir)
        assert result.success is True
        assert result.data["count"] == 3
    
    @pytest.mark.asyncio
    async def test_path_restriction(self, temp_dir):
        """Should reject paths outside allowed directories"""
        read_tool = FileReadTool([temp_dir])
        
        result = await read_tool.execute(file_path="/etc/passwd")
        assert result.success is False
        assert "not allowed" in result.error.lower()


class TestCodeExecutor:
    """Test code execution tool"""
    
    @pytest.mark.asyncio
    async def test_simple_code_execution(self):
        """Should execute simple Python code"""
        executor = CodeExecutorTool(timeout=10)
        
        result = await executor.execute(code="print('Hello, World!')")
        assert result.success is True
        assert "Hello, World!" in result.data["stdout"]
    
    @pytest.mark.asyncio
    async def test_code_with_error(self):
        """Should handle code errors gracefully"""
        executor = CodeExecutorTool(timeout=10)
        
        result = await executor.execute(code="raise ValueError('test error')")
        # Should capture the error in output
        assert "ValueError" in result.data.get("stdout", "") or "error" in str(result.data).lower()
    
    @pytest.mark.asyncio
    async def test_unsupported_language(self):
        """Should reject unsupported languages"""
        executor = CodeExecutorTool()
        
        result = await executor.execute(code="console.log('test');", language="javascript")
        assert result.success is False
        assert "not supported" in result.error.lower()


class TestToolRegistry:
    """Test tool registry"""
    
    def test_register_and_get_tool(self):
        """Should register and retrieve tools"""
        registry = ToolRegistry()
        registry._tools.clear()
        
        tool = FileReadTool()
        registry.register(tool)
        
        retrieved = registry.get("file_read")
        assert retrieved is not None
        assert retrieved.name == "file_read"
    
    def test_get_all_tools(self):
        """Should return all registered tools"""
        registry = ToolRegistry()
        registry._tools.clear()
        
        registry.register(FileReadTool())
        registry.register(FileWriteTool())
        
        tools = registry.get_all()
        assert len(tools) == 2
    
    def test_get_schemas(self):
        """Should return tool schemas"""
        registry = ToolRegistry()
        registry._tools.clear()
        
        registry.register(FileReadTool())
        
        schemas = registry.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "file_read"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
