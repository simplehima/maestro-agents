"""
Settings Manager
================
Manages application settings including screenshot permissions.
Persists settings to database and provides API endpoints.
"""

import json
from typing import Optional, Any, Dict
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from database import db


class SettingKey(str, Enum):
    """Available setting keys"""
    SCREENSHOT_PERMISSION = "screenshot_permission"
    SCREENSHOT_AUDIT_LOG = "screenshot_audit_log"
    THEME = "theme"
    MODEL_PRESET = "model_preset"
    OLLAMA_URL = "ollama_url"
    AUTO_SAVE = "auto_save"


@dataclass
class ScreenshotSettings:
    """Screenshot-related settings"""
    permission_level: str = "ask_every_time"  # disabled, ask_every_time, allow_once, always_allow
    audit_enabled: bool = True
    save_screenshots: bool = False
    save_directory: str = ""
    max_stored: int = 10


class SettingsManager:
    """
    Manages application settings with database persistence.
    """
    
    _instance = None
    _settings_cache: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._load_all_settings()
    
    def _load_all_settings(self):
        """Load all settings from database into cache"""
        try:
            for key in SettingKey:
                value = db.get_setting(key.value)
                if value is not None:
                    self._settings_cache[key.value] = value
        except Exception:
            pass
    
    def get(self, key: SettingKey, default: Any = None) -> Any:
        """Get a setting value"""
        return self._settings_cache.get(key.value, default)
    
    def set(self, key: SettingKey, value: Any) -> bool:
        """Set a setting value"""
        try:
            db.save_setting(key.value, value)
            self._settings_cache[key.value] = value
            return True
        except Exception:
            return False
    
    def get_screenshot_settings(self) -> ScreenshotSettings:
        """Get screenshot settings"""
        data = self.get(SettingKey.SCREENSHOT_PERMISSION, {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = {"permission_level": data}
        
        return ScreenshotSettings(
            permission_level=data.get("permission_level", "ask_every_time"),
            audit_enabled=data.get("audit_enabled", True),
            save_screenshots=data.get("save_screenshots", False),
            save_directory=data.get("save_directory", ""),
            max_stored=data.get("max_stored", 10)
        )
    
    def set_screenshot_settings(self, settings: ScreenshotSettings) -> bool:
        """Save screenshot settings"""
        return self.set(SettingKey.SCREENSHOT_PERMISSION, asdict(settings))
    
    def set_screenshot_permission(self, level: str) -> bool:
        """Quick method to set just the permission level"""
        settings = self.get_screenshot_settings()
        settings.permission_level = level
        return self.set_screenshot_settings(settings)
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a dictionary"""
        return {
            "screenshot": asdict(self.get_screenshot_settings()),
            "theme": self.get(SettingKey.THEME, "dark"),
            "model_preset": self.get(SettingKey.MODEL_PRESET, "basic"),
            "ollama_url": self.get(SettingKey.OLLAMA_URL, "http://localhost:11434"),
            "auto_save": self.get(SettingKey.AUTO_SAVE, True)
        }
    
    def update_from_dict(self, settings: Dict[str, Any]) -> bool:
        """Update settings from a dictionary"""
        try:
            if "screenshot" in settings:
                ss = ScreenshotSettings(**settings["screenshot"])
                self.set_screenshot_settings(ss)
            
            if "theme" in settings:
                self.set(SettingKey.THEME, settings["theme"])
            
            if "model_preset" in settings:
                self.set(SettingKey.MODEL_PRESET, settings["model_preset"])
            
            if "ollama_url" in settings:
                self.set(SettingKey.OLLAMA_URL, settings["ollama_url"])
            
            if "auto_save" in settings:
                self.set(SettingKey.AUTO_SAVE, settings["auto_save"])
            
            return True
        except Exception:
            return False


# Global settings manager instance
settings_manager = SettingsManager()


def get_settings() -> SettingsManager:
    """Get the global settings manager"""
    return settings_manager


# Apply screenshot permission from settings on import
def _apply_screenshot_permission():
    """Apply saved screenshot permission to the tool"""
    try:
        from tools.screenshot_tool import set_permission_level, ScreenshotPermission
        
        settings = settings_manager.get_screenshot_settings()
        level_map = {
            "disabled": ScreenshotPermission.DISABLED,
            "ask_every_time": ScreenshotPermission.ASK_EVERY_TIME,
            "allow_once": ScreenshotPermission.ALLOW_ONCE,
            "always_allow": ScreenshotPermission.ALWAYS_ALLOW
        }
        
        perm_level = level_map.get(settings.permission_level, ScreenshotPermission.ASK_EVERY_TIME)
        set_permission_level(perm_level)
    except Exception:
        pass


# Export
__all__ = [
    'SettingsManager',
    'SettingKey',
    'ScreenshotSettings',
    'settings_manager',
    'get_settings'
]
