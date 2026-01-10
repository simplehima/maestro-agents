"""
Specialized Agents for Maestro V2
=================================
Concrete implementations of specialized agents.
"""

from typing import Dict, Any, List
from . import BaseAgent, AgentConfig, AgentCapability, AgentStatus


class OrchestratorAgent(BaseAgent):
    """
    The Orchestrator Agent - Plans and coordinates work across other agents.
    """
    
    def __init__(self, llm_caller=None):
        config = AgentConfig(
            name="Orchestrator",
            role="orchestrator",
            description="Plans and coordinates work, breaks down objectives into tasks",
            capabilities=[AgentCapability.RESEARCH],
            system_prompt="""You are the Orchestrator Agent for Maestro V2.
Your role is to:
1. Analyze project objectives and break them into actionable tasks
2. Assign tasks to the most suitable agents based on their capabilities
3. Coordinate workflow between agents
4. Ensure project coherence and quality

When breaking down objectives, output ONLY a JSON array:
[{"task": "description", "assignee": "UI/UX|Developer|QA|Research|Security", "priority": 1-5, "depends_on": []}]

Consider task dependencies and parallel execution opportunities.
""",
            temperature=0.7
        )
        super().__init__(config, llm_caller)
    
    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        self.status = AgentStatus.EXECUTING
        try:
            result = await self.think(task, context.get("additional_context", "") if context else "")
            self.execution_history.append({"task": task, "result": result[:500]})
            return result
        finally:
            self.status = AgentStatus.COMPLETED
    
    async def break_down_objective(self, objective: str) -> List[Dict]:
        """Break down an objective into tasks"""
        prompt = f"Break down this objective into specific, actionable tasks:\n\n{objective}"
        response = await self.execute(prompt)
        
        # Parse JSON response
        try:
            import json
            clean = response.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0]
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0]
            return json.loads(clean)
        except:
            # Fallback parsing
            return [{"task": line.strip(), "assignee": "Developer", "priority": 3} 
                    for line in response.split('\n') if line.strip()]


class DeveloperAgent(BaseAgent):
    """
    The Developer Agent - Implements code and technical solutions.
    """
    
    def __init__(self, llm_caller=None):
        config = AgentConfig(
            name="Developer",
            role="developer",
            description="Implements robust and efficient code with clean architecture",
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_REVIEW,
                AgentCapability.OPTIMIZATION
            ],
            system_prompt="""You are a Senior Developer Agent for Maestro V2.
Your role is to:
1. Write clean, efficient, and well-documented code
2. Follow best practices and design patterns
3. Consider performance, security, and maintainability
4. Provide complete, working implementations

When writing code:
- Include proper error handling
- Add meaningful comments
- Follow language conventions
- Consider edge cases
""",
            temperature=0.3  # Lower temperature for more consistent code
        )
        super().__init__(config, llm_caller)
    
    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        self.status = AgentStatus.EXECUTING
        
        # Check for relevant messages from other agents
        messages = self.get_pending_messages()
        msg_context = "\n".join([f"[{m.from_agent}]: {m.content}" for m in messages])
        
        full_context = ""
        if context:
            full_context = context.get("additional_context", "")
        if msg_context:
            full_context += f"\n\nMessages from team:\n{msg_context}"
        
        try:
            result = await self.think(task, full_context)
            self.execution_history.append({"task": task, "result": result[:500]})
            return result
        finally:
            self.status = AgentStatus.COMPLETED


