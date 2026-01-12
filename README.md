<p align="center">
  <img src="frontend/public/favicon.ico" alt="Maestro V3 Logo" width="80" height="80">
</p>

<h1 align="center">Maestro V3</h1>

<p align="center">
  <strong>🤖 Enterprise-Grade Multi-Agent AI Orchestration Platform</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#agents">Agents</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/TypeScript-5.0+-blue.svg" alt="TypeScript">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

---

## 🌟 Overview

**Maestro V3** is a sophisticated multi-agent AI orchestration system that coordinates specialized AI agents to accomplish complex tasks. It features a beautiful desktop application with real-time agent collaboration, persistent memory, and extensible tool system.

Built with ❤️ by **HimaAzab**

---

## ✨ Features

### 🧠 8 Specialized AI Agents

| Agent | Role | Capabilities |
|-------|------|--------------|
| **Orchestrator** | Planning & Strategy | Breaks down objectives into actionable tasks |
| **Research** | Information Gathering | Web search, documentation lookup |
| **UI/UX Designer** | Interface Design | Beautiful, responsive UI designs |
| **Developer** | Code Implementation | Clean, efficient code generation |
| **Security** | Vulnerability Analysis | Security review, threat detection |
| **QA Tester** | Quality Assurance | Testing, bug finding, edge cases |
| **Documentation** | Docs Generation | READMEs, API docs, comments |
| **Refiner** | Final Polish | Synthesize and polish outputs |

### 🔧 Tool System

- **File Operations** - Read, write, and list files (sandboxed)
- **Web Search** - DuckDuckGo integration for research
- **Code Executor** - Sandboxed Python code execution

### 🚀 Additional Features

- **Native Desktop App** - Runs as a Windows application (no browser needed!)
- **Real-time Collaboration** - Watch agents work together via WebSocket
- **Persistent Memory** - SQLite database for project history
- **Workflow Engine** - DAG-based task execution with dependencies
- **Multiple Model Presets** - Basic, Standard, Advanced, and Cloud (GPT-4, Claude)

---

## 📥 Installation

### Prerequisites

- **Python 3.9+**
- **Node.js 18+** (for building frontend)
- **Ollama** - [Download here](https://ollama.ai) (for local models)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/simplehima/maestro-agents.git
cd maestro-agents

# Install Python dependencies
pip install -r requirements.txt

# Build the frontend
cd frontend
npm install
npm run build
cd ..

# Run as web application
python app.py

# OR run as desktop application
python desktop_app.py
```

### Build Desktop EXE

```bash
python build.py
```

This creates `MaestroV3.exe` in the `dist/` folder.

---

## 🎮 Usage

### Starting a Project

1. Launch Maestro V3 (desktop app or web)
2. Enter your project objective (e.g., "Build a REST API for a todo app")
3. Select a model preset (Basic, Standard, Advanced, or Cloud)
4. Click **Start Orchestration**
5. Watch the agents collaborate in real-time!

### Live Guidance

You can intervene during orchestration by sending guidance messages to steer the agents.

### Model Presets

| Preset | Models | Best For |
|--------|--------|----------|
| **Basic** | llama3:8b | Quick prototypes |
| **Standard** | llama3:70b + codellama:13b | Balanced quality |
| **Advanced** | llama3:70b + codellama:34b | Production quality |
| **Cloud** | GPT-4o + Claude 3.5 | Maximum capability |

---

## 🏗️ Project Structure

```
maestro-agents/
├── agents/              # Agent architecture
│   ├── __init__.py      # Base classes, registry
│   └── specialized.py   # 8 specialized agents
├── tools/               # Tool system
│   ├── __init__.py      # Base tool classes
│   ├── file_tool.py     # File operations
│   ├── web_search_tool.py
│   └── code_executor.py
├── frontend/            # TypeScript frontend
│   ├── src/
│   └── dist/
├── app.py               # FastAPI backend
├── desktop_app.py       # Desktop launcher
├── workflow_engine.py   # DAG task execution
├── database.py          # SQLite persistence
├── config.py            # Model configuration
└── build.py             # Build script
```

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**HimaAzab**

- GitHub: [@simplehima](https://github.com/simplehima)

---

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai) - Local LLM runtime
- [FastAPI](https://fastapi.tiangolo.com) - Modern Python web framework
- [PyWebView](https://pywebview.flowrl.com) - Native desktop windows
- [Lucide Icons](https://lucide.dev) - Beautiful icons

---

<p align="center">
  Made with ✨ by <a href="https://github.com/simplehima">HimaAzab</a>
</p>
