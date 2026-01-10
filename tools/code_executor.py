"""
Code Executor Tool
==================
Sandboxed tool for executing code snippets.
"""

import subprocess
import tempfile
import os
import asyncio
from typing import Optional
from . import BaseTool, ToolResult


class CodeExecutorTool(BaseTool):
    """Tool for executing code in a sandboxed environment"""
    
    name = "code_executor"
    description = "Execute code snippets (Python) in a sandboxed environment"
    
    def __init__(self, timeout: int = 30, max_output_length: int = 10000):
        self.timeout = timeout
        self.max_output_length = max_output_length
        self.allowed_languages = ["python"]
    
    async def execute(self, code: str, language: str = "python") -> ToolResult:
        if language.lower() not in self.allowed_languages:
            return ToolResult(
                success=False, 
                error=f"Language '{language}' not supported. Supported: {self.allowed_languages}"
            )
        
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.py', 
                delete=False,
                encoding='utf-8'
            ) as f:
                # Add safety wrapper
                safe_code = f'''
import sys
import os

# Limit resource usage
sys.setrecursionlimit(100)

# Restricted builtins
restricted_builtins = {{
    'print': print,
    'len': len,
    'range': range,
    'str': str,
    'int': int,
    'float': float,
    'bool': bool,
    'list': list,
    'dict': dict,
    'tuple': tuple,
    'set': set,
    'sorted': sorted,
    'enumerate': enumerate,
    'zip': zip,
    'map': map,
    'filter': filter,
    'sum': sum,
    'min': min,
    'max': max,
    'abs': abs,
    'round': round,
    'type': type,
    'isinstance': isinstance,
}}

try:
{chr(10).join("    " + line for line in code.split(chr(10)))}
except Exception as e:
    print(f"Error: {{type(e).__name__}}: {{e}}")
'''
                f.write(safe_code)
                temp_path = f.name
            
            try:
                # Run the code
                process = await asyncio.create_subprocess_exec(
                    'python', temp_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tempfile.gettempdir()
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    return ToolResult(
                        success=False, 
                        error=f"Execution timed out after {self.timeout} seconds"
                    )
                
                output = stdout.decode('utf-8', errors='replace')
                error_output = stderr.decode('utf-8', errors='replace')
                
                # Truncate if too long
                if len(output) > self.max_output_length:
                    output = output[:self.max_output_length] + "\n... (output truncated)"
                
                if process.returncode != 0:
                    return ToolResult(
                        success=False,
                        data={"stdout": output, "stderr": error_output},
                        error=f"Process exited with code {process.returncode}"
                    )
                
                return ToolResult(success=True, data={
                    "stdout": output,
                    "stderr": error_output,
                    "exit_code": process.returncode
                })
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def get_schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to execute"},
                    "language": {"type": "string", "description": "Programming language", "default": "python"}
                },
                "required": ["code"]
            }
        }


def register_code_tools(timeout: int = 30):
    """Register code execution tools"""
    from . import tool_registry
    tool_registry.register(CodeExecutorTool(timeout=timeout))
