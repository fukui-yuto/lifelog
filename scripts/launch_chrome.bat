@echo off
set CHROME=
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe

if "%CHROME%"=="" (
  echo Chrome not found
  pause
  exit /b 1
)

set PROFILE=%LocalAppData%\lifelog\chrome-profile
if not exist "%PROFILE%" mkdir "%PROFILE%"

start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%" --no-first-run
