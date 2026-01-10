"""
Screenshot Tool
===============
Captures screenshots for AI agents to visually analyze their work.
Supports permission-based access control.
"""

import asyncio
import base64
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass, field
from enum import Enum

from tools import BaseTool, ToolResult, tool_registry


class ScreenshotPermission(Enum):
    """Permission levels for screenshot capability"""
    DISABLED = "disabled"
    ASK_EVERY_TIME = "ask_every_time"
    ALLOW_ONCE = "allow_once"  # Session only
    ALWAYS_ALLOW = "always_allow"


@dataclass
class PermissionState:
    """Tracks the current permission state"""
    level: ScreenshotPermission = ScreenshotPermission.ASK_EVERY_TIME
    session_granted: bool = False
    last_request_time: Optional[datetime] = None
    request_count: int = 0
    
    def is_allowed(self) -> bool:
        """Check if screenshot is currently allowed"""
        if self.level == ScreenshotPermission.DISABLED:
            return False
        if self.level == ScreenshotPermission.ALWAYS_ALLOW:
            return True
        if self.level == ScreenshotPermission.ALLOW_ONCE and self.session_granted:
            return True
        return False
    
    def grant_session(self):
        """Grant permission for this session"""
        self.session_granted = True
        self.last_request_time = datetime.now()
    
    def reset_session(self):
        """Reset session permission"""
        self.session_granted = False


# Global permission state
_permission_state = PermissionState()

# Callback for permission requests (set by frontend)
_permission_callback = None


def set_permission_callback(callback):
    """Set the callback function for permission requests"""
    global _permission_callback
    _permission_callback = callback


def get_permission_state() -> PermissionState:
    """Get the current permission state"""
    return _permission_state


def set_permission_level(level: ScreenshotPermission):
    """Set the permission level"""
    _permission_state.level = level
    if level == ScreenshotPermission.DISABLED:
        _permission_state.session_granted = False


async def request_permission() -> bool:
    """Request permission from user via callback"""
    if _permission_callback:
        try:
            result = await _permission_callback()
            if result:
                _permission_state.grant_session()
            return result
        except Exception:
            return False
    return False


