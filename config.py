import os
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

class ModelProvider(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    NOCOST = "nocost"  # Free distributed API (no API key required)

@dataclass
class ModelConfig:
    name: str
    provider: ModelProvider
    api_url: str
    api_key: Optional[str] = None
    context_length: int = 8192
    description: str = ""

# Ollama API configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")

# No-Cost Free API configuration (ollamafreeapi)
NOCOST_API_URL = os.getenv("NOCOST_API_URL", "https://api.ollamafreeapi.com")

# Cloud API keys (optional fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Default model (fallback for simpler tasks)
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3:latest")

# Agent role names
ORCHESTRATOR_NAME = "Orchestrator"
WORKER_NAME = "Worker"
REFINER_NAME = "Refiner"

# Model presets for different complexity levels
MODEL_PRESETS = {
    "basic": {
        "orchestrator": "llama3:latest",
        "ui_ux": "llama3:latest",
        "developer": "llama3:latest", 
        "qa": "llama3:latest",
        "refiner": "llama3:latest",
        "research": "llama3:latest",
        "security": "llama3:latest",
        "documentation": "llama3:latest"
    },
    "standard": {
        "orchestrator": "llama3:latest",
        "ui_ux": "llama3:latest",
        "developer": "llama3:latest",
        "qa": "llama3:latest",
        "refiner": "llama3:latest",
        "research": "llama3:latest",
        "security": "llama3:latest",
        "documentation": "llama3:latest"
    },
    "advanced": {
        "orchestrator": "llama3:latest",
        "ui_ux": "llama3:latest",
        "developer": "llama3:latest",
        "qa": "llama3:latest",
        "refiner": "llama3:latest",
        "research": "llama3:latest",
        "security": "llama3:latest",
        "documentation": "llama3:latest"
    },
    "coding": {
        "orchestrator": "llama3:latest",
        "ui_ux": "deepseek-coder:6.7b",
        "developer": "deepseek-coder:6.7b",
        "qa": "llama3:latest",
        "refiner": "llama3:latest",
        "research": "llama3:latest",
        "security": "codellama:7b",
        "documentation": "llama3:latest"
    },
    "cloud": {
        "orchestrator": "gpt-4o",
        "ui_ux": "gpt-4o",
        "developer": "claude-3-5-sonnet-20241022",
        "qa": "gpt-4o-mini",
        "refiner": "gpt-4o",
        "research": "gpt-4o",
        "security": "gpt-4o",
        "documentation": "gpt-4o-mini"
    },
    "free": {
        "orchestrator": "llama3.3:70b",
        "ui_ux": "llama3.3:70b",
        "developer": "deepseek-coder:6.7b",
        "qa": "llama3:8b",
        "refiner": "llama3.3:70b",
        "research": "llama3.3:70b",
        "security": "mistral:7b",
        "documentation": "llama3:8b"
    }
}

# Agent temperature settings (lower = more consistent, higher = more creative)
AGENT_TEMPERATURES = {
    "orchestrator": 0.7,
    "developer": 0.3,
    "ui_ux": 0.6,
    "qa": 0.4,
    "refiner": 0.6,
    "research": 0.5,
    "security": 0.3,
    "documentation": 0.5
}

def get_temperature_for_role(role: str) -> float:
    """Get the temperature setting for a specific agent role"""
    role_key = role.lower().replace(" ", "_").replace("/", "")
    return AGENT_TEMPERATURES.get(role_key, 0.7)

# Current active preset
CURRENT_PRESET = os.getenv("MODEL_PRESET", "basic")

def get_model_for_role(role: str) -> str:
    """Get the configured model for a specific agent role"""
    preset = MODEL_PRESETS.get(CURRENT_PRESET, MODEL_PRESETS["basic"])
    role_key = role.lower().replace(" ", "_").replace("/", "")
    return preset.get(role_key, DEFAULT_MODEL)

def get_available_models() -> Dict[str, list]:
    """Return all available model presets"""
    return MODEL_PRESETS

def set_model_preset(preset_name: str):
    """Set the active model preset"""
    global CURRENT_PRESET
    if preset_name in MODEL_PRESETS:
        CURRENT_PRESET = preset_name
        os.environ["MODEL_PRESET"] = preset_name
        return True
    return False

# Cloud API configurations
CLOUD_CONFIGS = {
    "openai": {
        "base_url": "https://api.openai.com/v1/chat/completions",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1/messages",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"]
    },
    "nocost": {
        "base_url": NOCOST_API_URL,
        "models": [
            "llama3.3:70b", "llama3:8b", "llama3:70b",
            "mistral:7b", "mixtral:8x7b",
            "deepseek-coder:6.7b", "deepseek-r1:7b",
            "codellama:7b", "codellama:13b",
            "phi3:mini", "gemma:7b", "qwen:7b"
        ]
    }
}

def is_cloud_model(model_name: str) -> bool:
    """Check if a model name is a cloud/nocost model (not local Ollama)"""
    for provider, config in CLOUD_CONFIGS.items():
        if model_name in config["models"]:
            return True
    return False

def is_nocost_model(model_name: str) -> bool:
    """Check if a model name is from the free no-cost API"""
    return model_name in CLOUD_CONFIGS.get("nocost", {}).get("models", [])

def get_provider_for_model(model_name: str) -> ModelProvider:
    """Get the provider for a given model name"""
    for provider, config in CLOUD_CONFIGS.items():
        if model_name in config["models"]:
            if provider == "openai":
                return ModelProvider.OPENAI
            elif provider == "anthropic":
                return ModelProvider.ANTHROPIC
            elif provider == "nocost":
                return ModelProvider.NOCOST
    return ModelProvider.OLLAMA
