"""
Maestro V2 - Desktop Application Launcher
==========================================
Creates a native Windows desktop window for Maestro V2.
Uses pywebview to embed the web UI in a native window.
"""

import sys
import os
import threading
import time
import socket
import webview
import uvicorn
from pathlib import Path


def get_base_path():
    """Get the base path for bundled or dev environment"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def get_executable_dir():
    """Get the directory where the executable is located"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def find_free_port(start_port=8000, max_attempts=10):
    """Find an available port"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except OSError:
                continue
    return None


def wait_for_server(host, port, timeout=30):
    """Wait for the server to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.1)
    return False


class MaestroDesktopApp:
    """Desktop application manager for Maestro V2"""
    
    def __init__(self):
        self.port = None
        self.server_thread = None
        self.window = None
        
    def start_server(self):
        """Start the FastAPI server in a background thread"""
        # Import the app here to avoid circular imports
        BASE_DIR = get_base_path()
        sys.path.insert(0, str(BASE_DIR))
        
        from app import app
        
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
            access_log=False
        )
        server = uvicorn.Server(config)
        server.run()
    
    def run(self):
        """Run the desktop application"""
        # Find available port
        self.port = find_free_port(8000)
        if not self.port:
            print("Error: Could not find an available port")
            sys.exit(1)
        
        # Start server in background thread
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to be ready
        print(f"Starting Maestro V2 on port {self.port}...")
        if not wait_for_server('127.0.0.1', self.port, timeout=30):
            print("Error: Server did not start in time")
            sys.exit(1)
        
        url = f"http://127.0.0.1:{self.port}"
        
        # Create API class for JavaScript to call
        js_api = JsApi()
        
        # Create and show the native window
        self.window = webview.create_window(
            title="Maestro V2 - AI Agent Platform",
            url=url,
            width=1400,
            height=900,
            min_size=(1000, 700),
            resizable=True,
            confirm_close=True,
            text_select=True,
            js_api=js_api,  # Expose Python API to JavaScript
        )
        
        # Start the webview (this blocks until window is closed)
        webview.start(
            debug=False,
            http_server=False,
        )
        
        print("Maestro V2 closed.")


class JsApi:
    """Python API exposed to JavaScript via pywebview"""
    
    def select_folder(self):
        """Open native folder selection dialog and return selected path"""
        try:
            result = webview.windows[0].create_file_dialog(
                webview.FOLDER_DIALOG
            )
            if result and len(result) > 0:
                return result[0]
            return None
        except Exception as e:
            print(f"Error selecting folder: {e}")
            return None


def main():
    """Entry point for the desktop application"""
    # Set up logging
    import logging
    log_file = get_executable_dir() / "maestro_v2.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("maestro")
    logger.info("Starting Maestro V2 Desktop Application")
    
    try:
        app = MaestroDesktopApp()
        app.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if getattr(sys, 'frozen', False):
            input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
