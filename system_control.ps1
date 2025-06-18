#!/usr/bin/env pwsh
<#
.SYNOPSIS
    AI Agent System Controller for PowerShell
    
.DESCRIPTION
    Provides easy start, stop, restart, and status commands for the AI Agent System
    
.PARAMETER Command
    The command to execute: start, stop, restart, status, diagnostics
    
.PARAMETER Port
    Web interface port (default: 8000)
    
.PARAMETER Force
    Force stop the system (kill process)
    
.EXAMPLE
    .\system_control.ps1 start
    .\system_control.ps1 status
    .\system_control.ps1 restart -Port 8001
    .\system_control.ps1 stop -Force
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status", "diagnostics")]
    [string]$Command,
    
    [Parameter(Position=1)]
    [int]$Port = 8000,
    
    [switch]$Force
)

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Function to write colored output
function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Status "🐍 Python: $pythonVersion" "Green"
} catch {
    Write-Status "❌ Python is not installed or not in PATH" "Red"
    Write-Status "Please install Python and try again" "Yellow"
    exit 1
}

# Check if required files exist
$requiredFiles = @("start_server.py", "web_interface.py")
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Status "❌ $file not found in current directory" "Red"
        exit 1
    }
}

# Show help if no command provided
if (-not $Command) {
    Write-Status "🤖 AI Agent System Controller" "Cyan"
    Write-Status "=============================" "Cyan"
    Write-Status ""
    Write-Status "Usage: .\system_control.ps1 [command] [port] [options]" "White"
    Write-Status ""
    Write-Status "Commands:" "Yellow"
    Write-Status "  start       - Start the AI agent system" "White"
    Write-Status "  stop        - Stop the system gracefully" "White"
    Write-Status "  restart     - Restart the system" "White"
    Write-Status "  status      - Show system status" "White"
    Write-Status "  diagnostics - Run system diagnostics" "White"
    Write-Status ""
    Write-Status "Options:" "Yellow"
    Write-Status "  -Port       - Web interface port (default: 8000)" "White"
    Write-Status "  -Force      - Force stop (kill process)" "White"
    Write-Status ""
    Write-Status "Examples:" "Yellow"
    Write-Status "  .\system_control.ps1 start" "White"
    Write-Status "  .\system_control.ps1 status" "White"
    Write-Status "  .\system_control.ps1 restart -Port 8001" "White"
    Write-Status "  .\system_control.ps1 stop -Force" "White"
    Write-Status ""
    exit 0
}

Write-Status "🚀 AI Agent System Controller" "Cyan"
Write-Status "=============================" "Cyan"
Write-Status "Command: $Command" "White"
Write-Status "Port: $Port" "White"
if ($Force) {
    Write-Status "Force: Yes" "Yellow"
}
Write-Status ""

# Build command arguments
$args = @($Command, "--port", $Port)
if ($Force -and $Command -eq "stop") {
    $args += "--force"
}

# Execute the command
try {
    switch ($Command) {
        "start" {
            Write-Status "🚀 Starting AI Agent System..." "Green"
        }
        "stop" {
            Write-Status "🛑 Stopping AI Agent System..." "Yellow"
        }
        "restart" {
            Write-Status "🔄 Restarting AI Agent System..." "Blue"
        }
        "status" {
            Write-Status "📊 Getting System Status..." "Cyan"
        }
        "diagnostics" {
            Write-Status "🔍 Running System Diagnostics..." "Magenta"
        }
    }
    
    # Execute the Python script
    $result = & python start_server.py @args 2>&1
    
    # Display output with appropriate colors
    foreach ($line in $result) {
        if ($line -match "✅|🟢|Success") {
            Write-Status $line "Green"
        } elseif ($line -match "❌|🔴|Error|Failed") {
            Write-Status $line "Red"
        } elseif ($line -match "⚠️|🟡|Warning") {
            Write-Status $line "Yellow"
        } elseif ($line -match "🚀|🔄|📊|🔍") {
            Write-Status $line "Cyan"
        } else {
            Write-Status $line "White"
        }
    }
    
} catch {
    Write-Status "❌ Error executing command: $($_.Exception.Message)" "Red"
    exit 1
}

Write-Status ""
Write-Status "✅ Command completed" "Green" 