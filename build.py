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
    # Ensure pywebview is installed with EdgeChromium support for Windows
    run_command([sys.executable, "-m", "pip", "install", "pywebview[cef]"], check=False)

def build_executable():
    """Build the executable with PyInstaller"""
    print("\n=== Building Desktop Application ===")
    run_command([sys.executable, "-m", "PyInstaller", "build.spec", "--clean"])
    
    print("\n=== Build Complete! ===")
    print(f"Desktop Application created at: {PROJECT_ROOT / 'dist' / 'MaestroV2.exe'}")

def create_release_package():
    """Create a release folder with the EXE and an installer script"""
    print("\n=== Creating Release Package ===")
    import shutil
    import time
    
    release_dir = PROJECT_ROOT / "release"
    if release_dir.exists():
        try:
            shutil.rmtree(release_dir)
            time.sleep(1) # Give OS time to catch up
        except OSError as e:
            print(f"Warning: Could not remove old release directory: {e}")
            print("Trying to clean contents instead...")
            for item in release_dir.iterdir():
                try:
                    if item.is_file(): item.unlink()
                    else: shutil.rmtree(item)
                except: pass
    
    if not release_dir.exists():
        release_dir.mkdir()
    
    exe_src = PROJECT_ROOT / "dist" / "MaestroV2.exe"
    if exe_src.exists():
        try:
            shutil.copy(exe_src, release_dir / "MaestroV2.exe")
        except PermissionError:
            print(f"❌ Error: Could not copy MaestroV2.exe to release folder.")
            print("The EXE is likely running. Please close it and try again.")
            return # Don't proceed with installer creation if copy fails
        
        # Create a simple installer PowerShell script
        installer_content = r"""# Maestro V2 Installer
$InstallDir = "$env:LOCALAPPDATA\MaestroV2"
$ExePath = "$InstallDir\MaestroV2.exe"

Write-Host "Installing Maestro V2 to $InstallDir..." -ForegroundColor Cyan

if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir
}

Copy-Item "MaestroV2.exe" -Destination $ExePath -Force

# Create Desktop Shortcut - more robust Desktop path resolution
$DesktopPath = [Environment]::GetFolderPath("Desktop")
if (!(Test-Path $DesktopPath)) {
    # Fallback for some systems
    $DesktopPath = "$HOME\Desktop"
}

try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$DesktopPath\Maestro V2.lnk")
    $Shortcut.TargetPath = $ExePath
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.Save()
    Write-Host "Installation Complete! A shortcut has been created on your desktop." -ForegroundColor Green
} catch {
    Write-Host "Installation Complete, but could not create desktop shortcut automatically." -ForegroundColor Yellow
    Write-Host "You can find your EXE at: $ExePath"
}

Write-Host "You can now run Maestro V2 from your Desktop or Start Menu."
Pause
"""
        with open(release_dir / "Install.ps1", "w") as f:
            f.write(installer_content)
        
        # Create a basic batch runner for the installer
        with open(release_dir / "RunInstaller.bat", "w") as f:
            f.write("@echo off\npowershell -ExecutionPolicy Bypass -File Install.ps1\n")

    print(f"Release package created in: {release_dir}")

def main():
    os.chdir(PROJECT_ROOT)
    
    print("=" * 50)
    print("Maestro V2 Build Script")
    print("=" * 50)
    
    install_python_deps()
    build_frontend()
    build_executable()
    create_release_package()
    
    print("\n" + "=" * 50)
    print("SUCCESS! Your Maestro V2 Desktop App is ready.")
    print("=" * 50)
    print("\nCheck the 'release' folder for the Desktop EXE and Installer.")
    print("The app will open in a native Windows window (no browser needed).")
    print("\nNOTE: Ollama must be installed and running separately.")
    print("Download Ollama from: https://ollama.ai")

if __name__ == "__main__":
    main()
