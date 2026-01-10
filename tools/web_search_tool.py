"""
Web Search Tool
===============
Tool for searching the web using DuckDuckGo.
"""

import asyncio
from typing import List, Dict
import urllib.parse
from . import BaseTool, ToolResult


class WebSearchTool(BaseTool):
    """Tool for searching the web using DuckDuckGo Instant Answer API"""
    
    name = "web_search"
    description = "Search the web for information"
    
    async def execute(self, query: str, num_results: int = 5) -> ToolResult:
        try:
            import httpx
            
            # Use DuckDuckGo Instant Answer API
            encoded_query = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            results = []
            
            # Abstract (main answer)
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", "Answer"),
                    "snippet": data["AbstractText"],
                    "source": data.get("AbstractSource", ""),
                    "url": data.get("AbstractURL", "")
                })
            
            # Related topics
            for topic in data.get("RelatedTopics", [])[:num_results]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text", "")[:50] + "...",
                        "snippet": topic.get("Text", ""),
                        "url": topic.get("FirstURL", "")
                    })
            
            # If no results from DDG, provide a fallback message
            if not results:
                results.append({
                    "title": "No direct results",
                    "snippet": f"Try searching for: {query}",
                    "url": f"https://duckduckgo.com/?q={encoded_query}"
                })
            
            return ToolResult(success=True, data={
                "query": query,
                "num_results": len(results),
                "results": results
            })
            
        except ImportError:
            return ToolResult(
                success=False, 
                error="httpx is required for web search. Install with: pip install httpx"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def get_schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "description": "Number of results", "default": 5}
                },
                "required": ["query"]
            }
        }


def register_web_tools():
    """Register web tools with the tool registry"""
    from . import tool_registry
    tool_registry.register(WebSearchTool())
