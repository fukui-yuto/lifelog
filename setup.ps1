# lifelog setup script
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbs = Join-Path $projectDir "launch.vbs"
$shell = New-Object -ComObject WScript.Shell

# 1. Desktop shortcut
$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "lifelog.lnk"

$shortcut = $shell.CreateShortcut($lnkPath)
$shortcut.TargetPath       = "wscript.exe"
$shortcut.Arguments        = "`"$vbs`""
$shortcut.WorkingDirectory = $projectDir
$shortcut.Description      = "lifelog - PC activity logger"
$shortcut.IconLocation     = "shell32.dll,16"
$shortcut.Save()
Write-Host "OK: desktop shortcut -> $lnkPath"

# 2. Startup folder registration
$startupDir = [Environment]::GetFolderPath("Startup")
$startupLnk = Join-Path $startupDir "lifelog.lnk"

$su = $shell.CreateShortcut($startupLnk)
$su.TargetPath       = "wscript.exe"
$su.Arguments        = "`"$vbs`""
$su.WorkingDirectory = $projectDir
$su.Description      = "lifelog auto-start"
$su.Save()
Write-Host "OK: startup registered -> $startupLnk"

# 3. Remove old VBS if present
$oldVbs = Join-Path $startupDir "lifelog-tracker.vbs"
if (Test-Path $oldVbs) {
    Remove-Item $oldVbs -Force
    Write-Host "OK: removed old script -> $oldVbs"
}

Write-Host ""
Write-Host "Setup complete. Double-click 'lifelog' on Desktop to launch."
