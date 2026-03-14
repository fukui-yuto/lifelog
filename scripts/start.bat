@echo off
title lifelog
cd /d "%~dp0.."

echo [lifelog] Starting tracker...
start "lifelog-tracker" pipenv run python tracker.py

echo [lifelog] Starting API server...
start "lifelog-api" pipenv run uvicorn api:app --port 8000

timeout /t 2 /nobreak > nul
echo [lifelog] Opening browser...
start http://localhost:8000
