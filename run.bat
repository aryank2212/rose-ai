@echo off
title ROSE — Responsive On-device Synthetic Engine

REM ─── Check if Ollama is running ─────────────────────────────────────
echo Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo Starting Ollama...
    where ollama >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Ollama not found on PATH. Install from https://ollama.com
        echo Or set OLLAMA_EXE environment variable to the ollama executable path.
        pause
        exit /b 1
    )
    start /B "" ollama serve
    timeout /t 5 /nobreak >nul
)

REM ─── Activate venv if present ───────────────────────────────────────
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM ─── Launch ROSE ────────────────────────────────────────────────────
python -m rose.main
pause