class UIUXAgent(BaseAgent):
    """
    The UI/UX Designer Agent - Creates beautiful and intuitive interfaces.
    """
    
    def __init__(self, llm_caller=None):
        config = AgentConfig(
            name="UI/UX Designer",
            role="ui_ux",
            description="Designs beautiful, intuitive interfaces with great UX",
            capabilities=[AgentCapability.DESIGN],
            system_prompt="""You are a UI/UX Designer Agent for Maestro V2.
Your role is to:
1. Design beautiful, modern, and intuitive interfaces
2. Create responsive layouts that work on all devices
3. Focus on user experience and accessibility
4. Provide CSS, HTML, and design specifications

Design principles:
- Use modern aesthetics (gradients, subtle shadows, smooth animations)
- Ensure accessibility (proper contrast, keyboard navigation)
- Mobile-first responsive design
- Consistent design system with reusable components
""",
            temperature=0.6
        )
        super().__init__(config, llm_caller)
    
    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        self.status = AgentStatus.EXECUTING
        try:
            result = await self.think(task, context.get("additional_context", "") if context else "")
            self.execution_history.append({"task": task, "result": result[:500]})
            return result
        finally:
            self.status = AgentStatus.COMPLETED


class QAAgent(BaseAgent):
    """
    The QA Tester Agent - Ensures quality and finds bugs.
    """
    
    def __init__(self, llm_caller=None):
        config = AgentConfig(
            name="QA Tester",
            role="qa",
            description="Verifies functionality, finds bugs, ensures quality",
            capabilities=[AgentCapability.TESTING, AgentCapability.CODE_REVIEW],
            system_prompt="""You are a QA Tester Agent for Maestro V2.
Your role is to:
1. Review code for bugs and issues
2. Create comprehensive test cases
3. Identify edge cases and potential failures
4. Suggest improvements and fixes

When testing:
- Consider all edge cases
- Check for security vulnerabilities
- Verify error handling
- Test boundary conditions
- Ensure proper validation
""",
            temperature=0.4
        )
        super().__init__(config, llm_caller)
    
    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        self.status = AgentStatus.EXECUTING
        try:
            result = await self.think(task, context.get("additional_context", "") if context else "")
            self.execution_history.append({"task": task, "result": result[:500]})
            return result
        finally:
            self.status = AgentStatus.COMPLETED


class ResearchAgent(BaseAgent):
    """
    The Research Agent - Searches for information and documentation.
    """
    
    def __init__(self, llm_caller=None):
        config = AgentConfig(
            name="Research",
            role="research",
            description="Researches information, best practices, and documentation",
            capabilities=[AgentCapability.RESEARCH, AgentCapability.WEB_SEARCH],
            system_prompt="""You are a Research Agent for Maestro V2.
Your role is to:
1. Research best practices and patterns
2. Find relevant documentation and examples
3. Analyze existing solutions
4. Provide comprehensive research reports

When researching:
- Cite sources when available
- Compare multiple approaches
- Highlight pros and cons
- Provide actionable recommendations
""",
            temperature=0.5,
            tools=["web_search"]
        )
        super().__init__(config, llm_caller)
    
    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        self.status = AgentStatus.EXECUTING
        
        # Try to use web search tool if available
        search_results = ""
        if "web_search" in self.tools:
            search_results = await self.use_tool("web_search", query=task)
            if isinstance(search_results, dict) and "results" in search_results:
                search_results = f"\n\nWeb Search Results:\n{search_results['results']}"
        
        full_context = context.get("additional_context", "") if context else ""
        full_context += search_results
        
        try:
            result = await self.think(task, full_context)
            self.execution_history.append({"task": task, "result": result[:500]})
            return result
        finally:
            self.status = AgentStatus.COMPLETED


class SecurityAgent(BaseAgent):
    """
    The Security Agent - Analyzes code for security vulnerabilities.
    """
    
    def __init__(self, llm_caller=None):
        config = AgentConfig(
            name="Security",
            role="security",
            description="Analyzes code for security vulnerabilities and best practices",
            capabilities=[AgentCapability.SECURITY, AgentCapability.CODE_REVIEW],
            system_prompt="""You are a Security Agent for Maestro V2.
Your role is to:
1. Identify security vulnerabilities in code
2. Check for common security issues (injection, XSS, CSRF, etc.)
3. Review authentication and authorization logic
4. Suggest security improvements and fixes

Security checklist:
- Input validation and sanitization
- Proper authentication/authorization
- Secure data storage
- Protection against common attacks
- Secure configuration
- Dependency vulnerabilities
""",
            temperature=0.3
        )
        super().__init__(config, llm_caller)
    
    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        self.status = AgentStatus.EXECUTING
        try:
            result = await self.think(task, context.get("additional_context", "") if context else "")
            self.execution_history.append({"task": task, "result": result[:500]})
            return result
        finally:
            self.status = AgentStatus.COMPLETED


