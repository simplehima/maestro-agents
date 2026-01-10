"""
Agent Tests
===========
Unit tests for the agent architecture.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import (
    BaseAgent, AgentConfig, AgentCapability, AgentStatus,
    AgentMessage, AgentRegistry, agent_registry
)
from agents.specialized import (
    OrchestratorAgent, DeveloperAgent, UIUXAgent, QAAgent,
    ResearchAgent, SecurityAgent, DocumentationAgent, RefinerAgent,
    create_all_agents
)


class TestAgentCapability:
    """Test agent capability scoring"""
    
    def test_developer_handles_code_tasks(self):
        """Developer should score high on code-related tasks"""
        agent = DeveloperAgent()
        score = agent.can_handle("implement a REST API endpoint")
        assert score > 0.0, "Developer should handle implementation tasks"
    
    def test_uiux_handles_design_tasks(self):
        """UI/UX agent should score high on design tasks"""
        agent = UIUXAgent()
        score = agent.can_handle("design a beautiful login page with CSS")
        assert score > 0.0, "UI/UX should handle design tasks"
    
    def test_qa_handles_test_tasks(self):
        """QA agent should score high on testing tasks"""
        agent = QAAgent()
        score = agent.can_handle("test the user registration flow")
        assert score > 0.0, "QA should handle testing tasks"
    
    def test_security_handles_security_tasks(self):
        """Security agent should score high on security tasks"""
        agent = SecurityAgent()
        score = agent.can_handle("check for SQL injection vulnerabilities")
        assert score > 0.0, "Security should handle security tasks"
    
    def test_research_handles_research_tasks(self):
        """Research agent should score high on research tasks"""
        agent = ResearchAgent()
        score = agent.can_handle("research best practices for API design")
        assert score > 0.0, "Research should handle research tasks"


class TestAgentRegistry:
    """Test the agent registry"""
    
    def test_register_and_get_agent(self):
        """Should register and retrieve agents"""
        registry = AgentRegistry()
        registry._agents.clear()  # Clear for test isolation
        
        agent = DeveloperAgent()
        registry.register(agent)
        
        retrieved = registry.get("Developer")
        assert retrieved is not None
        assert retrieved.name == "Developer"
    
    def test_find_best_agent(self):
        """Should find the best agent for a task"""
        registry = AgentRegistry()
        registry._agents.clear()
        
        # Register multiple agents
        registry.register(DeveloperAgent())
        registry.register(UIUXAgent())
        registry.register(QAAgent())
        
        # Developer should be best for code tasks
        best = registry.find_best_agent("implement a function")
        assert best is not None
        assert best.name == "Developer"


class TestAgentMessage:
    """Test inter-agent messaging"""
    
    def test_create_message(self):
        """Should create messages correctly"""
        agent = DeveloperAgent()
        message = agent.create_message("QA Tester", "Please review this code", "request")
        
        assert message.from_agent == "Developer"
        assert message.to_agent == "QA Tester"
        assert message.content == "Please review this code"
        assert message.message_type == "request"
    
    def test_receive_message(self):
        """Should receive and store messages"""
        dev = DeveloperAgent()
        qa = QAAgent()
        
        message = dev.create_message("QA Tester", "Code ready for review")
        qa.receive_message(message)
        
        pending = qa.get_pending_messages()
        assert len(pending) == 1
        assert pending[0].content == "Code ready for review"


class TestAgentStatus:
    """Test agent status tracking"""
    
    def test_initial_status_idle(self):
        """Agents should start in idle status"""
        agent = DeveloperAgent()
        assert agent.status == AgentStatus.IDLE
    
    def test_get_status_dict(self):
        """Should return status as dictionary"""
        agent = DeveloperAgent()
        status = agent.get_status_dict()
        
        assert "name" in status
        assert "role" in status
        assert "status" in status
        assert status["name"] == "Developer"


class TestCreateAllAgents:
    """Test the agent factory function"""
    
    def test_creates_all_agents(self):
        """Should create all 8 specialized agents"""
        agents = create_all_agents()
        
        expected_agents = [
            "Orchestrator", "Developer", "UI/UX Designer", "QA Tester",
            "Research", "Security", "Documentation", "Refiner"
        ]
        
        for name in expected_agents:
            assert name in agents, f"Missing agent: {name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
