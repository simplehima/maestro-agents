# Maestro V2 Installer
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
