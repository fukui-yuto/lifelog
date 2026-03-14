$paths = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chrome = $paths | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($chrome) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut("$env:USERPROFILE\Desktop\Chrome (lifelog).lnk")
    $shortcut.TargetPath = $chrome
    $profileDir = "$env:LOCALAPPDATA\lifelog\chrome-profile"
    New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
    $shortcut.Arguments = "--remote-debugging-port=9222 --user-data-dir=`"$profileDir`" --no-first-run"
    $shortcut.Description = "lifelog URL tracking用 Chrome"
    $shortcut.Save()
    Write-Host "OK: $chrome"
} else {
    Write-Host "Chrome not found"
}
