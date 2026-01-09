#!/usr/bin/env python3
"""
Maestro V2 Build Script
Builds the frontend and creates the executable
"""

import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

def run_command(cmd, cwd=None, check=True):
    """Run a command and handle errors"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, shell=True)
    if check and result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(1)
    return result

def build_frontend():
    """Build the frontend with Vite"""
    print("\n=== Building Frontend ===")
    frontend_dir = PROJECT_ROOT / "frontend"
    
    # Install dependencies
    run_command(["npm", "install"], cwd=frontend_dir)
    
    # Build
    run_command(["npm", "run", "build"], cwd=frontend_dir)
    
    print("Frontend build complete!")

def install_python_deps():
    """Install Python dependencies"""
    print("\n=== Installing Python Dependencies ===")
    run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def build_executable():
    """Build the executable with PyInstaller"""
    print("\n=== Building Executable ===")
    run_command([sys.executable, "-m", "PyInstaller", "build.spec", "--clean"])
    
    print("\n=== Build Complete! ===")
    print(f"Executable created at: {PROJECT_ROOT / 'dist' / 'MaestroV2.exe'}")

def main():
    os.chdir(PROJECT_ROOT)
    
    print("=" * 50)
    print("Maestro V2 Build Script")
    print("=" * 50)
    
    install_python_deps()
    build_frontend()
    build_executable()
    
    print("\n" + "=" * 50)
    print("SUCCESS! Your Maestro V2 executable is ready.")
    print("=" * 50)
    print("\nNOTE: Ollama must be installed and running separately.")
    print("Download Ollama from: https://ollama.ai")
    print("\nTo start Maestro V2, run the executable and open:")
    print("http://localhost:8000 in your browser")

if __name__ == "__main__":
    main()
