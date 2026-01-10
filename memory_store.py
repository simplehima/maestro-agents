import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field
import json

@dataclass
class MemoryEntry:
    timestamp: str
    type: str  # thought, decision, output, error, communication
    content: str
    context: Optional[str] = None
    target_agent: Optional[str] = None  # For inter-agent communication

@dataclass
class AgentMemory:
    agent_name: str
    project_path: Path
    entries: List[MemoryEntry] = field(default_factory=list)
    
    def __post_init__(self):
        self.memory_dir = self.project_path / "agents" / self.agent_name.lower().replace(" ", "_").replace("/", "")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_path = self.memory_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self._init_log_file()
    
    def _init_log_file(self):
        with open(self.current_log_path, 'w') as f:
            f.write(f"# {self.agent_name} Session Log\n")
            f.write(f"**Started:** {datetime.now().isoformat()}\n\n")
            f.write("---\n\n")
    
    def log(self, entry_type: str, content: str, context: str = None, target_agent: str = None):
        entry = MemoryEntry(
            timestamp=datetime.now().isoformat(),
            type=entry_type,
            content=content,
            context=context,
            target_agent=target_agent
        )
        self.entries.append(entry)
        self._write_entry(entry)
        return entry
    
    def _write_entry(self, entry: MemoryEntry):
        type_icons = {
            "thought": "💭",
            "decision": "✅",
            "output": "📤",
            "error": "❌",
            "communication": "💬",
            "input": "📥"
        }
        icon = type_icons.get(entry.type, "📝")
        
        with open(self.current_log_path, 'a', encoding='utf-8') as f:
            f.write(f"## {icon} {entry.type.upper()} - {entry.timestamp}\n\n")
            if entry.target_agent:
                f.write(f"**To:** {entry.target_agent}\n\n")
            if entry.context:
                f.write(f"> Context: {entry.context}\n\n")
            f.write(f"{entry.content}\n\n")
            f.write("---\n\n")
    
    def think(self, thought: str, context: str = None):
        return self.log("thought", thought, context)
    
    def decide(self, decision: str, context: str = None):
        return self.log("decision", decision, context)
    
    def output(self, result: str, context: str = None):
        return self.log("output", result, context)
    
    def error(self, error_msg: str, context: str = None):
        return self.log("error", error_msg, context)
    
    def send_message(self, target_agent: str, message: str):
        return self.log("communication", message, target_agent=target_agent)
    
    def receive_message(self, from_agent: str, message: str):
        return self.log("input", f"From {from_agent}: {message}")
    
    def get_recent_entries(self, count: int = 10) -> List[MemoryEntry]:
        return self.entries[-count:]
    
    def get_all_logs(self) -> List[Path]:
        return sorted(self.memory_dir.glob("session_*.md"), reverse=True)
    
    def get_all_logs_content(self, limit: int = 5) -> str:
        """Get actual content from log files"""
        logs = self.get_all_logs()[:limit]
        content = []
        for log in logs:
            try:
                with open(log, 'r', encoding='utf-8') as f:
                    content.append(f.read())
            except Exception:
                pass
        return "\n\n---\n\n".join(content) if content else ""
    
    def read_other_agent_logs(self, other_agent: str, limit: int = 1) -> str:
        """Read logs from another agent for context sharing"""
        other_dir = self.project_path / "agents" / other_agent.lower().replace(" ", "_").replace("/", "")
        if not other_dir.exists():
            return ""
        
        logs = sorted(other_dir.glob("session_*.md"), reverse=True)[:limit]
        content = []
        for log in logs:
            with open(log, 'r', encoding='utf-8') as f:
                content.append(f.read())
        return "\n\n---\n\n".join(content)


class MemoryStore:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.agents: Dict[str, AgentMemory] = {}
        self.message_queue: List[Dict] = []
    
    def get_agent_memory(self, agent_name: str) -> AgentMemory:
        if agent_name not in self.agents:
            self.agents[agent_name] = AgentMemory(agent_name, self.project_path)
        return self.agents[agent_name]
    
    def send_inter_agent_message(self, from_agent: str, to_agent: str, message: str):
        """Queue a message from one agent to another"""
        self.message_queue.append({
            "from": from_agent,
            "to": to_agent,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Log in both agents
        if from_agent in self.agents:
            self.agents[from_agent].send_message(to_agent, message)
    
    def get_messages_for_agent(self, agent_name: str) -> List[Dict]:
        """Get pending messages for an agent"""
        messages = [m for m in self.message_queue if m["to"] == agent_name]
        # Remove delivered messages
        self.message_queue = [m for m in self.message_queue if m["to"] != agent_name]
        
        # Log received messages
        if agent_name in self.agents:
            for m in messages:
                self.agents[agent_name].receive_message(m["from"], m["message"])
        
        return messages
    
    def get_project_context(self) -> str:
        """Get a summary of all agent activities for context"""
        context_parts = []
        for agent_name, memory in self.agents.items():
            recent = memory.get_recent_entries(3)
            if recent:
                agent_ctx = f"### {agent_name}\n"
                for entry in recent:
                    agent_ctx += f"- [{entry.type}] {entry.content[:100]}...\n"
                context_parts.append(agent_ctx)
        return "\n".join(context_parts)
    
    def read_other_agent_logs(self, agent_name: str, limit: int = 5) -> str:
        """Read logs from an agent (wrapper for AgentMemory method)"""
        # Check if agent has been initialized
        if agent_name in self.agents:
            return self.agents[agent_name].get_all_logs_content(limit)
        
        # Otherwise read directly from disk
        agent_dir = self.project_path / "agents" / agent_name.lower().replace(" ", "_").replace("/", "")
        if not agent_dir.exists():
            return ""
        
        logs = sorted(agent_dir.glob("session_*.md"), reverse=True)[:limit]
        content = []
        for log in logs:
            try:
                with open(log, 'r', encoding='utf-8') as f:
                    content.append(f.read())
            except Exception:
                pass
        return "\n\n---\n\n".join(content) if content else ""
