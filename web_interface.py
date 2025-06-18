"""
Web Interface - The control panel for the multi-agent system.
This provides a REST API and web interface for monitoring and controlling the system.
Think of it as the mission control dashboard.
"""

import asyncio
import json
import time
import sys
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import re
import functools
import logging
import traceback

from system_orchestrator import orchestrator
from utils.message_bus import message_bus
from config import config

# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Monitoring System",
    description="GPT-driven system monitoring and self-healing",
    version="1.0.0",
)

# Global state
system_running: bool = False
startup_task = None
startup_time: Optional[float] = None
system_ready: bool = False
startup_error: Optional[str] = None

# Performance monitoring
performance_cache = {}
cache_ttl = 30  # seconds
last_health_check = None
health_check_interval = 60  # seconds

# Startup validation results
startup_validation = {
    "database": False,
    "message_bus": False,
    "agents": False,
    "llm_provider": False,
    "file_permissions": False,
    "system_resources": False,
}


async def validate_startup_requirements():
    """Validate all startup requirements and log results."""
    global startup_validation

    print("🔍 Starting system validation...")

    # 1. Check file permissions
    try:
        import os

        log_dir = os.path.dirname(config.logging.log_file)
        os.makedirs(log_dir, exist_ok=True)
        with open(config.logging.log_file, "a") as f:
            f.write("")
        startup_validation["file_permissions"] = True
        print("✅ File permissions validated")
    except Exception as e:
        print(f"❌ File permissions failed: {e}")

    # 2. Check system resources
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\" if sys.platform == "win32" else "/")
        if (
            memory.available > 500 * 1024 * 1024 and disk.free > 1 * 1024 * 1024 * 1024
        ):  # 500MB RAM, 1GB disk
            startup_validation["system_resources"] = True
            print("✅ System resources sufficient")
        else:
            print("⚠️ System resources low")
    except Exception as e:
        print(f"❌ System resource check failed: {e}")

    # 3. Check database
    try:
        from utils.persistence import PersistenceManager

        persistence = PersistenceManager()
        await persistence.initialize()
        startup_validation["database"] = True
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

    # 4. Check message bus
    try:
        await message_bus.start()
        startup_validation["message_bus"] = True
        print("✅ Message bus started")
    except Exception as e:
        print(f"❌ Message bus failed: {e}")

    # 5. Check LLM provider
    try:
        from utils.ollama_client import ollama_client

        if await ollama_client.health_check():
            startup_validation["llm_provider"] = True
            print("✅ LLM provider (Ollama) available")
        else:
            print("⚠️ LLM provider not available - will use fallback")
    except Exception as e:
        print(f"⚠️ LLM provider check failed: {e}")

    # 6. Validate agents can be created
    try:
        from agents import (
            SensorAgent,
            AnalyzerAgent,
            RemediatorAgent,
            CommunicatorAgent,
        )

        test_agents = {
            "sensor": SensorAgent(),
            "analyzer": AnalyzerAgent(),
            "remediator": RemediatorAgent(),
            "communicator": CommunicatorAgent(),
        }
        startup_validation["agents"] = True
        print("✅ Agent classes validated")
    except Exception as e:
        print(f"❌ Agent validation failed: {e}")

    # Summary
    all_valid = all(startup_validation.values())
    print(f"\n📊 Startup Validation Summary:")
    for check, status in startup_validation.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {check}: {'PASS' if status else 'FAIL'}")

    if all_valid:
        print("🎉 All startup requirements validated successfully!")
    else:
        print(
            "⚠️ Some startup requirements failed - system may have limited functionality"
        )

    return all_valid


async def monitor_system_performance():
    """Monitor system performance and cache results."""
    global performance_cache, last_health_check

    while system_running:
        try:
            current_time = time.time()

            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            performance_cache["system_metrics"] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "disk_percent": disk.percent,
                "disk_free": disk.free,
                "timestamp": current_time,
            }

            # Agent health check (cached)
            if (
                not last_health_check
                or (current_time - last_health_check) > health_check_interval
            ):
                try:
                    agent_health = {}
                    for name, agent in orchestrator.agents.items():
                        if hasattr(agent, "health_status"):
                            agent_health[name] = {
                                "status": agent.health_status,
                                "running": getattr(agent, "running", False),
                                "uptime": getattr(agent, "uptime", 0),
                            }

                    performance_cache["agent_health"] = agent_health
                    performance_cache["agent_health_timestamp"] = current_time
                    last_health_check = current_time
                except Exception as e:
                    print(f"Warning: Agent health check failed: {e}")

            await asyncio.sleep(10)  # Update every 10 seconds

        except Exception as e:
            print(f"Performance monitoring error: {e}")
            await asyncio.sleep(30)


def get_cached_data(key: str, max_age: Optional[int] = None):
    """Get cached data if it's still valid."""
    if key not in performance_cache:
        return None

    data = performance_cache[key]
    if max_age is None:
        max_age = 60

    if time.time() - data.get("timestamp", 0) > max_age:
        return None

    return data


async def background_init():
    global system_ready, startup_error, system_running, startup_task, startup_time
    try:
        validation_passed = await validate_startup_requirements()
        if validation_passed:
            try:
                # Start performance monitoring
                asyncio.create_task(monitor_system_performance())
                # Start the orchestrator
                startup_task = asyncio.create_task(start_system())
                system_running = True
                system_ready = True
                elapsed = (time.time() - startup_time) if startup_time is not None else 0
                print(f"✅ System started successfully in {elapsed:.2f} seconds")
            except Exception as e:
                print(f"❌ System startup failed: {e}")
                startup_error = str(e)
                system_ready = False
        else:
            print("⚠️ System started with limited functionality due to validation failures")
            startup_error = "Startup validation failed"
            system_ready = False
    except Exception as e:
        startup_error = str(e)
        system_ready = False