class DocumentationAgent(BaseAgent):
    """
    The Documentation Agent - Generates documentation and explanations.
    """
    
    def __init__(self, llm_caller=None):
        config = AgentConfig(
            name="Documentation",
            role="documentation",
            description="Generates documentation, READMEs, and API docs",
            capabilities=[AgentCapability.DOCUMENTATION],
            system_prompt="""You are a Documentation Agent for Maestro V2.
Your role is to:
1. Write clear, comprehensive documentation
2. Create README files and API documentation
3. Generate code comments and docstrings
4. Create user guides and tutorials

Documentation principles:
- Clear and concise language
- Proper formatting with headers and lists
- Include code examples
- Cover both basic and advanced usage
- Keep documentation up-to-date
""",
            temperature=0.5
        )
        super().__init__(config, llm_caller)
    
    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        self.status = AgentStatus.EXECUTING
        try:
            result = await self.think(task, context.get("additional_context", "") if context else "")
            self.execution_history.append({"task": task, "result": result[:500]})
            return result
        finally:
            self.status = AgentStatus.COMPLETED


class RefinerAgent(BaseAgent):
    """
    The Refiner Agent - Synthesizes and polishes final outputs.
    """
    
    def __init__(self, llm_caller=None):
        config = AgentConfig(
            name="Refiner",
            role="refiner",
            description="Synthesizes outputs from all agents into polished deliverables",
            capabilities=[],
            system_prompt="""You are the Refiner Agent for Maestro V2.
Your role is to:
1. Synthesize outputs from all other agents
2. Ensure consistency and coherence
3. Polish and finalize deliverables
4. Create comprehensive project outputs

When refining:
- Maintain consistent style and formatting
- Resolve any conflicts between agent outputs
- Add missing connections or transitions
- Ensure completeness of the final deliverable
""",
            temperature=0.6
        )
        super().__init__(config, llm_caller)
    
    async def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        self.status = AgentStatus.EXECUTING
        try:
            result = await self.think(task, context.get("additional_context", "") if context else "")
            self.execution_history.append({"task": task, "result": result[:500]})
            return result
        finally:
            self.status = AgentStatus.COMPLETED
    
    async def refine_results(self, objective: str, results: List[str]) -> str:
        """Refine and synthesize results from multiple agents"""
        context = "\n\n".join([f"--- Result {i+1} ---\n{r}" for i, r in enumerate(results)])
        prompt = f"""Synthesize these agent outputs into a polished final deliverable.

Original Objective: {objective}

Agent Outputs:
{context}

Create a comprehensive, well-organized final output."""
        
        return await self.execute(prompt)


# Factory function to create all agents
def create_all_agents(llm_caller=None) -> Dict[str, BaseAgent]:
    """Create and return all specialized agents"""
    from . import agent_registry
    
    agents = {
        "Orchestrator": OrchestratorAgent(llm_caller),
        "Developer": DeveloperAgent(llm_caller),
        "UI/UX Designer": UIUXAgent(llm_caller),
        "QA Tester": QAAgent(llm_caller),
        "Research": ResearchAgent(llm_caller),
        "Security": SecurityAgent(llm_caller),
        "Documentation": DocumentationAgent(llm_caller),
        "Refiner": RefinerAgent(llm_caller),
    }
    
    # Register all agents
    for agent in agents.values():
        agent_registry.register(agent)
    
    return agents
