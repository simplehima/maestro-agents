import os
from dotenv import load_dotenv

load_dotenv()

# Ollama Settings
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3")

# Agent Names
ORCHESTRATOR_NAME = "Maestro-Manager"
WORKER_NAME = "Maestro-Worker"
REFINER_NAME = "Maestro-Refiner"