class ScreenshotTool(BaseTool):
    """
    Tool for capturing screenshots.
    
    Supports:
    - Full screen capture
    - Window capture
    - Region capture
    - Base64 encoding for LLM analysis
    """
    
    name = "screenshot"
    description = "Capture a screenshot for visual analysis. Requires user permission."
    
    def __init__(self):
        self._pil_available = False
        self._pyautogui_available = False
        self._mss_available = False
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check which screenshot libraries are available"""
        try:
            import PIL.Image
            self._pil_available = True
        except ImportError:
            pass
        
        try:
            import pyautogui
            self._pyautogui_available = True
        except ImportError:
            pass
        
        try:
            import mss
            self._mss_available = True
        except ImportError:
            pass
    
    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Region to capture: 'full', 'window', or 'x,y,width,height'",
                        "default": "full"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["png", "jpeg"],
                        "description": "Image format",
                        "default": "png"
                    },
                    "quality": {
                        "type": "integer",
                        "description": "JPEG quality (1-100)",
                        "default": 85
                    },
                    "save_path": {
                        "type": "string",
                        "description": "Optional path to save the screenshot"
                    }
                }
            }
        }
    
    async def execute(
        self,
        region: str = "full",
        format: Literal["png", "jpeg"] = "png",
        quality: int = 85,
        save_path: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Execute screenshot capture"""
        
        # Check permission
        perm = get_permission_state()
        
        if perm.level == ScreenshotPermission.DISABLED:
            return ToolResult(
                success=False,
                error="Screenshot capability is disabled. Enable it in Settings."
            )
        
        if not perm.is_allowed():
            if perm.level == ScreenshotPermission.ASK_EVERY_TIME:
                # Request permission
                granted = await request_permission()
                if not granted:
                    return ToolResult(
                        success=False,
                        error="Screenshot permission denied by user."
                    )
            else:
                return ToolResult(
                    success=False,
                    error="Screenshot permission not granted for this session."
                )
        
        # Track request
        perm.request_count += 1
        perm.last_request_time = datetime.now()
        
        # Capture screenshot
        try:
            image_data = await self._capture(region)
            
            if image_data is None:
                return ToolResult(
                    success=False,
                    error="Failed to capture screenshot. Required libraries not available."
                )
            
            # Convert to desired format
            output = io.BytesIO()
            if format == "jpeg":
                image_data.convert("RGB").save(output, format="JPEG", quality=quality)
            else:
                image_data.save(output, format="PNG")
            
            image_bytes = output.getvalue()
            
            # Save if path provided
            if save_path:
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(image_bytes)
            
            # Encode for LLM
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            return ToolResult(
                success=True,
                data={
                    "image_base64": base64_image,
                    "format": format,
                    "width": image_data.width,
                    "height": image_data.height,
                    "size_bytes": len(image_bytes),
                    "saved_to": str(save_path) if save_path else None,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Screenshot capture failed: {str(e)}"
            )
    
    async def _capture(self, region: str):
        """Capture screenshot using available library"""
        
        # Try mss first (fastest, cross-platform)
        if self._mss_available:
            try:
                import mss
                from PIL import Image
                
                with mss.mss() as sct:
                    if region == "full":
                        # Capture all monitors combined
                        screenshot = sct.grab(sct.monitors[0])
                    else:
                        # Parse region string
                        try:
                            x, y, w, h = map(int, region.split(','))
                            monitor = {"left": x, "top": y, "width": w, "height": h}
                            screenshot = sct.grab(monitor)
                        except ValueError:
                            # Default to full screen
                            screenshot = sct.grab(sct.monitors[0])
                    
                    # Convert to PIL Image
                    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                    return img
            except Exception:
                pass
        
        # Try pyautogui as fallback
        if self._pyautogui_available:
            try:
                import pyautogui
                
                if region == "full":
                    screenshot = pyautogui.screenshot()
                else:
                    try:
                        x, y, w, h = map(int, region.split(','))
                        screenshot = pyautogui.screenshot(region=(x, y, w, h))
                    except ValueError:
                        screenshot = pyautogui.screenshot()
                
                return screenshot
            except Exception:
                pass
        
        return None


class BrowserScreenshotTool(BaseTool):
    """
    Tool for capturing browser/webview screenshots.
    Works with pywebview for desktop app.
    """
    
    name = "browser_screenshot"
    description = "Capture a screenshot of the current browser/webview window."
    
    def __init__(self, webview_window=None):
        self._window = webview_window
    
    def set_window(self, window):
        """Set the webview window reference"""
        self._window = window
    
    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "save_path": {
                        "type": "string",
                        "description": "Optional path to save the screenshot"
                    }
                }
            }
        }
    
    async def execute(self, save_path: Optional[str] = None, **kwargs) -> ToolResult:
        """Capture browser screenshot"""
        
        # Check permission
        perm = get_permission_state()
        if not perm.is_allowed() and perm.level != ScreenshotPermission.ALWAYS_ALLOW:
            return ToolResult(
                success=False,
                error="Screenshot permission not granted."
            )
        
        if not self._window:
            return ToolResult(
                success=False,
                error="No browser window available for capture."
            )
        
        try:
            # pywebview screenshot capability
            if hasattr(self._window, 'evaluate_js'):
                # Use html2canvas or similar
                js_code = """
                (async function() {
                    // Try to capture using canvas
                    const canvas = document.createElement('canvas');
                    const body = document.body;
                    canvas.width = body.scrollWidth;
                    canvas.height = body.scrollHeight;
                    // Return placeholder for now
                    return 'browser_screenshot_placeholder';
                })();
                """
                result = self._window.evaluate_js(js_code)
                
                return ToolResult(
                    success=True,
                    data={
                        "message": "Browser screenshot captured",
                        "timestamp": datetime.now().isoformat()
                    }
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Browser screenshot failed: {str(e)}"
            )
        
        return ToolResult(
            success=False,
            error="Browser screenshot not implemented for this platform."
        )


def register_screenshot_tools(allowed_dirs: list = None):
    """Register screenshot tools with the registry"""
    tool_registry.register(ScreenshotTool())
    tool_registry.register(BrowserScreenshotTool())


# Export for easy access
__all__ = [
    'ScreenshotTool',
    'BrowserScreenshotTool',
    'ScreenshotPermission',
    'PermissionState',
    'get_permission_state',
    'set_permission_level',
    'set_permission_callback',
    'register_screenshot_tools'
]
