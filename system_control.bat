@echo off
REM AI Agent System Control Script for Windows
REM Provides easy start, stop, restart, and status commands

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Check if required files exist
if not exist "start_server.py" (
    echo ❌ start_server.py not found in current directory
    pause
    exit /b 1
)

if not exist "web_interface.py" (
    echo ❌ web_interface.py not found in current directory
    pause
    exit /b 1
)

REM Parse command line arguments
set "COMMAND=%1"
set "PORT=%2"

if "%COMMAND%"=="" (
    echo.
    echo 🤖 AI Agent System Controller
    echo =============================
    echo.
    echo Usage: system_control.bat [command] [port]
    echo.
    echo Commands:
    echo   start       - Start the AI agent system
    echo   stop        - Stop the system gracefully
    echo   restart     - Restart the system
    echo   status      - Show system status
    echo   diagnostics - Run system diagnostics
    echo.
    echo Options:
    echo   port        - Web interface port (default: 8000)
    echo.
    echo Examples:
    echo   system_control.bat start
    echo   system_control.bat status
    echo   system_control.bat restart 8001
    echo.
    pause
    exit /b 0
)

REM Set default port if not specified
if "%PORT%"=="" set "PORT=8000"

echo.
echo 🚀 AI Agent System Controller
echo =============================
echo Command: %COMMAND%
echo Port: %PORT%
echo.

REM Execute the command
if "%COMMAND%"=="start" (
    echo 🚀 Starting AI Agent System...
    python start_server.py start --port %PORT%
) else if "%COMMAND%"=="stop" (
    echo 🛑 Stopping AI Agent System...
    python start_server.py stop --port %PORT%
) else if "%COMMAND%"=="restart" (
    echo 🔄 Restarting AI Agent System...
    python start_server.py restart --port %PORT%
) else if "%COMMAND%"=="status" (
    echo 📊 Getting System Status...
    python start_server.py status --port %PORT%
) else if "%COMMAND%"=="diagnostics" (
    echo 🔍 Running System Diagnostics...
    python start_server.py diagnostics --port %PORT%
) else (
    echo ❌ Unknown command: %COMMAND%
    echo.
    echo Available commands: start, stop, restart, status, diagnostics
    pause
    exit /b 1
)

echo.
echo ✅ Command completed
pause 