@app.on_event("startup")
async def startup_event():
    global startup_time
    startup_time = time.time()
    print("🚀 Starting Multi-Agent System...")
    # Launch background initialization (do not await)
    asyncio.create_task(background_init())


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the multi-agent system when the web interface shuts down."""
    global system_running

    if system_running:
        print("🛑 Shutting down system...")
        await orchestrator.stop()
        system_running = False
        print("✅ System shutdown complete")


async def start_system():
    """Start the multi-agent system in the background."""
    global system_running

    try:
        await orchestrator.start()
        print("🎉 Multi-agent system is running!")
    except Exception as e:
        print(f"❌ Failed to start system: {e}")
        system_running = False


# Performance monitoring endpoints
@app.get("/api/performance")
async def get_performance_metrics():
    """Get current system performance metrics."""
    try:
        cached_metrics = get_cached_data("system_metrics")
        if cached_metrics:
            return cached_metrics

        # Fallback to real-time metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available": memory.available,
            "disk_percent": disk.percent,
            "disk_free": disk.free,
            "timestamp": time.time(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/startup/status")
async def get_startup_status():
    """Get startup validation status."""
    global startup_validation, system_ready, startup_time

    return {
        "system_ready": system_ready,
        "startup_time": startup_time,
        "uptime": time.time() - startup_time if startup_time else 0,
        "validation": startup_validation,
        "all_valid": all(startup_validation.values()),
    }


@app.get("/api/startup/diagnostics")
async def get_startup_diagnostics():
    """Get detailed startup diagnostics."""
    try:
        diagnostics = {
            "system_info": {
                "platform": sys.platform,
                "python_version": sys.version,
                "cpu_count": psutil.cpu_count() or 1,
                "memory_total": psutil.virtual_memory().total,
            },
            "file_system": {},
            "network": {},
            "processes": {},
        }

        # Check file system
        try:
            import os

            log_dir = os.path.dirname(config.logging.log_file)
            diagnostics["file_system"]["log_directory"] = {
                "exists": os.path.exists(log_dir),
                "writable": (
                    os.access(log_dir, os.W_OK) if os.path.exists(log_dir) else False
                ),
                "path": log_dir,
            }
        except Exception as e:
            diagnostics["file_system"]["error"] = str(e)

        # Check network
        try:
            import socket

            diagnostics["network"]["localhost"] = {
                "reachable": True,
                "port_8002": False,
            }
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("localhost", 8002))
            diagnostics["network"]["localhost"]["port_8002"] = result == 0
            sock.close()
        except Exception as e:
            diagnostics["network"]["error"] = str(e)

        # Check processes
        try:
            diagnostics["processes"]["current"] = {
                "pid": os.getpid(),
                "memory_usage": psutil.Process().memory_info().rss,
                "cpu_percent": psutil.Process().cpu_percent(),
            }
        except Exception as e:
            diagnostics["processes"]["error"] = str(e)

        return diagnostics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# API Routes


@app.get("/", response_class=HTMLResponse)
async def root():
    """Main dashboard page with cutting-edge design, advanced features, and comprehensive data widgets."""
    return """
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>AI Agent System Dashboard</title>
        <link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap' rel='stylesheet'>
        <link href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css' rel='stylesheet'>
        <script src='https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js'></script>
        <style>
            :root {
                --primary: #4f8cff;
                --secondary: #232946;
                --background: #f4f6fb;
                --glass: rgba(255,255,255,0.7);
                --border: rgba(76,110,245,0.12);
                --shadow: 0 8px 32px 0 rgba(31,38,135,0.18);
                --radius: 18px;
                --sidebar-width: 260px;
                --success: #10b981;
                --warning: #f59e0b;
                --danger: #ef4444;
                --info: #3b82f6;
            }
            html, body {
                height: 100%;
                margin: 0;
                padding: 0;
                font-family: 'Inter', Arial, sans-serif;
                background: var(--background);
                color: var(--secondary);
            }
            body {
                min-height: 100vh;
                display: flex;
                flex-direction: row;
            }
            nav {
                width: var(--sidebar-width);
                min-width: var(--sidebar-width);
                background: var(--glass);
                backdrop-filter: blur(16px) saturate(180%);
                box-shadow: var(--shadow);
                border-right: 1px solid var(--border);
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 2rem 1rem 1rem 1rem;
                position: sticky;
                top: 0;
                height: 100vh;
                z-index: 10;
                transition: left 0.3s;
            }
            nav .logo {
                font-size: 2rem;
                font-weight: 800;
                color: var(--primary);
                margin-bottom: 2rem;
                letter-spacing: 2px;
            }
            nav ul {
                list-style: none;
                padding: 0;
                margin: 0;
                width: 100%;
            }
            nav ul li {
                margin: 1.2rem 0;
            }
            nav ul li a {
                text-decoration: none;
                color: var(--secondary);
                font-weight: 600;
                font-size: 1.1rem;
                padding: 0.7rem 1.2rem;
                border-radius: var(--radius);
                display: flex;
                align-items: center;
                transition: background 0.2s, color 0.2s;
            }
            nav ul li a.active, nav ul li a:hover {
                background: var(--primary);
                color: #fff;
            }
            .hamburger {
                display: none;
                position: absolute;
                top: 1.5rem;
                left: 1.5rem;
                background: none;
                border: none;
                font-size: 2rem;
                color: var(--primary);
                cursor: pointer;
                z-index: 20;
            }
            main {
                flex: 1;
                padding: 2.5rem 2rem 2rem 2rem;
                display: flex;
                flex-direction: column;
                gap: 2rem;
                min-width: 0;
                overflow-y: auto;
            }
            .dashboard-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 1.5rem;
                flex-wrap: wrap;
                gap: 1rem;
            }
            .dashboard-header h1 {
                font-size: 2.2rem;
                font-weight: 800;
                margin: 0;
                color: var(--primary);
            }
            .dashboard-header .actions {
                display: flex;
                gap: 1rem;
                flex-wrap: wrap;
            }
            .glass-card {
                background: var(--glass);
                border-radius: var(--radius);
                box-shadow: var(--shadow);
                border: 1px solid var(--border);
                padding: 2rem 1.5rem;
                margin-bottom: 1.5rem;
                backdrop-filter: blur(12px) saturate(180%);
                transition: box-shadow 0.2s;
            }
            .glass-card:hover {
                box-shadow: 0 12px 40px 0 rgba(31,38,135,0.22);
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 2rem;
                margin-bottom: 2rem;
            }
            .dashboard-grid.full-width {
                grid-template-columns: 1fr;
            }
            .quick-actions {
                display: flex;
                gap: 1rem;
                flex-wrap: wrap;
                margin-bottom: 1rem;
            }
            .btn {
                background: var(--primary);
                color: #fff;
                border: none;
                padding: 0.7rem 1.2rem;
                border-radius: var(--radius);
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 0.9rem;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(79, 140, 255, 0.3);
            }
            .btn.success { background: var(--success); }
            .btn.warning { background: var(--warning); }
            .btn.danger { background: var(--danger); }
            .btn.info { background: var(--info); }
            .toast-container {
                position: fixed;
                top: 2rem;
                right: 2rem;
                z-index: 1000;
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            .toast {
                background: var(--glass);
                backdrop-filter: blur(16px);
                border: 1px solid var(--border);
                border-radius: var(--radius);
                padding: 1rem 1.5rem;
                box-shadow: var(--shadow);
                min-width: 300px;
                transform: translateX(100%);
                transition: transform 0.3s ease;
            }
            .toast.show {
                transform: translateX(0);
            }
            .toast.success { border-left: 4px solid var(--success); }
            .toast.warning { border-left: 4px solid var(--warning); }
            .toast.danger { border-left: 4px solid var(--danger); }
            .toast.info { border-left: 4px solid var(--info); }
            .toast-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
            }
            .toast-title {
                font-weight: 600;
                font-size: 1rem;
            }
            .toast-close {
                background: none;
                border: none;
                color: var(--secondary);
                cursor: pointer;
                font-size: 1.2rem;
            }
            .toast-message {
                font-size: 0.9rem;
                opacity: 0.9;
            }
            .loader {
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 2rem;
                color: var(--secondary);
                opacity: 0.7;
            }
            .loader::after {
                content: '';
                width: 20px;
                height: 20px;
                border: 2px solid var(--border);
                border-top: 2px solid var(--primary);
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-left: 0.5rem;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .metric-card {
                background: var(--glass);
                border-radius: var(--radius);
                padding: 1.5rem;
                text-align: center;
                border: 1px solid var(--border);
            }
            .metric-value {
                font-size: 2rem;
                font-weight: 800;
                color: var(--primary);
                margin-bottom: 0.5rem;
            }
            .metric-label {
                font-size: 0.9rem;
                opacity: 0.8;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 0.5rem;
            }
            .status-healthy { background: var(--success); }
            .status-warning { background: var(--warning); }
            .status-critical { background: var(--danger); }
            .status-unknown { background: #9ca3af; }
            @media (max-width: 900px) {
                nav {
                    position: fixed;
                    left: -100vw;
                    top: 0;
                    height: 100vh;
                    z-index: 100;
                    transition: left 0.3s;
                }
                nav.open {
                    left: 0;
                }
                .hamburger {
                    display: block;
                }
                main {
                    padding: 1.2rem;
                }
                .dashboard-grid {
                    grid-template-columns: 1fr;
                }
                .toast-container {
                    top: 1rem;
                    right: 1rem;
                    left: 1rem;
                }
                .toast {
                    min-width: auto;
                }
                /* Configuration management responsive */
                .glass-card > div:first-child {
                    flex-direction: column;
                    gap: 1rem;
                    align-items: stretch;
                }
                .glass-card > div:first-child > div:last-child {
                    flex-wrap: wrap;
                }
                .glass-card > div:first-child > div:last-child .btn {
                    flex: 1;
                    min-width: 120px;
                }
                /* Logs viewer responsive */
                #logs-container {
                    max-height: 300px;
                    font-size: 0.8rem;
                }
                /* Configuration form responsive */
                .glass-card > div:nth-child(2) {
                    grid-template-columns: 1fr;
                    gap: 1.5rem;
                }
                /* Input fields responsive */
                input[type="number"], input[type="url"], input[type="text"], select {
                    font-size: 16px; /* Prevents zoom on iOS */
                }
            }
            /* Focus styles for accessibility */
            a:focus, button:focus {
                outline: 2px solid var(--primary);
                outline-offset: 2px;
            }
            html {
                scroll-behavior: smooth;
            }
            /* --- Accessibility: Skip to Content --- */
            .skip-link {
                position: absolute;
                left: -999px;
                top: 10px;
                background: var(--primary);
                color: #fff;
                padding: 0.5rem 1rem;
                border-radius: 8px;
                z-index: 10000;
                font-weight: 600;
                transition: left 0.2s;
            }
            .skip-link:focus {
                left: 1rem;
            }
        </style>
    </head>
    <body>
        <a href="#dashboard" class="skip-link" tabindex="0">Skip to main content</a>
        <button class="hamburger" aria-label="Open navigation" aria-controls="main-nav" aria-expanded="false" tabindex="0">
            <i class="fas fa-bars"></i>
        </button>
        <nav id="main-nav" aria-label="Main navigation">
            <div class="logo">AI Agents</div>
            <ul>
                <li><a href="#dashboard" class="active" tabindex="0"><i class="fas fa-tachometer-alt"></i>&nbsp;Dashboard</a></li>
                <li><a href="#agents" tabindex="0"><i class="fas fa-robot"></i>&nbsp;Agents</a></li>
                <li><a href="#alerts" tabindex="0"><i class="fas fa-bell"></i>&nbsp;Alerts</a></li>
                <li><a href="#logs" tabindex="0"><i class="fas fa-file-alt"></i>&nbsp;Logs</a></li>
                <li><a href="#settings" tabindex="0"><i class="fas fa-cog"></i>&nbsp;Settings</a></li>
            </ul>
        </nav>
        <main id="dashboard" tabindex="-1">
            <div class="dashboard-header">
                <h1>System Dashboard</h1>
                <div class="actions">
                    <button id="darkModeToggle" class="btn" aria-label="Toggle dark mode">Dark Mode</button>
                    <button id="refreshBtn" class="btn info" aria-label="Refresh dashboard"><i class="fas fa-sync-alt"></i> Refresh</button>
                </div>
            </div>
            <!-- Accessibility: Banner for critical alerts -->
            <div id="critical-banner" style="display:none;background:var(--danger);color:#fff;padding:1rem 2rem;border-radius:12px;margin-bottom:1.5rem;font-weight:600;" role="alert" aria-live="assertive"></div>
            
            <!-- Quick Actions -->
            <section class="glass-card" aria-label="Quick Actions">
                <h2 style="margin-top:0;">Quick Actions</h2>
                <div class="quick-actions">
                    <button class="btn success" onclick="sendCommand('restart', 'all')" aria-label="Restart all agents">
                        <i class="fas fa-redo"></i> Restart All
                    </button>
                    <button class="btn warning" onclick="sendCommand('health_check', 'all')" aria-label="Health check all agents">
                        <i class="fas fa-heartbeat"></i> Health Check
                    </button>
                    <button class="btn info" onclick="sendCommand('status', 'all')" aria-label="Get status of all agents">
                        <i class="fas fa-info-circle"></i> Get Status
                    </button>
                    <button class="btn" onclick="showToast('info', 'System Info', 'System information refreshed')" aria-label="Refresh system info">
                        <i class="fas fa-cog"></i> System Info
                    </button>
                </div>
            </section>

            <!-- System Metrics Overview -->
            <div class="dashboard-grid">
                <section id="agents" class="glass-card" aria-label="System Overview">
                    <h2 style="margin-top:0;">System Overview</h2>
                    <div id="system-overview" aria-live="polite">
                        <div class="loader" id="system-overview-loader">Loading system overview...</div>
                    </div>
                </section>
                
                <section class="glass-card" aria-label="System Health">
                    <h2 style="margin-top:0;">System Health</h2>
                    <div id="system-health" aria-live="polite">
                        <div class="loader" id="system-health-loader">Loading health metrics...</div>
                    </div>
                </section>
            </div>

            <!-- Agent Status with Chart -->
            <section class="glass-card" aria-label="Agent Status">
                <h2 style="margin-top:0;">Agent Status</h2>
                <div id="agent-status" aria-live="polite">
                    <div class="loader" id="agent-status-loader">Loading agent status...</div>
                </div>
                <div id="agent-status-chart" style="width:100%;height:300px;margin-top:1rem;"></div>
            </section>

            <!-- Live Alerts and Activity Feed -->
            <div class="dashboard-grid">
                <section id="alerts" class="glass-card" aria-label="Live Alerts">
                    <h2 style="margin-top:0;">Live Alerts</h2>
                    <div id="live-alerts" aria-live="polite">
                        <div class="loader" id="live-alerts-loader">Loading alerts...</div>
                    </div>
                </section>
                
                <section class="glass-card" aria-label="Activity Feed">
                    <h2 style="margin-top:0;">Activity Feed</h2>
                    <div id="activity-feed" aria-live="polite">
                        <div class="loader" id="activity-feed-loader">Loading activity...</div>
                    </div>
                </section>
            </div>

            <!-- System Metrics Charts -->
            <section class="glass-card" aria-label="System Metrics">
                <h2 style="margin-top:0;">System Metrics</h2>
                <div id="system-metrics-chart" style="width:100%;height:400px;"></div>
            </section>

            <!-- Logs Viewer -->
            <section id="logs" class="glass-card" aria-label="System Logs">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
                    <h2 style="margin:0;">System Logs</h2>
                    <div style="display:flex;gap:0.5rem;align-items:center;">
                        <select id="log-level-filter" style="padding:0.3rem;border-radius:8px;border:1px solid var(--border);background:var(--glass);">
                            <option value="all">All Levels</option>
                            <option value="INFO">Info</option>
                            <option value="WARNING">Warning</option>
                            <option value="ERROR">Error</option>
                            <option value="CRITICAL">Critical</option>
                        </select>
                        <button class="btn" onclick="refreshLogs()" aria-label="Refresh logs">
                            <i class="fas fa-sync-alt"></i>
                        </button>
                        <button class="btn" onclick="clearLogs()" aria-label="Clear logs">
                            <i class="fas fa-trash"></i>
                        </button>
                        <label style="display:flex;align-items:center;gap:0.5rem;font-size:0.9rem;">
                            <input type="checkbox" id="auto-scroll-logs" checked>
                            Auto-scroll
                        </label>
                    </div>
                </div>
                <div id="logs-container" style="background:rgba(0,0,0,0.05);border-radius:12px;padding:1rem;max-height:400px;overflow-y:auto;font-family:'Courier New',monospace;font-size:0.85rem;line-height:1.4;">
                    <div id="logs-content" aria-live="polite">
                        <div class="loader">Loading logs...</div>
                    </div>
                </div>
            </section>

            <!-- Configuration Management -->
            <section id="settings" class="glass-card" aria-label="Configuration Management">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
                    <h2 style="margin:0;">Configuration</h2>
                    <div style="display:flex;gap:0.5rem;">
                        <button class="btn success" onclick="saveConfig()" aria-label="Save configuration">
                            <i class="fas fa-save"></i> Save
                        </button>
                        <button class="btn warning" onclick="resetConfig()" aria-label="Reset configuration">
                            <i class="fas fa-undo"></i> Reset
                        </button>
                        <button class="btn info" onclick="exportConfig()" aria-label="Export configuration">
                            <i class="fas fa-download"></i> Export
                        </button>
                    </div>
                </div>
                
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:2rem;">
                    <!-- System Thresholds -->
                    <div>
                        <h3 style="margin-top:0;color:var(--primary);">System Thresholds</h3>
                        <div style="display:flex;flex-direction:column;gap:1rem;">
                            <div>
                                <label for="cpu-warning">CPU Warning (%)</label>
                                <input type="number" id="cpu-warning" min="0" max="100" step="1" style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid var(--border);background:var(--glass);">
                            </div>
                            <div>
                                <label for="cpu-critical">CPU Critical (%)</label>
                                <input type="number" id="cpu-critical" min="0" max="100" step="1" style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid var(--border);background:var(--glass);">
                            </div>
                            <div>
                                <label for="memory-warning">Memory Warning (%)</label>
                                <input type="number" id="memory-warning" min="0" max="100" step="1" style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid var(--border);background:var(--glass);">
                            </div>
                            <div>
                                <label for="memory-critical">Memory Critical (%)</label>
                                <input type="number" id="memory-critical" min="0" max="100" step="1" style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid var(--glass);">
                            </div>
                            <div>
                                <label for="disk-warning">Disk Warning (%)</label>
                                <input type="number" id="disk-warning" min="0" max="100" step="1" style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid var(--border);background:var(--glass);">
                            </div>
                            <div>
                                <label for="disk-critical">Disk Critical (%)</label>
                                <input type="number" id="disk-critical" min="0" max="100" step="1" style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid var(--border);background:var(--glass);">
                            </div>
                        </div>
                    </div>

                    <!-- Agent Settings -->
                    <div>
                        <h3 style="margin-top:0;color:var(--primary);">Agent Settings</h3>
                        <div style="display:flex;flex-direction:column;gap:1rem;">
                            <div>
                                <label for="check-interval">Check Interval (seconds)</label>
                                <input type="number" id="check-interval" min="1" max="3600" step="1" style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid var(--border);background:var(--glass);">
                            </div>
                            <div>
                                <label for="log-level">Log Level</label>
                                <select id="log-level" style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid var(--border);background:var(--glass);">
                                    <option value="DEBUG">Debug</option>
                                    <option value="INFO">Info</option>
                                    <option value="WARNING">Warning</option>
                                    <option value="ERROR">Error</option>
                                    <option value="CRITICAL">Critical</option>
                                </select>
                            </div>
                            <div>
                                <label for="web-port">Web Interface Port</label>
                                <input type="number" id="web-port" min="1024" max="65535" step="1" style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid var(--border);background:var(--glass);">
                            </div>
                            <div>
                                <label for="ollama-url">Ollama URL</label>
                                <input type="url" id="ollama-url" style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid var(--border);background:var(--glass);">
                            </div>
                            <div>
                                <label for="ollama-model">Ollama Model</label>
                                <input type="text" id="ollama-model" style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid var(--border);background:var(--glass);">
                            </div>
                            <div style="display:flex;align-items:center;gap:0.5rem;">
                                <input type="checkbox" id="persistence-enabled">
                                <label for="persistence-enabled">Enable Database Persistence</label>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Current Configuration Display -->
                <div style="margin-top:2rem;">
                    <h3 style="margin-top:0;color:var(--primary);">Current Configuration</h3>
                    <div id="current-config" style="background:rgba(0,0,0,0.05);border-radius:12px;padding:1rem;max-height:200px;overflow-y:auto;font-family:'Courier New',monospace;font-size:0.85rem;">
                        <div class="loader">Loading configuration...</div>
                    </div>
                </div>
            </section>
        </main>

        <!-- Toast Notifications Container -->
        <div class="toast-container" id="toast-container" aria-live="polite" aria-label="Notifications"></div>

        <script>
        // Toast notification system
        function showToast(type, title, message, duration = 5000) {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `
                <div class="toast-header">
                    <span class="toast-title">${title}</span>
                    <button class="toast-close" aria-label="Close notification">&times;</button>
                </div>
                <div class="toast-message">${message}</div>
            `;
            
            container.appendChild(toast);
            
            // Show animation
            setTimeout(() => toast.classList.add('show'), 100);
            
            // Auto-remove
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => container.removeChild(toast), 300);
            }, duration);
            
            // Manual close
            toast.querySelector('.toast-close').addEventListener('click', () => {
                toast.classList.remove('show');
                setTimeout(() => container.removeChild(toast), 300);
            });
        }

        // Hamburger menu for mobile
        const hamburger = document.querySelector('.hamburger');
        const nav = document.getElementById('main-nav');
        if (hamburger && nav) {
            hamburger.addEventListener('click', () => {
                const expanded = nav.classList.toggle('open');
                hamburger.setAttribute('aria-expanded', expanded);
            });
            // Close nav on link click (mobile)
            nav.querySelectorAll('a').forEach(link => {
                link.addEventListener('click', () => {
                    nav.classList.remove('open');
                    hamburger.setAttribute('aria-expanded', false);
                });
            });
            // Keyboard accessibility for hamburger
            hamburger.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ' ') {
                    hamburger.click();
                }
            });
        }
        // Always show sidebar on desktop
        function handleResizeNav() {
            if (window.innerWidth > 900) {
                nav.classList.remove('open');
                nav.style.left = '';
            }
        }
        window.addEventListener('resize', handleResizeNav);
        handleResizeNav();

        // Dark mode toggle
        const darkModeToggle = document.getElementById('darkModeToggle');
        darkModeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            if(document.body.classList.contains('dark-mode')) {
                document.documentElement.style.setProperty('--background', '#232946');
                document.documentElement.style.setProperty('--secondary', '#f4f6fb');
                document.documentElement.style.setProperty('--glass', 'rgba(35,41,70,0.85)');
                darkModeToggle.textContent = 'Light Mode';
            } else {
                document.documentElement.style.setProperty('--background', '#f4f6fb');
                document.documentElement.style.setProperty('--secondary', '#232946');
                document.documentElement.style.setProperty('--glass', 'rgba(255,255,255,0.7)');
                darkModeToggle.textContent = 'Dark Mode';
            }
            localStorage.setItem('dashboard-dark-mode', document.body.classList.contains('dark-mode'));
        });

        // Persist dark mode
        if(localStorage.getItem('dashboard-dark-mode') === 'true') {
            document.body.classList.add('dark-mode');
            document.documentElement.style.setProperty('--background', '#232946');
            document.documentElement.style.setProperty('--secondary', '#f4f6fb');
            document.documentElement.style.setProperty('--glass', 'rgba(35,41,70,0.85)');
            darkModeToggle.textContent = 'Light Mode';
        }

        // Send command function
        async function sendCommand(command, target = 'all') {
            try {
                const response = await fetch('/api/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command, target })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    showToast('success', 'Command Sent', result.message || `${command} sent to ${target}`, 3000);
                } else {
                    showToast('danger', 'Command Failed', result.message || `Failed to send ${command} command`, 5000);
                }
                // Refresh relevant data
                setTimeout(() => {
                    loadAgentStatus();
                    loadSystemOverview();
                }, 1000);
            } catch (error) {
                showToast('danger', 'Command Failed', `Failed to send ${command} command`, 5000);
            }
        }

        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            showToast('info', 'Refreshing', 'Dashboard data is being refreshed...', 2000);
            loadSystemOverview();
            loadAgentStatus();
            loadLiveAlerts();
            loadActivityFeed();
            loadSystemHealth();
        });

        // ECharts chart instances
        let agentStatusChart = null;
        let systemMetricsChart = null;

        // Fetch and render System Overview
        async function loadSystemOverview() {
            const el = document.getElementById('system-overview');
            const loader = document.getElementById('system-overview-loader');
            try {
                const res = await fetch('/api/system');
                const data = await res.json();
                if (loader) loader.style.display = 'none';
                if (!data || !data.system_overview) {
                    el.innerHTML = '<div style="text-align:center;padding:2rem;color:#888;">System overview data not available.</div>';
                    showToast('warning', 'No Data', 'System overview is currently unavailable', 4000);
                    return;
                }
                let html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;">';
                const overview = data.system_overview;
                html += `
                    <div class="metric-card">
                        <div class="metric-value">${overview.cpu_usage?.toFixed(1) || 'N/A'}%</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${overview.memory_usage?.toFixed(1) || 'N/A'}%</div>
                        <div class="metric-label">Memory Usage</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${overview.running_agents || 0}/${overview.total_agents || 0}</div>
                        <div class="metric-label">Agents Running</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${data.active_issues?.length || 0}</div>
                        <div class="metric-label">Active Issues</div>
                    </div>
                `;
                html += '</div>';
                el.innerHTML = html;
            } catch (e) {
                if (loader) loader.textContent = 'Failed to load system overview.';
                el.innerHTML = '<div style="text-align:center;padding:2rem;color:#ef4444;">Failed to load system overview</div>';
                showToast('danger', 'Error', 'Failed to load system overview', 5000);
            }
        }

        // Fetch and render System Health
        async function loadSystemHealth() {
            const el = document.getElementById('system-health');
            const loader = document.getElementById('system-health-loader');
            try {
                const res = await fetch('/api/health');
                const data = await res.json();
                if (loader) loader.style.display = 'none';
                
                const statusClass = data.status === 'healthy' ? 'status-healthy' : 'status-critical';
                const statusText = data.status === 'healthy' ? 'Healthy' : 'Unhealthy';
                
                el.innerHTML = `
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;">
                        <div class="metric-card">
                            <div class="metric-value">
                                <span class="status-indicator ${statusClass}"></span>${statusText}
                            </div>
                            <div class="metric-label">System Status</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${data.agents_running || 0}</div>
                            <div class="metric-label">Agents Running</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${data.system_health || 'Unknown'}</div>
                            <div class="metric-label">Health Score</div>
                        </div>
                    </div>
                `;
            } catch (e) {
                if (loader) loader.textContent = 'Failed to load system health.';
                showToast('danger', 'Error', 'Failed to load system health', 5000);
            }
        }

        // Fetch and render Agent Status
        async function loadAgentStatus() {
            const el = document.getElementById('agent-status');
            const loader = document.getElementById('agent-status-loader');
            try {
                const res = await fetch('/api/agents');
                const data = await res.json();
                if (loader) loader.style.display = 'none';
                if (!data || Object.keys(data).length === 0) {
                    el.innerHTML = '<div style="text-align:center;padding:2rem;color:#888;">No agent status data available.</div>';
                    showToast('warning', 'No Data', 'Agent status is currently unavailable', 4000);
                    return;
                }
                let html = '<table style="width:100%;border-collapse:collapse;font-size:1rem;">';
                html += '<thead><tr><th style="text-align:left;padding:0.5rem;">Agent</th><th>Status</th><th>Health</th><th>Uptime</th><th>Checks</th><th>Errors</th><th>Actions</th></tr></thead><tbody>';
                const chartData = {names:[], health:[]};
                for(const [name, agent] of Object.entries(data)) {
                    const statusClass = agent.health === 'healthy' ? 'status-healthy' : 
                                      agent.health === 'warning' ? 'status-warning' : 'status-critical';
                    const statusText = agent.health === 'healthy' ? 'Healthy' : 
                                     agent.health === 'warning' ? 'Warning' : 'Critical';
                    html += `
                        <tr>
                            <td style="padding:0.5rem;font-weight:600;">${name}</td>
                            <td><span class="status-indicator ${agent.status ? 'status-healthy' : 'status-critical'}"></span>${agent.status ? 'Running' : 'Stopped'}</td>
                            <td><span class="status-indicator ${statusClass}"></span>${statusText}</td>
                            <td>${(agent.uptime/60).toFixed(1)} min</td>
                            <td>${agent.check_count}</td>
                            <td>${agent.error_count}</td>
                            <td>
                                <button class="btn" style="padding:0.3rem 0.6rem;font-size:0.8rem;" onclick="sendCommand('restart', '${name}')" aria-label="Restart ${name}">
                                    <i class="fas fa-redo"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                    chartData.names.push(name);
                    chartData.health.push(agent.health === 'healthy' ? 1 : agent.health === 'warning' ? 0.5 : 0);
                }
                html += '</tbody></table>';
                el.innerHTML = html;
                // Render ECharts bar chart for agent health
                const chartEl = document.getElementById('agent-status-chart');
                if(chartEl) {
                    if (!agentStatusChart) {
                        agentStatusChart = echarts.init(chartEl);
                    }
                    agentStatusChart.setOption({
                        title: {text: 'Agent Health Overview', left: 'center', textStyle:{fontWeight:'bold',fontSize:18}},
                        tooltip: {},
                        xAxis: {type: 'category', data: chartData.names},
                        yAxis: {type: 'value', min:0, max:1, axisLabel:{formatter:v=>v===1?'Healthy':v===0.5?'Warning':'Critical'}},
                        series: [{
                            name: 'Health',
                            type: 'bar',
                            data: chartData.health,
                            itemStyle: {
                                color: function(params) {
                                    if(params.value === 1) return '#10b981';
                                    if(params.value === 0.5) return '#f59e0b';
                                    return '#ef4444';
                                }
                            },
                            barWidth: '40%'
                        }]
                    });
                }
            } catch (e) {
                if (loader) loader.textContent = 'Failed to load agent status.';
                el.innerHTML = '<div style="text-align:center;padding:2rem;color:#ef4444;">Failed to load agent status</div>';
                showToast('danger', 'Error', 'Failed to load agent status', 5000);
            }
        }

        // Fetch and render Live Alerts
        async function loadLiveAlerts() {
            const el = document.getElementById('live-alerts');
            const loader = document.getElementById('live-alerts-loader');
            try {
                const res = await fetch('/api/alerts/live');
                const data = await res.json();
                if (loader) loader.style.display = 'none';
                if (!Array.isArray(data) || data.length === 0) {
                    el.innerHTML = '<div style="text-align:center;padding:2rem;color:#888;">No recent alerts. System is running smoothly! 🎉</div>';
                    showToast('info', 'No Alerts', 'No recent alerts found', 3000);
                    return;
                }
                let html = '<ul style="list-style:none;padding:0;margin:0;">';
                for(const alert of data.slice(-10)) {
                    const severityColor = alert.severity === 'CRITICAL' ? '#ef4444' : 
                                        alert.severity === 'ERROR' ? '#f59e0b' : '#4f8cff';
                    html += `
                        <li style="margin-bottom:0.7rem;padding:0.5rem;background:rgba(255,255,255,0.1);border-radius:8px;">
                            <span style="font-weight:bold;">${alert.emoji||''} ${alert.agent}</span> 
                            <span style="color:${severityColor};font-weight:600;">[${alert.severity}]</span> 
                            <span style="font-size:0.95em;">${alert.message}</span> 
                            <span style="color:#888;font-size:0.9em;">(${alert.timestamp})</span>
                        </li>
                    `;
                }
                html += '</ul>';
                el.innerHTML = html;
            } catch (e) {
                if (loader) loader.textContent = 'Failed to load alerts.';
                el.innerHTML = '<div style="text-align:center;padding:2rem;color:#ef4444;">Failed to load alerts</div>';
                showToast('danger', 'Error', 'Failed to load alerts', 5000);
            }
        }

        // Fetch and render Activity Feed
        async function loadActivityFeed() {
            const el = document.getElementById('activity-feed');
            const loader = document.getElementById('activity-feed-loader');
            try {
                const res = await fetch('/api/activity');
                const data = await res.json();
                if (loader) loader.style.display = 'none';
                
                if(Array.isArray(data) && data.length) {
                    let html = '<ul style="list-style:none;padding:0;margin:0;">';
                    for(const activity of data.slice(-10)) {
                        html += `
                            <li style="margin-bottom:0.7rem;padding:0.5rem;background:rgba(255,255,255,0.1);border-radius:8px;">
                                <span style="font-weight:600;">${activity.description || 'System activity'}</span>
                                <span style="color:#888;font-size:0.9em;display:block;">${activity.timestamp || 'Unknown time'}</span>
                            </li>
                        `;
                    }
                    html += '</ul>';
                    el.innerHTML = html;
                } else {
                    el.innerHTML = '<div style="text-align:center;padding:2rem;color:#888;">No recent activity.</div>';
                }
            } catch (e) {
                if (loader) loader.textContent = 'Failed to load activity feed.';
                showToast('danger', 'Error', 'Failed to load activity feed', 5000);
            }
        }

        // Load system metrics chart
        async function loadSystemMetricsChart() {
            try {
                const res = await fetch('/api/metrics');
                const data = await res.json();
                const chartEl = document.getElementById('system-metrics-chart');
                if(chartEl && data) {
                    if (!systemMetricsChart) {
                        systemMetricsChart = echarts.init(chartEl);
                    }
                    systemMetricsChart.setOption({
                        title: {text: 'System Performance Metrics', left: 'center', textStyle:{fontWeight:'bold',fontSize:18}},
                        tooltip: {trigger: 'axis'},
                        legend: {data: ['CPU Usage', 'Memory Usage'], top: 30},
                        xAxis: {type: 'category', data: ['Current']},
                        yAxis: {type: 'value', min: 0, max: 100, axisLabel: {formatter: '{value}%'}},
                        series: [
                            {
                                name: 'CPU Usage',
                                type: 'line',
                                data: [data.cpu?.usage_percent || 0],
                                smooth: true,
                                lineStyle: {color: '#4f8cff'},
                                itemStyle: {color: '#4f8cff'}
                            },
                            {
                                name: 'Memory Usage',
                                type: 'line',
                                data: [data.memory?.usage_percent || 0],
                                smooth: true,
                                lineStyle: {color: '#10b981'},
                                itemStyle: {color: '#10b981'}
                            }
                        ]
                    });
                } else if (chartEl) {
                    chartEl.innerHTML = '<div style="text-align:center;padding:2rem;color:#888;">No system metrics data available.</div>';
                    showToast('warning', 'No Data', 'System metrics are currently unavailable', 4000);
                }
            } catch (e) {
                const chartEl = document.getElementById('system-metrics-chart');
                if (chartEl) chartEl.innerHTML = '<div style="text-align:center;padding:2rem;color:#ef4444;">Failed to load system metrics</div>';
                showToast('danger', 'Error', 'Failed to load system metrics', 5000);
            }
        }

        // Logs Viewer Functions
        let logsInterval = null;
        let currentLogLevel = 'all';

        async function loadLogs() {
            const el = document.getElementById('logs-content');
            const container = document.getElementById('logs-container');
            try {
                const res = await fetch('/api/logs');
                const data = await res.json();
                
                if (data.logs && Array.isArray(data.logs)) {
                    let html = '';
                    const filteredLogs = data.logs.filter(log => 
                        currentLogLevel === 'all' || log.level === currentLogLevel
                    );
                    
                    for (const log of filteredLogs.slice(-100)) {
                        const levelColor = log.level === 'CRITICAL' ? '#ef4444' : 
                                         log.level === 'ERROR' ? '#f59e0b' : 
                                         log.level === 'WARNING' ? '#fbbf24' : '#4f8cff';
                        html += `<div style="margin-bottom:0.3rem;color:${levelColor};font-weight:600;">[${log.timestamp}] ${log.level}</div>`;
                        html += `<div style="margin-bottom:0.5rem;color:var(--secondary);">${log.message}</div>`;
                    }
                    el.innerHTML = html;
                    
                    // Auto-scroll to bottom if enabled
                    if (document.getElementById('auto-scroll-logs').checked) {
                        container.scrollTop = container.scrollHeight;
                    }
                } else {
                    el.innerHTML = '<div style="text-align:center;padding:2rem;color:#888;">No logs available</div>';
                }
            } catch (e) {
                el.innerHTML = '<div style="text-align:center;padding:2rem;color:#ef4444;">Failed to load logs</div>';
                showToast('danger', 'Error', 'Failed to load logs', 5000);
            }
        }

        function refreshLogs() {
            loadLogs();
            showToast('info', 'Logs Refreshed', 'Log data has been updated', 2000);
        }

        function clearLogs() {
            if (confirm('Are you sure you want to clear the logs? This action cannot be undone.')) {
                document.getElementById('logs-content').innerHTML = '<div style="text-align:center;padding:2rem;color:#888;">Logs cleared</div>';
                showToast('warning', 'Logs Cleared', 'Log display has been cleared', 3000);
            }
        }

        // Configuration Management Functions
        async function loadConfiguration() {
            const el = document.getElementById('current-config');
            try {
                const res = await fetch('/api/config');
                const data = await res.json();
                
                // Populate form fields
                if (data.thresholds) {
                    document.getElementById('cpu-warning').value = data.thresholds.cpu_warning || 75;
                    document.getElementById('cpu-critical').value = data.thresholds.cpu_critical || 90;
                    document.getElementById('memory-warning').value = data.thresholds.memory_warning || 85;
                    document.getElementById('memory-critical').value = data.thresholds.memory_critical || 95;
                    document.getElementById('disk-warning').value = data.thresholds.disk_warning || 85;
                    document.getElementById('disk-critical').value = data.thresholds.disk_critical || 95;
                }
                
                if (data.agent_config) {
                    const sensorConfig = data.agent_config.get('sensor', {});
                    document.getElementById('check-interval').value = sensorConfig.check_interval || 30;
                }
                
                if (data.logging) {
                    document.getElementById('log-level').value = data.logging.log_level || 'INFO';
                }
                
                if (data.web_interface) {
                    document.getElementById('web-port').value = data.web_interface.port || 8000;
                }
                
                if (data.ollama) {
                    document.getElementById('ollama-url').value = data.ollama.url || 'http://localhost:11434';
                    document.getElementById('ollama-model').value = data.ollama.model || 'mistral';
                }
                
                document.getElementById('persistence-enabled').checked = data.persistence_enabled !== false;
                
                // Display current configuration
                el.innerHTML = `<pre style="margin:0;white-space:pre-wrap;">${JSON.stringify(data, null, 2)}</pre>`;
            } catch (e) {
                el.innerHTML = '<div style="text-align:center;padding:2rem;color:#ef4444;">Failed to load configuration</div>';
                showToast('danger', 'Error', 'Failed to load configuration', 5000);
            }
        }

        async function saveConfig() {
            try {
                const configData = {
                    thresholds: {
                        cpu_warning: parseFloat(document.getElementById('cpu-warning').value),
                        cpu_critical: parseFloat(document.getElementById('cpu-critical').value),
                        memory_warning: parseFloat(document.getElementById('memory-warning').value),
                        memory_critical: parseFloat(document.getElementById('memory-critical').value),
                        disk_warning: parseFloat(document.getElementById('disk-warning').value),
                        disk_critical: parseFloat(document.getElementById('disk-critical').value)
                    },
                    agent_config: {
                        sensor: {
                            check_interval: parseInt(document.getElementById('check-interval').value)
                        }
                    },
                    logging: {
                        log_level: document.getElementById('log-level').value
                    },
                    web_interface: {
                        port: parseInt(document.getElementById('web-port').value)
                    },
                    ollama: {
                        url: document.getElementById('ollama-url').value,
                        model: document.getElementById('ollama-model').value
                    },
                    persistence_enabled: document.getElementById('persistence-enabled').checked
                };
                
                const res = await fetch('/api/config/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(configData)
                });
                
                const result = await res.json();
                if (result.status === 'success') {
                    showToast('success', 'Configuration Saved', 'Settings have been updated successfully', 3000);
                    loadConfiguration(); // Refresh display
                } else {
                    throw new Error(result.message || 'Failed to save configuration');
                }
            } catch (e) {
                showToast('danger', 'Save Failed', `Failed to save configuration: ${e.message}`, 5000);
            }
        }

        function resetConfig() {
            if (confirm('Are you sure you want to reset all configuration to default values?')) {
                loadConfiguration(); // Reload original values
                showToast('warning', 'Configuration Reset', 'All settings have been reset to defaults', 3000);
            }
        }

        function exportConfig() {
            try {
                const configData = {
                    thresholds: {
                        cpu_warning: parseFloat(document.getElementById('cpu-warning').value),
                        cpu_critical: parseFloat(document.getElementById('cpu-critical').value),
                        memory_warning: parseFloat(document.getElementById('memory-warning').value),
                        memory_critical: parseFloat(document.getElementById('memory-critical').value),
                        disk_warning: parseFloat(document.getElementById('disk-warning').value),
                        disk_critical: parseFloat(document.getElementById('disk-critical').value)
                    },
                    agent_config: {
                        sensor: {
                            check_interval: parseInt(document.getElementById('check-interval').value)
                        }
                    },
                    logging: {
                        log_level: document.getElementById('log-level').value
                    },
                    web_interface: {
                        port: parseInt(document.getElementById('web-port').value)
                    },
                    ollama: {
                        url: document.getElementById('ollama-url').value,
                        model: document.getElementById('ollama-model').value
                    },
                    persistence_enabled: document.getElementById('persistence-enabled').checked,
                    exported_at: new Date().toISOString()
                };
                
                const blob = new Blob([JSON.stringify(configData, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `agent-system-config-${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                showToast('success', 'Configuration Exported', 'Configuration has been downloaded', 3000);
            } catch (e) {
                showToast('danger', 'Export Failed', `Failed to export configuration: ${e.message}`, 5000);
            }
        }

        // Event listeners for logs and config
        document.getElementById('log-level-filter').addEventListener('change', function() {
            currentLogLevel = this.value;
            loadLogs();
        });

        // Initial load
        loadSystemOverview();
        loadSystemHealth();
        loadAgentStatus();
        loadLiveAlerts();
        loadActivityFeed();
        loadSystemMetricsChart();
        loadLogs();
        loadConfiguration();

        // Auto-refresh
        setInterval(loadSystemOverview, 30000);
        setInterval(loadSystemHealth, 30000);
        setInterval(loadAgentStatus, 30000);
        setInterval(loadLiveAlerts, 15000);
        setInterval(loadActivityFeed, 30000);
        setInterval(loadSystemMetricsChart, 60000);
        setInterval(loadLogs, 10000); // Refresh logs every 10 seconds

        // Show welcome toast
        setTimeout(() => {
            showToast('success', 'Dashboard Loaded', 'Welcome to the AI Agent System Dashboard!', 3000);
        }, 1000);

        // Nav bar smooth scroll and active link
        document.querySelectorAll('nav ul li a').forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href && href.startsWith('#')) {
                    e.preventDefault();
                    const target = document.querySelector(href);
                    if (target) {
                        target.scrollIntoView({behavior: 'smooth', block: 'start'});
                        // Update active class
                        document.querySelectorAll('nav ul li a').forEach(l => l.classList.remove('active'));
                        this.classList.add('active');
                    }
                }
            });
        });
        // Scrollspy: highlight nav link on scroll
        const sectionIds = ['#dashboard', '#agents', '#alerts', '#logs', '#settings'];
        window.addEventListener('scroll', () => {
            let current = sectionIds[0];
            for (const id of sectionIds) {
                const section = document.querySelector(id);
                if (section && section.getBoundingClientRect().top <= 80) {
                    current = id;
                }
            }
            document.querySelectorAll('nav ul li a').forEach(link => {
                link.classList.toggle('active', link.getAttribute('href') === current);
            });
        });

        // --- Banner for critical alerts ---
        function showCriticalBanner(message) {
            const banner = document.getElementById('critical-banner');
            if (banner) {
                banner.textContent = message;
                banner.style.display = 'block';
            }
        }
        function hideCriticalBanner() {
            const banner = document.getElementById('critical-banner');
            if (banner) banner.style.display = 'none';
        }
        // --- API error handling: show banner for critical errors ---
        async function safeFetch(url, opts) {
            try {
                const res = await fetch(url, opts);
                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    if (res.status >= 500) showCriticalBanner(data.error || 'Internal server error');
                    throw new Error(data.error || res.statusText);
                }
                hideCriticalBanner();
                return await res.json();
            } catch (e) {
                showCriticalBanner(e.message || 'Network error');
                throw e;
            }
        }
        </script>
    </body>
    </html>
    """


@app.get("/api/system")
async def get_system_info():
    """Get comprehensive system information with caching."""
    try:
        # Check cache first
        cached_data = get_cached_data("system_info", max_age=15)  # 15 second cache
        if cached_data:
            return cached_data

        info = orchestrator.get_system_info()

        # Compose system_overview for the dashboard with fallback values
        system_overview = {
            "cpu_usage": 0,
            "memory_usage": 0,
            "running_agents": info.get("running_agents", 0),
            "total_agents": info.get("total_agents", 0),
        }

        # Try to get metrics from sensor agent if available
        try:
            sensor_agent = orchestrator.agents.get("sensor")
            if sensor_agent and hasattr(sensor_agent, "get_current_metrics"):
                latest_metrics = sensor_agent.get_current_metrics()
                if latest_metrics:
                    cpu_usage = latest_metrics.get("cpu", {}).get("usage_percent")
                    memory_usage = latest_metrics.get("memory", {}).get("usage_percent")
                    if cpu_usage is not None:
                        system_overview["cpu_usage"] = cpu_usage
                    if memory_usage is not None:
                        system_overview["memory_usage"] = memory_usage
        except Exception as e:
            # Log but don't fail the entire endpoint
            print(f"Warning: Could not get sensor metrics: {e}")

        # Add active issues if available from analyzer
        active_issues = []
        try:
            analyzer_agent = orchestrator.agents.get("analyzer")
            if analyzer_agent and hasattr(analyzer_agent, "get_analysis_summary"):
                summary = analyzer_agent.get_analysis_summary()
                if summary and isinstance(summary, dict):
                    issues = summary.get("latest_analysis", {}).get("issues_detected")
                    if isinstance(issues, list):
                        active_issues = issues
                    elif isinstance(issues, int):
                        active_issues = [f"{issues} issues detected"]
        except Exception as e:
            # Log but don't fail the entire endpoint
            print(f"Warning: Could not get analyzer issues: {e}")

        info["system_overview"] = system_overview
        info["active_issues"] = active_issues
        info["cached_at"] = time.time()

        # Cache the result
        performance_cache["system_info"] = info

        return info
    except Exception as e:
        # Return a minimal response instead of 500 error
        return {
            "system_overview": {
                "cpu_usage": 0,
                "memory_usage": 0,
                "running_agents": 0,
                "total_agents": 0,
            },
            "active_issues": [],
            "error": f"System information temporarily unavailable: {str(e)}",
            "cached_at": time.time(),
        }


@app.get("/api/agents")
async def get_agents():
    """Get status of all agents with caching."""
    try:
        # Check cache first
        cached_data = get_cached_data("agents_status", max_age=10)  # 10 second cache
        if cached_data:
            return cached_data

        agents = {}
        for agent_name, agent in orchestrator.agents.items():
            stats = orchestrator.get_agent_stats(agent_name)
            if stats:
                agents[agent_name] = {
                    "health": stats.get("health_status", "unknown"),
                    "status": stats.get("running", False),
                    "uptime": stats.get("uptime", 0),
                    "check_count": stats.get("check_count", 0),
                    "error_count": stats.get("error_count", 0),
                }

        # Cache the result
        performance_cache["agents_status"] = {**agents, "cached_at": time.time()}

        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics")
async def get_current_metrics():
    """Get current system metrics with caching and robust error handling."""
    logger = logging.getLogger("web_interface.api.metrics")
    def ensure_floats(obj):
        if isinstance(obj, dict):
            return {k: ensure_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ensure_floats(v) for v in obj]
        elif isinstance(obj, str):
            try:
                if obj.replace('.', '', 1).isdigit():
                    return float(obj)
            except Exception:
                pass
            return obj
        else:
            return obj
    try:
        metrics = get_cached_data("metrics")
        no_data = False
        if metrics is None:
            sensor_agent = None
            try:
                from system_orchestrator import orchestrator
                sensor_agent = getattr(orchestrator, "agents", {}).get("sensor")
            except Exception:
                sensor_agent = None
            if sensor_agent and hasattr(sensor_agent, "get_current_metrics"):
                metrics = sensor_agent.get_current_metrics() or {}
            else:
                from agents.sensor_agent import SensorAgent
                metrics = SensorAgent().get_current_metrics() or {}
        metrics = ensure_floats(metrics)
        # Ensure structure
        if not metrics or not isinstance(metrics, dict) or "cpu" not in metrics or "memory" not in metrics:
            logger.warning("/api/metrics: No valid metrics found, returning fallback structure.")
            metrics = {
                "cpu": {"usage_percent": 0},
                "memory": {"usage_percent": 0},
                "no_data": True
            }
        return metrics
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"/api/metrics error: {e}\n{tb}")
        return {"error": str(e), "details": tb, "no_data": True}, 500


@app.get("/api/health")
async def health_check():
    """Health check endpoint with caching."""
    try:
        # Check cache first
        cached_data = get_cached_data("health_check", max_age=30)  # 30 second cache
        if cached_data:
            return cached_data

        # Get basic health data
        try:
            agents_running = (
                sum(
                    1
                    for agent in orchestrator.agents.values()
                    if getattr(agent, "running", False)
                )
                if hasattr(orchestrator, "agents")
                else 0
            )
        except Exception:
            agents_running = 0

        health_data = {
            "status": "healthy" if system_running else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "system_health": getattr(orchestrator, "system_health", "unknown"),
            "agents_running": agents_running,
            "system_ready": system_ready,
            "uptime": time.time() - startup_time if startup_time else 0,
            "cached_at": time.time(),
        }

        # Cache the result
        performance_cache["health_check"] = health_data

        return health_data
    except Exception as e:
        # Return a basic health response even if there's an error
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "system_ready": False,
            "agents_running": 0,
        }


@app.get("/api/analysis")
async def get_analysis_results():
    """Get recent analysis results."""
    try:
        analyzer_agent = orchestrator.agents.get("analyzer")
        if analyzer_agent and hasattr(analyzer_agent, "get_analysis_summary"):
            return analyzer_agent.get_analysis_summary()
        return {"error": "Analysis results not available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remediation")
async def get_remediation_summary():
    """Get remediation summary."""
    try:
        remediator_agent = orchestrator.agents.get("remediator")
        if remediator_agent and hasattr(remediator_agent, "get_remediation_summary"):
            return remediator_agent.get_remediation_summary()
        return {"error": "Remediation summary not available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/activity")
async def get_recent_activity(limit: int = 50):
    """Get recent system activity."""
    try:
        communicator_agent = orchestrator.agents.get("communicator")
        if communicator_agent and hasattr(
            communicator_agent, "get_communication_summary"
        ):
            summary = communicator_agent.get_communication_summary()
            return summary.get("recent_messages", [])
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/command")
async def send_command(command_data: Dict[str, Any]):
    """Send a command to the system."""
    try:
        command = command_data.get("command")
        target = command_data.get("target", "all")

        if not command:
            raise HTTPException(status_code=400, detail="Command is required")

        result = await orchestrator.send_command(command, target)
        if result and result.get("status") == "success":
            return {
                "status": "success",
                "message": f"Command '{command}' sent to {target}",
                "result": result,
            }
        else:
            return {
                "status": "error",
                "message": result.get("error", "Unknown error"),
                "result": result,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/messages")
async def get_message_bus_stats():
    """Get message bus statistics."""
    try:
        return message_bus.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/messages/recent")
async def get_recent_messages(limit: int = 20):
    """Get recent messages from the message bus for live activity feed."""
    try:
        return message_bus.get_recent_messages(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_configuration():
    """Get current system configuration."""
    try:
        return config.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/update")
async def update_configuration(config_data: Dict[str, Any]):
    """Update system configuration."""
    try:
        # Update thresholds
        if "thresholds" in config_data:
            thresholds = config_data["thresholds"]
            if "cpu_warning" in thresholds:
                config.update_threshold("cpu_warning", thresholds["cpu_warning"])
            if "cpu_critical" in thresholds:
                config.update_threshold("cpu_critical", thresholds["cpu_critical"])
            if "memory_warning" in thresholds:
                config.update_threshold("memory_warning", thresholds["memory_warning"])
            if "memory_critical" in thresholds:
                config.update_threshold(
                    "memory_critical", thresholds["memory_critical"]
                )
            if "disk_warning" in thresholds:
                config.update_threshold("disk_warning", thresholds["disk_warning"])
            if "disk_critical" in thresholds:
                config.update_threshold("disk_critical", thresholds["disk_critical"])

        # Update agent configuration
        if "agent_config" in config_data:
            agent_config = config_data["agent_config"]
            if "sensor" in agent_config and "check_interval" in agent_config["sensor"]:
                sensor_config = config.get_agent_config("sensor")
                sensor_config.check_interval = agent_config["sensor"]["check_interval"]

        # Update logging configuration
        if "logging" in config_data:
            logging_config = config_data["logging"]
            if "log_level" in logging_config:
                config.logging.log_level = logging_config["log_level"]

        # Update web interface configuration
        if "web_interface" in config_data:
            web_config = config_data["web_interface"]
            if "port" in web_config:
                config.web_port = web_config["port"]

        # Update Ollama configuration
        if "ollama" in config_data:
            ollama_config = config_data["ollama"]
            if "url" in ollama_config:
                config.ollama.url = ollama_config["url"]
            if "model" in ollama_config:
                config.ollama.model = ollama_config["model"]

        # Update persistence configuration
        if "persistence_enabled" in config_data:
            config.persistence_enabled = config_data["persistence_enabled"]

        return {
            "status": "success",
            "message": "Configuration updated successfully",
            "updated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs")
async def get_logs(limit: int = 100):
    """Get recent system logs with caching and optimized parsing."""
    try:
        cached_data = get_cached_data("system_logs", max_age=5)
        if cached_data:
            return cached_data
        log_path = config.logging.log_file
        logs = []
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                if len(lines) > limit * 2:
                    lines = lines[-limit * 2 :]
            log_pattern = re.compile(r"\\[(.*?)\\] (DEBUG|INFO|WARNING|ERROR|CRITICAL)\\s+([\\S]+): (.+)")
            matched = False
            for line in reversed(lines):
                match = log_pattern.search(line)
                if match:
                    matched = True
                    timestamp, level, agent, message = match.groups()
                    emoji = ""
                    agent_name = agent
                    if " " in agent:
                        emoji, agent_name = agent.split(" ", 1)
                    logs.append({
                        "timestamp": timestamp,
                        "level": level,
                        "agent": agent_name,
                        "emoji": emoji,
                        "message": message.strip(),
                        "raw_line": line.strip(),
                    })
                    if len(logs) >= limit:
                        break
            if not matched:
                logging.getLogger("web_interface.api.logs").warning("/api/logs: No log lines matched regex. Returning fallback entry.")
                logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "agent": "system",
                    "emoji": "",
                    "message": "No logs found or log format mismatch.",
                    "raw_line": "",
                })
            result = {"logs": list(reversed(logs)), "cached_at": time.time()}
            performance_cache["system_logs"] = result
            return result
        except FileNotFoundError:
            return {"logs": [{
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "agent": "system",
                "emoji": "",
                "message": "Log file not found.",
                "raw_line": "",
            }], "error": "Log file not found", "cached_at": time.time()}
        except Exception as e:
            return {"logs": [{
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "agent": "system",
                "emoji": "",
                "message": f"Error reading log file: {str(e)}",
                "raw_line": "",
            }], "error": f"Error reading log file: {str(e)}", "cached_at": time.time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/llm_status")
async def get_llm_status():
    """Get LLM provider status and health (Ollama-only)."""
    try:
        # Check Ollama status
        ollama_healthy = False
        ollama_models = []
        try:
            from utils.ollama_client import ollama_client

            ollama_healthy = await ollama_client.health_check()
            if ollama_healthy:
                ollama_models = await ollama_client.list_models()
        except Exception:
            pass

        return {
            "ollama": {
                "available": ollama_healthy,
                "provider": "Ollama (Local)",
                "requires_api_key": False,
                "models": ollama_models,
                "default_model": config.ollama.model,
                "url": config.ollama.url,
            },
            "current_providers": {
                "analyzer": config.agent_ai_provider.get("analyzer", "ollama"),
                "remediator": config.agent_ai_provider.get("remediator", "ollama"),
            },
            "recommendation": "ollama" if ollama_healthy else "none",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/llm_agents")
async def get_llm_agents():
    """Get LLM provider for each agent."""
    try:
        # Map agent roles to LLM provider
        agent_llms = {}
        for agent in ["sensor", "analyzer", "remediator", "communicator"]:
            provider = config.agent_ai_provider.get(agent, None)
            if provider is None:
                agent_llms[agent] = None
            else:
                agent_llms[agent] = provider
        return agent_llms
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts/live")
async def get_live_alerts(limit: int = 50):
    """Return the latest WARNING/ERROR/CRITICAL agent alerts from the log file."""
    log_path = "debug_output/agent_system.log"
    alert_levels = ["WARNING", "ERROR", "CRITICAL"]
    alert_lines = []
    # Updated regex to match actual log format: "timestamp - AgentSystem - LEVEL - agent: message"
    log_pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - AgentSystem - (WARNING|ERROR|CRITICAL) - (.+): (.+)"
    )
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        # Reverse for newest first
        for line in reversed(lines):
            match = log_pattern.search(line)
            if match:
                timestamp, severity, agent, message = match.groups()
                # Extract emoji and agent name
                emoji = ""
                agent_name = agent
                if " " in agent:
                    emoji, agent_name = agent.split(" ", 1)
                alert_lines.append(
                    {
                        "timestamp": timestamp,
                        "severity": severity,
                        "agent": agent_name,
                        "emoji": emoji,
                        "message": message.strip(),
                    }
                )
                if len(alert_lines) >= limit:
                    break
        # Return in chronological order (oldest first)
        return list(reversed(alert_lines))
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/agent/{agent_name}")
async def get_agent_details(agent_name: str):
    """Get detailed information about a specific agent."""
    try:
        stats = orchestrator.get_agent_stats(agent_name)
        if not stats:
            raise HTTPException(status_code=404, detail="Agent not found")
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/history")
async def get_metric_history(limit: int = 50):
    """Get metric history."""
    try:
        sensor_agent = orchestrator.agents.get("sensor")
        if sensor_agent and hasattr(sensor_agent, "get_metric_history"):
            return sensor_agent.get_metric_history(limit)
        return {"error": "Metric history not available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404, content={"error": "Endpoint not found", "detail": str(exc)}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )


def start_web_interface():
    """Start the web interface with proper configuration."""
    import uvicorn

    # Use config port instead of hardcoded 8002
    port = config.web_port
    host = config.web_host

    print(f"🌐 Starting web interface on http://{host}:{port}")
    print(f"📊 Dashboard: http://{host}:{port}/")
    print(f"🔧 API Docs: http://{host}:{port}/docs")

    uvicorn.run(
        "web_interface:app", host=host, port=port, reload=False, log_level="info"
    )


@app.get("/healthz")
async def healthz():
    return {"ready": system_ready, "error": startup_error}


def require_ready(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not system_ready:
            return JSONResponse(status_code=503, content={"status": "starting", "message": "System is starting, please wait."})
        return await func(*args, **kwargs)
    return wrapper


if __name__ == "__main__":
    start_web_interface()
