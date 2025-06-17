"""
Web Interface - The control panel for the multi-agent system.
This provides a REST API and web interface for monitoring and controlling the system.
Think of it as the mission control dashboard.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import re

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
system_running = False
startup_task = None


@app.on_event("startup")
async def startup_event():
    """Start the multi-agent system when the web interface starts."""
    global system_running, startup_task

    if not system_running:
        startup_task = asyncio.create_task(start_system())
        system_running = True


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the multi-agent system when the web interface shuts down."""
    global system_running

    if system_running:
        await orchestrator.stop()
        system_running = False


async def start_system():
    """Start the multi-agent system in the background."""
    global system_running

    try:
        await orchestrator.start()
    except Exception as e:
        print(f"Failed to start system: {e}")
        system_running = False


# API Routes


@app.get("/", response_class=HTMLResponse)
async def root():
    """Main dashboard page."""
    return """
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>AI Agent System Dashboard</title>
        <link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap' rel='stylesheet'>
        <link href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css' rel='stylesheet'>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {
                --primary: #6366f1;
                --primary-dark: #4f46e5;
                --accent: #8b5cf6;
                --bg: #181c2a;
                --bg-light: #23263a;
                --card: #23263a;
                --card-alt: #23263a;
                --text: #f3f4f6;
                --text-muted: #a0aec0;
                --success: #22c55e;
                --warning: #facc15;
                --danger: #ef4444;
                --info: #38bdf8;
                --border: #2d3147;
                --shadow: 0 4px 24px rgba(0,0,0,0.12);
            }
            html, body { height: 100%; margin: 0; padding: 0; font-family: 'Inter', Arial, sans-serif; background: var(--bg); color: var(--text); }
            body { min-height: 100vh; display: flex; }
            .sidebar {
                width: 240px;
                background: var(--bg-light);
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 32px 0 0 0;
                position: fixed;
                top: 0; left: 0; bottom: 0;
                z-index: 10;
                box-shadow: 2px 0 12px rgba(0,0,0,0.08);
            }
            .sidebar .logo {
                font-size: 2rem;
                font-weight: 700;
                color: var(--primary);
                margin-bottom: 32px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .sidebar nav {
                width: 100%;
            }
            .sidebar nav a {
                display: flex;
                align-items: center;
                gap: 12px;
                color: var(--text-muted);
                text-decoration: none;
                font-size: 1.1rem;
                padding: 14px 32px;
                border-left: 4px solid transparent;
                transition: background 0.2s, color 0.2s, border 0.2s;
            }
            .sidebar nav a.active, .sidebar nav a:hover {
                color: var(--primary);
                background: rgba(99,102,241,0.08);
                border-left: 4px solid var(--primary);
            }
            .sidebar .spacer { flex: 1; }
            .sidebar .footer {
                color: var(--text-muted);
                font-size: 0.9rem;
                margin-bottom: 24px;
            }
            .main {
                margin-left: 240px;
                width: 100%;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            .topbar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                background: var(--bg-light);
                padding: 18px 36px;
                box-shadow: var(--shadow);
                position: sticky;
                top: 0;
                z-index: 5;
            }
            .topbar .status {
                display: flex;
                align-items: center;
                gap: 24px;
            }
            .topbar .status .badge {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 1rem;
                padding: 6px 16px;
                border-radius: 16px;
                background: var(--card);
                color: var(--text-muted);
            }
            .topbar .status .badge.critical { background: var(--danger); color: #fff; }
            .topbar .status .badge.warning { background: var(--warning); color: #222; }
            .topbar .status .badge.healthy { background: var(--success); color: #fff; }
            .topbar .actions {
                display: flex;
                gap: 16px;
            }
            .llm-banner {
                width: 100%;
                background: linear-gradient(90deg, var(--danger), var(--accent));
                color: #fff;
                text-align: center;
                padding: 10px 0;
                font-weight: 600;
                font-size: 1.1rem;
                letter-spacing: 0.5px;
                display: none;
            }
            .llm-banner.active { display: block; }
            .dashboard {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 32px;
                padding: 36px 36px 0 36px;
                flex: 1;
            }
            .card {
                background: var(--card);
                border-radius: 18px;
                box-shadow: var(--shadow);
                padding: 28px 28px 20px 28px;
                margin-bottom: 32px;
                transition: box-shadow 0.2s;
            }
            .card h2 {
                font-size: 1.3rem;
                font-weight: 600;
                margin: 0 0 18px 0;
                color: var(--primary);
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .agent-cards {
                display: flex;
                flex-direction: column;
                gap: 18px;
            }
            .agent-card {
                background: var(--card-alt);
                border-radius: 12px;
                padding: 18px 20px;
                display: flex;
                align-items: center;
                gap: 24px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                transition: box-shadow 0.2s;
            }
            .agent-card .icon {
                font-size: 2.2rem;
                color: var(--primary);
                margin-right: 10px;
            }
            .agent-card .info {
                flex: 1;
            }
            .agent-card .info .name {
                font-size: 1.1rem;
                font-weight: 600;
                margin-bottom: 4px;
            }
            .agent-card .info .status {
                font-size: 0.98rem;
                color: var(--text-muted);
            }
            .agent-card .badges {
                display: flex;
                gap: 10px;
            }
            .agent-card .badge {
                font-size: 0.95rem;
                padding: 4px 12px;
                border-radius: 12px;
                background: var(--bg-light);
                color: var(--text-muted);
            }
            .agent-card .badge.healthy { background: var(--success); color: #fff; }
            .agent-card .badge.warning { background: var(--warning); color: #222; }
            .agent-card .badge.critical { background: var(--danger); color: #fff; }
            .agent-card .badge.llm { background: var(--primary-dark); color: #fff; }
            .metrics-charts {
                display: flex;
                flex-direction: column;
                gap: 24px;
            }
            .metrics-charts .chart-card {
                background: var(--bg-light);
                border-radius: 12px;
                padding: 18px 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }
            .metrics-charts .chart-title {
                font-size: 1.05rem;
                font-weight: 600;
                color: var(--primary);
                margin-bottom: 8px;
            }
            .metrics-charts .chart {
                width: 100%;
                height: 120px;
                background: #222;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--text-muted);
                font-size: 1.2rem;
            }
            .metrics-charts .chart-card.normal .chart {
                background: var(--success);
                color: #fff;
            }
            .metrics-charts .chart-card.warning .chart {
                background: var(--warning);
                color: #222;
            }
            .metrics-charts .chart-card.critical .chart {
                background: var(--danger);
                color: #fff;
            }
            .activity-feed {
                background: var(--bg-light);
                border-radius: 12px;
                padding: 18px 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                margin-bottom: 32px;
            }
            .activity-feed .feed-title {
                font-size: 1.05rem;
                font-weight: 600;
                color: var(--primary);
                margin-bottom: 8px;
            }
            .activity-feed .feed-list {
                max-height: 260px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .activity-feed .feed-item {
                font-size: 0.98rem;
                color: var(--text-muted);
                background: #23263a;
                border-radius: 8px;
                padding: 8px 12px;
                transition: background 0.2s;
            }
            .activity-feed .feed-item.critical { background: var(--danger); color: #fff; }
            .activity-feed .feed-item.warning { background: var(--warning); color: #222; }
            .activity-feed .feed-item.success { background: var(--success); color: #fff; }
            @media (max-width: 1100px) {
                .dashboard { grid-template-columns: 1fr; }
            }
            @media (max-width: 700px) {
                .sidebar { display: none; }
                .main { margin-left: 0; }
                .dashboard { padding: 16px 4px 0 4px; }
                .topbar { padding: 12px 8px; }
            }
            .alert-feed .alert-item .ts {
                font-size: 0.92rem;
                color: var(--text-muted);
                margin-left: 8px;
            }
            
            /* Mini Dashboard Styles */
            .grafana-mini-dashboard {
                margin-top: 16px;
            }
            
            .mini-panels {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
            }
            
            .mini-panel {
                background: var(--bg-light);
                border-radius: 8px;
                padding: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: box-shadow 0.2s;
            }
            
            .mini-panel:hover {
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }
            
            .mini-panel-header {
                font-size: 0.9rem;
                color: var(--text-muted);
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            .mini-panel-value {
                font-size: 1.5rem;
                font-weight: 600;
                color: var(--primary);
                margin-bottom: 8px;
                text-align: center;
            }
            
            .mini-panel-chart {
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .mini-panel-chart canvas {
                max-width: 100%;
                height: auto;
            }
            
            @media (max-width: 768px) {
                .mini-panels {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class='sidebar'>
            <div class='logo'><i class='fa-solid fa-brain'></i> AI Agent System</div>
            <nav id='sidebar-nav'>
                <a href='#dashboard' class='active' id='nav-dashboard'><i class='fa-solid fa-gauge'></i> Dashboard</a>
                <a href='#agents' id='nav-agents'><i class='fa-solid fa-users'></i> Agents</a>
                <a href='#metrics' id='nav-metrics'><i class='fa-solid fa-chart-line'></i> Metrics</a>
                <a href='#activity' id='nav-activity'><i class='fa-solid fa-clock-rotate-left'></i> Activity</a>
                <a href='#llm' id='nav-llm'><i class='fa-solid fa-robot'></i> LLM Status</a>
                <a href='#settings' id='nav-settings'><i class='fa-solid fa-gear'></i> Settings</a>
            </nav>
            <div class='spacer'></div>
            <div class='footer'>v1.0 &copy; 2024</div>
        </div>
        <div class='main'>
            <div class='topbar'>
                <div class='status'>
                    <span class='badge critical' id='system-alert' style='display:none;'><i class='fa-solid fa-triangle-exclamation'></i> System Critical</span>
                    <span class='badge healthy' id='system-uptime'><i class='fa-solid fa-clock'></i> Uptime: <span id='uptime-value'>--</span></span>
                    <span class='badge' id='agent-count'><i class='fa-solid fa-users'></i> Agents: <span id='agent-count-value'>--</span></span>
                </div>
                <div class='actions'>
                    <button onclick='refreshDashboard()' style='background:var(--primary);color:#fff;border:none;padding:8px 18px;border-radius:8px;font-weight:600;cursor:pointer;transition:background 0.2s;'><i class='fa-solid fa-rotate'></i> Refresh</button>
                </div>
            </div>
            <div class='llm-banner' id='llm-banner'>LLM Quota Exceeded: System is using fallback AI. Please check your OpenAI plan and clear the alert to resume normal operation.</div>
            <!-- SPA Sections -->
            <div id='section-dashboard' class='spa-section'>
                <div class='dashboard' id='dashboard'>
                    <div>
                        <div class='card' id='agent-health-card'>
                            <h2><i class='fa-solid fa-users'></i> Agent Health</h2>
                            <div class='agent-cards' id='agent-cards'></div>
                        </div>
                        <div class='card' id='metrics-card'>
                            <h2><i class='fa-solid fa-chart-line'></i> System Metrics</h2>
                            <div class='grafana-mini-dashboard'>
                                <div class='mini-panels'>
                                    <div class='mini-panel'>
                                        <div class='mini-panel-header'>
                                            <i class='fa-solid fa-microchip'></i> CPU
                                        </div>
                                        <div class='mini-panel-value' id='dashboard-cpu'>--</div>
                                        <div class='mini-panel-chart'>
                                            <canvas id='dashboard-cpu-chart' width='200' height='60'></canvas>
                                        </div>
                                    </div>
                                    <div class='mini-panel'>
                                        <div class='mini-panel-header'>
                                            <i class='fa-solid fa-memory'></i> Memory
                                        </div>
                                        <div class='mini-panel-value' id='dashboard-memory'>--</div>
                                        <div class='mini-panel-chart'>
                                            <canvas id='dashboard-memory-chart' width='200' height='60'></canvas>
                                        </div>
                                    </div>
                                    <div class='mini-panel'>
                                        <div class='mini-panel-header'>
                                            <i class='fa-solid fa-hdd'></i> Disk
                                        </div>
                                        <div class='mini-panel-value' id='dashboard-disk'>--</div>
                                        <div class='mini-panel-chart'>
                                            <canvas id='dashboard-disk-chart' width='200' height='60'></canvas>
                                        </div>
                                    </div>
                                    <div class='mini-panel'>
                                        <div class='mini-panel-header'>
                                            <i class='fa-solid fa-gauge-high'></i> Load
                                        </div>
                                        <div class='mini-panel-value' id='dashboard-load'>--</div>
                                        <div class='mini-panel-chart'>
                                            <canvas id='dashboard-load-chart' width='200' height='60'></canvas>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div>
                        <div class='activity-feed' id='activity-feed'>
                            <div class='feed-title'><i class='fa-solid fa-clock-rotate-left'></i> Activity Feed</div>
                            <div class='feed-list' id='feed-list'></div>
                        </div>
                        <div class='card' id='llm-status-card'>
                            <h2><i class='fa-solid fa-robot'></i> LLM Status</h2>
                            <div id='llm-status'></div>
                        </div>
                    </div>
                </div>
            </div>
            <div id='section-agents' class='spa-section' style='display:none;'>
                <div class='card'><h2><i class='fa-solid fa-users'></i> Agents</h2><div id='agents-detail'></div></div>
            </div>
            <div id='section-metrics' class='spa-section' style='display:none;'>
                <div class='grafana-dashboard'>
                    <div class='dashboard-header'>
                        <h2><i class='fa-solid fa-chart-line'></i> System Metrics Dashboard</h2>
                        <div class='dashboard-controls'>
                            <span class='refresh-indicator' id='refresh-indicator'>Auto-refresh: ON</span>
                            <button onclick='toggleAutoRefresh()' class='btn-secondary'><i class='fa-solid fa-sync-alt'></i> Toggle Auto-refresh</button>
                        </div>
                    </div>
                    
                    <div class='grafana-grid'>
                        <!-- CPU Panel -->
                        <div class='grafana-panel'>
                            <div class='panel-header'>
                                <h3><i class='fa-solid fa-microchip'></i> CPU Usage</h3>
                                <div class='panel-controls'>
                                    <span class='panel-value' id='cpu-value'>--</span>
                                </div>
                            </div>
                            <div class='panel-content'>
                                <canvas id='cpu-chart' width='400' height='200'></canvas>
                            </div>
                        </div>
                        
                        <!-- Memory Panel -->
                        <div class='grafana-panel'>
                            <div class='panel-header'>
                                <h3><i class='fa-solid fa-memory'></i> Memory Usage</h3>
                                <div class='panel-controls'>
                                    <span class='panel-value' id='memory-value'>--</span>
                                </div>
                            </div>
                            <div class='panel-content'>
                                <canvas id='memory-chart' width='400' height='200'></canvas>
                            </div>
                        </div>
                        
                        <!-- Disk Panel -->
                        <div class='grafana-panel'>
                            <div class='panel-header'>
                                <h3><i class='fa-solid fa-hdd'></i> Disk Usage</h3>
                                <div class='panel-controls'>
                                    <span class='panel-value' id='disk-value'>--</span>
                                </div>
                            </div>
                            <div class='panel-content'>
                                <canvas id='disk-chart' width='400' height='200'></canvas>
                            </div>
                        </div>
                        
                        <!-- System Load Panel -->
                        <div class='grafana-panel'>
                            <div class='panel-header'>
                                <h3><i class='fa-solid fa-gauge-high'></i> System Load</h3>
                                <div class='panel-controls'>
                                    <span class='panel-value' id='load-value'>--</span>
                                </div>
                            </div>
                            <div class='panel-content'>
                                <canvas id='load-chart' width='400' height='200'></canvas>
                            </div>
                        </div>
                        
                        <!-- Network Panel -->
                        <div class='grafana-panel'>
                            <div class='panel-header'>
                                <h3><i class='fa-solid fa-network-wired'></i> Network I/O</h3>
                                <div class='panel-controls'>
                                    <span class='panel-value' id='network-value'>--</span>
                                </div>
                            </div>
                            <div class='panel-content'>
                                <canvas id='network-chart' width='400' height='200'></canvas>
                            </div>
                        </div>
                        
                        <!-- System Info Panel -->
                        <div class='grafana-panel'>
                            <div class='panel-header'>
                                <h3><i class='fa-solid fa-info-circle'></i> System Information</h3>
                            </div>
                            <div class='panel-content'>
                                <div id='system-info' class='info-grid'></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div id='section-activity' class='spa-section' style='display:none;'>
                <div class='card'><h2><i class='fa-solid fa-clock-rotate-left'></i> Activity</h2><div id='activity-detail'></div></div>
            </div>
            <div id='section-llm' class='spa-section' style='display:none;'>
                <div class='card'><h2><i class='fa-solid fa-robot'></i> LLM Status</h2><div id='llm-detail'></div></div>
            </div>
            <div id='section-settings' class='spa-section' style='display:none;'>
                <div class='card'><h2><i class='fa-solid fa-gear'></i> Settings</h2><div id='settings-detail'></div></div>
            </div>
        </div>
        <script>
            // --- SPA Navigation Logic ---
            const sections = ['dashboard', 'agents', 'metrics', 'activity', 'llm', 'settings'];
            function showSection(section) {
                for (const sec of sections) {
                    document.getElementById('section-' + sec).style.display = (sec === section) ? '' : 'none';
                    const nav = document.getElementById('nav-' + sec);
                    if (nav) nav.classList.toggle('active', sec === section);
                }
                // Load data for the section
                loadSectionData(section);
            }
            function handleNavClick(e) {
                if (e.target.tagName === 'A') {
                    const hash = e.target.getAttribute('href').replace('#', '');
                    showSection(hash);
                }
            }
            document.getElementById('sidebar-nav').addEventListener('click', function(e) {
                if (e.target.tagName === 'A') {
                    e.preventDefault();
                    const hash = e.target.getAttribute('href').replace('#', '');
                    window.location.hash = hash;
                    showSection(hash);
                }
            });
            window.addEventListener('hashchange', function() {
                const hash = window.location.hash.replace('#', '') || 'dashboard';
                showSection(hash);
            });
            // On load, show correct section
            window.addEventListener('DOMContentLoaded', function() {
                const hash = window.location.hash.replace('#', '') || 'dashboard';
                showSection(hash);
            });

            // --- Section Data Loading ---
            async function loadSectionData(section) {
                const container = document.getElementById(section + '-detail');
                if (!container) return;

                // Show loading state
                container.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</div>';

                try {
                    switch (section) {
                        case 'agents':
                            await loadAgentsData(container);
                            break;
                        case 'metrics':
                            await loadMetricsData(container);
                            break;
                        case 'activity':
                            await loadActivityData(container);
                            break;
                        case 'llm':
                            await loadLLMData(container);
                            break;
                        case 'settings':
                            await loadSettingsData(container);
                            break;
                    }
                } catch (error) {
                    container.innerHTML = `<div style="text-align:center;padding:20px;color:var(--danger);"><i class="fa-solid fa-exclamation-triangle"></i> Error loading data: ${error.message}</div>`;
                }
            }

            async function loadAgentsData(container) {
                const response = await fetch('/api/agents');
                const agents = await response.json();
                
                let html = '<div class="agent-cards">';
                for (const [name, agent] of Object.entries(agents)) {
                    let icon = 'fa-user-robot';
                    if (name.toLowerCase().includes('sensor')) icon = 'fa-eye';
                    if (name.toLowerCase().includes('analyzer')) icon = 'fa-brain';
                    if (name.toLowerCase().includes('remediator')) icon = 'fa-screwdriver-wrench';
                    if (name.toLowerCase().includes('communicator')) icon = 'fa-bullhorn';
                    // New agent icons
                    if (name.toLowerCase().includes('security')) icon = 'fa-shield-halved';
                    if (name.toLowerCase().includes('network')) icon = 'fa-network-wired';
                    if (name.toLowerCase().includes('application')) icon = 'fa-window-maximize';
                    if (name.toLowerCase().includes('predictive')) icon = 'fa-crystal-ball';
                    if (name.toLowerCase().includes('compliance')) icon = 'fa-clipboard-check';
                    if (name.toLowerCase().includes('backup')) icon = 'fa-database';
                    
                    let health = agent.health || 'unknown';
                    let healthClass = health;
                    let llm = agent.llm_provider || 'none';
                    let badges = `<span class='badge ${healthClass}'>${health}</span>`;
                    if (llm && llm !== 'none') badges += `<span class='badge llm'>LLM: ${llm}</span>`;
                    
                    html += `
                        <div class='agent-card'>
                            <span class='icon'><i class='fa-solid ${icon}'></i></span>
                            <div class='info'>
                                <div class='name'>${name}</div>
                                <div class='status'>Uptime: ${formatUptime(agent.uptime)} | Checks: ${agent.check_count || 0} | Errors: ${agent.error_count || 0}</div>
                            </div>
                            <div class='badges'>${badges}</div>
                        </div>
                    `;
                }
                html += '</div>';
                container.innerHTML = html;
            }

            async function loadMetricsData(container) {
                const response = await fetch('/api/metrics');
                const metrics = await response.json();
                
                let html = '<div class="metrics-charts">';
                
                // Check if we have valid metrics data
                if (metrics && typeof metrics === 'object' && !metrics.error) {
                    // CPU Metrics
                    if (metrics.cpu && metrics.cpu.usage_percent !== undefined) {
                        const cpuUsage = metrics.cpu.usage_percent;
                        const cpuClass = cpuUsage > 90 ? 'critical' : cpuUsage > 75 ? 'warning' : 'normal';
                        html += `<div class='chart-card ${cpuClass}'><div class='chart-title'>CPU Usage</div><div class='chart'>${cpuUsage.toFixed(1)}%</div></div>`;
                    }
                    
                    // Memory Metrics
                    if (metrics.memory && metrics.memory.usage_percent !== undefined) {
                        const memUsage = metrics.memory.usage_percent;
                        const memClass = memUsage > 95 ? 'critical' : memUsage > 85 ? 'warning' : 'normal';
                        html += `<div class='chart-card ${memClass}'><div class='chart-title'>Memory Usage</div><div class='chart'>${memUsage.toFixed(1)}%</div></div>`;
                    }
                    
                    // Disk Metrics
                    if (metrics.disk) {
                        for (const [path, diskData] of Object.entries(metrics.disk)) {
                            if (diskData.usage_percent !== undefined) {
                                const diskUsage = diskData.usage_percent;
                                const diskClass = diskUsage > 95 ? 'critical' : diskUsage > 85 ? 'warning' : 'normal';
                                html += `<div class='chart-card ${diskClass}'><div class='chart-title'>Disk Usage (${path})</div><div class='chart'>${diskUsage.toFixed(1)}%</div></div>`;
                            }
                        }
                    }
                    
                    // Performance Metrics
                    if (metrics.performance && metrics.performance.system_load_score !== undefined) {
                        const loadScore = metrics.performance.system_load_score;
                        const healthStatus = metrics.performance.health_status || 'unknown';
                        const loadClass = healthStatus === 'critical' ? 'critical' : healthStatus === 'warning' ? 'warning' : 'normal';
                        html += `<div class='chart-card ${loadClass}'><div class='chart-title'>System Load</div><div class='chart'>${loadScore.toFixed(1)}% (${healthStatus})</div></div>`;
                    }
                    
                    // Network Metrics (if available)
                    if (metrics.network) {
                        for (const [interface, netData] of Object.entries(metrics.network)) {
                            if (netData.bytes_sent !== undefined && netData.bytes_recv !== undefined) {
                                html += `<div class='chart-card'><div class='chart-title'>Network (${interface})</div><div class='chart'>↑ ${formatBytes(netData.bytes_sent)} ↓ ${formatBytes(netData.bytes_recv)}</div></div>`;
                            }
                        }
                    }
                    
                    // System Info
                    if (metrics.system_info) {
                        html += `<div class='chart-card'><div class='chart-title'>System Info</div><div class='chart'>${metrics.system_info.platform} | ${metrics.system_info.hostname}</div></div>`;
                    }
                    
                    // Timestamp
                    if (metrics.timestamp) {
                        const timestamp = new Date(metrics.timestamp).toLocaleString();
                        html += `<div class='chart-card'><div class='chart-title'>Last Updated</div><div class='chart'>${timestamp}</div></div>`;
                    }
                } else {
                    // No metrics available
                    html += `<div class='chart-card'><div class='chart-title'>No Metrics Available</div><div class='chart'>${metrics.error || 'Metrics not collected yet'}</div></div>`;
                }
                
                html += '</div>';
                container.innerHTML = html;
            }

            async function loadActivityData(container) {
                const response = await fetch('/api/activity?limit=20');
                const activity = await response.json();
                
                let html = '<div class="activity-feed">';
                if (activity && Array.isArray(activity) && activity.length > 0) {
                    for (const item of activity) {
                        let cls = 'feed-item';
                        if (item.severity === 'critical') cls += ' critical';
                        if (item.severity === 'warning') cls += ' warning';
                        if (item.severity === 'success') cls += ' success';
                        html += `<div class='${cls}'>${item.timestamp ? `<b>${item.timestamp.split('T')[1].slice(0,8)}</b> ` : ''}${item.description || item.message || 'Event'}</div>`;
                    }
                } else {
                    html += '<div class="feed-item">No recent activity</div>';
                }
                html += '</div>';
                container.innerHTML = html;
            }

            async function loadLLMData(container) {
                const [llmStatus, llmAgents] = await Promise.all([
                    fetch('/api/llm_status').then(r => r.json()),
                    fetch('/api/llm_agents').then(r => r.json())
                ]);
                
                let html = '';
                if (llmStatus.llm_quota_alert_active) {
                    html += `<div class='feed-item critical'><i class='fa-solid fa-triangle-exclamation'></i> ${llmStatus.llm_quota_alert_message || 'LLM Quota Exceeded'}</div>`;
                } else {
                    html += `<div class='feed-item success'><i class='fa-solid fa-check-circle'></i> LLMs are healthy and available.</div>`;
                }
                if (llmAgents && Object.keys(llmAgents).length > 0) {
                    html += `<div style='margin-top:10px;'><b>LLM Providers:</b></div>`;
                    for (const [agent, provider] of Object.entries(llmAgents)) {
                        html += `<div class='feed-item'><b>${agent}:</b> ${provider}</div>`;
                    }
                }
                container.innerHTML = html;
            }

            async function loadSettingsData(container) {
                const response = await fetch('/api/config');
                const config = await response.json();
                
                let html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">';
                
                // Thresholds
                html += '<div><h3>Thresholds</h3>';
                if (config.thresholds) {
                    for (const [key, value] of Object.entries(config.thresholds)) {
                        html += `<div style="margin:5px 0;"><b>${key}:</b> ${value}</div>`;
                    }
                }
                html += '</div>';
                
                // Agent Config
                html += '<div><h3>Agent Configuration</h3>';
                if (config.agents) {
                    for (const [name, agent] of Object.entries(config.agents)) {
                        html += `<div style="margin:5px 0;"><b>${name}:</b> ${agent.check_interval}s interval</div>`;
                    }
                }
                html += '</div>';
                
                // System Config
                html += '<div><h3>System Configuration</h3>';
                html += `<div style="margin:5px 0;"><b>Persistence:</b> ${config.persistence_enabled ? 'Enabled' : 'Disabled'}</div>`;
                html += `<div style="margin:5px 0;"><b>Auto Healing:</b> ${config.auto_healing_enabled ? 'Enabled' : 'Disabled'}</div>`;
                html += `<div style="margin:5px 0;"><b>Plugins:</b> ${config.plugins_enabled ? 'Enabled' : 'Disabled'}</div>`;
                html += '</div>';
                
                // LLM Config
                html += '<div><h3>LLM Configuration</h3>';
                if (config.gpt) {
                    html += `<div style="margin:5px 0;"><b>Model:</b> ${config.gpt.model}</div>`;
                    html += `<div style="margin:5px 0;"><b>Max Tokens:</b> ${config.gpt.max_tokens}</div>`;
                    html += `<div style="margin:5px 0;"><b>Temperature:</b> ${config.gpt.temperature}</div>`;
                }
                html += '</div>';
                
                html += '</div>';
                container.innerHTML = html;
            }

            // --- Dashboard Data Fetching & Rendering ---
            async function fetchDashboardData() {
                try {
                    // Fetch system info
                    const systemResponse = await fetch('/api/system');
                    const systemData = await systemResponse.json();
                    
                    // Update system status
                    if (systemData.uptime !== undefined) {
                        document.getElementById('uptime-value').textContent = formatUptime(systemData.uptime);
                    }
                    if (systemData.agent_count !== undefined) {
                        document.getElementById('agent-count-value').textContent = systemData.agent_count;
                    }
                    
                    // Fetch and update metrics
                    const metricsResponse = await fetch('/api/metrics');
                    const metrics = await metricsResponse.json();
                    
                    if (metrics && typeof metrics === 'object' && !metrics.error) {
                        updateDashboardCharts(metrics);
                    }
                    
                    // Fetch agents
                    const agentsResponse = await fetch('/api/agents');
                    const agents = await agentsResponse.json();
                    
                    // Update agent cards
                    const agentCardsContainer = document.getElementById('agent-cards');
                    if (agentCardsContainer) {
                        let html = '';
                        for (const [name, agent] of Object.entries(agents)) {
                            let icon = 'fa-user-robot';
                            if (name.toLowerCase().includes('sensor')) icon = 'fa-eye';
                            if (name.toLowerCase().includes('analyzer')) icon = 'fa-brain';
                            if (name.toLowerCase().includes('remediator')) icon = 'fa-screwdriver-wrench';
                            if (name.toLowerCase().includes('communicator')) icon = 'fa-bullhorn';
                            // New agent icons
                            if (name.toLowerCase().includes('security')) icon = 'fa-shield-halved';
                            if (name.toLowerCase().includes('network')) icon = 'fa-network-wired';
                            if (name.toLowerCase().includes('application')) icon = 'fa-window-maximize';
                            if (name.toLowerCase().includes('predictive')) icon = 'fa-crystal-ball';
                            if (name.toLowerCase().includes('compliance')) icon = 'fa-clipboard-check';
                            if (name.toLowerCase().includes('backup')) icon = 'fa-database';
                            
                            let health = agent.health || 'unknown';
                            let healthClass = health;
                            let llm = agent.llm_provider || 'none';
                            let badges = `<span class='badge ${healthClass}'>${health}</span>`;
                            if (llm && llm !== 'none') badges += `<span class='badge llm'>LLM: ${llm}</span>`;
                            
                            html += `
                                <div class='agent-card'>
                                    <span class='icon'><i class='fa-solid ${icon}'></i></span>
                                    <div class='info'>
                                        <div class='name'>${name}</div>
                                        <div class='status'>Uptime: ${formatUptime(agent.uptime)} | Checks: ${agent.check_count || 0} | Errors: ${agent.error_count || 0}</div>
                                    </div>
                                    <div class='badges'>${badges}</div>
                                </div>
                            `;
                        }
                        agentCardsContainer.innerHTML = html;
                    }
                    
                    // Fetch activity
                    const activityResponse = await fetch('/api/activity?limit=10');
                    const activity = await activityResponse.json();
                    
                    // Update activity feed
                    const feedList = document.getElementById('feed-list');
                    if (feedList) {
                        let html = '';
                        if (activity && Array.isArray(activity) && activity.length > 0) {
                            for (const item of activity) {
                                let cls = 'feed-item';
                                if (item.severity === 'critical') cls += ' critical';
                                if (item.severity === 'warning') cls += ' warning';
                                if (item.severity === 'success') cls += ' success';
                                html += `<div class='${cls}'>${item.timestamp ? `<b>${item.timestamp.split('T')[1].slice(0,8)}</b> ` : ''}${item.description || item.message || 'Event'}</div>`;
                            }
                        } else {
                            html += '<div class="feed-item">No recent activity</div>';
                        }
                        feedList.innerHTML = html;
                    }
                    
                    // Fetch LLM status
                    const llmResponse = await fetch('/api/llm_status');
                    const llmData = await llmResponse.json();
                    
                    // Update LLM status
                    const llmStatusContainer = document.getElementById('llm-status');
                    if (llmStatusContainer) {
                        let html = '';
                        if (llmData.ollama && llmData.ollama.available) {
                            html += `<div style='color:var(--success);margin-bottom:8px;'><i class='fa-solid fa-check-circle'></i> Ollama Available</div>`;
                            if (llmData.ollama.models && llmData.ollama.models.length > 0) {
                                html += `<div style='font-size:0.9rem;color:var(--text-muted);'>Models: ${llmData.ollama.models.join(', ')}</div>`;
                            }
                        } else {
                            html += `<div style='color:var(--danger);'><i class='fa-solid fa-times-circle'></i> Ollama Not Available</div>`;
                        }
                        llmStatusContainer.innerHTML = html;
                    }
                    
                } catch (error) {
                    console.error('Error fetching dashboard data:', error);
                }
            }
            
            // Initialize dashboard charts on page load
            window.addEventListener('DOMContentLoaded', function() {
                setTimeout(() => {
                    initializeDashboardCharts();
                    fetchDashboardData();
                }, 100);
            });
            
            fetchDashboardData();
            setInterval(fetchDashboardData, 10000);

            // Dashboard mini charts
            let dashboardCharts = {};
            
            // Initialize dashboard mini charts
            function initializeDashboardCharts() {
                const miniChartOptions = {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 500,
                        easing: 'easeInOutQuart'
                    },
                    scales: {
                        x: {
                            display: false
                        },
                        y: {
                            display: false
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    elements: {
                        point: {
                            radius: 0
                        },
                        line: {
                            tension: 0.4
                        }
                    }
                };
                
                // Dashboard CPU Chart
                const dashboardCpuCtx = document.getElementById('dashboard-cpu-chart');
                if (dashboardCpuCtx) {
                    dashboardCharts.cpu = new Chart(dashboardCpuCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'CPU',
                                data: [],
                                borderColor: '#6366f1',
                                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                                borderWidth: 2,
                                fill: true
                            }]
                        },
                        options: miniChartOptions
                    });
                }
                
                // Dashboard Memory Chart
                const dashboardMemoryCtx = document.getElementById('dashboard-memory-chart');
                if (dashboardMemoryCtx) {
                    dashboardCharts.memory = new Chart(dashboardMemoryCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Memory',
                                data: [],
                                borderColor: '#8b5cf6',
                                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                                borderWidth: 2,
                                fill: true
                            }]
                        },
                        options: miniChartOptions
                    });
                }
                
                // Dashboard Disk Chart
                const dashboardDiskCtx = document.getElementById('dashboard-disk-chart');
                if (dashboardDiskCtx) {
                    dashboardCharts.disk = new Chart(dashboardDiskCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Disk',
                                data: [],
                                borderColor: '#f59e0b',
                                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                borderWidth: 2,
                                fill: true
                            }]
                        },
                        options: miniChartOptions
                    });
                }
                
                // Dashboard Load Chart
                const dashboardLoadCtx = document.getElementById('dashboard-load-chart');
                if (dashboardLoadCtx) {
                    dashboardCharts.load = new Chart(dashboardLoadCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Load',
                                data: [],
                                borderColor: '#10b981',
                                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                borderWidth: 2,
                                fill: true
                            }]
                        },
                        options: miniChartOptions
                    });
                }
            }
            
            // Update dashboard mini charts
            function updateDashboardCharts(metrics) {
                const now = new Date().toLocaleTimeString();
                
                // Update CPU
                if (dashboardCharts.cpu && metrics.cpu && metrics.cpu.usage_percent !== undefined) {
                    const cpuUsage = metrics.cpu.usage_percent;
                    dashboardCharts.cpu.data.labels.push(now);
                    dashboardCharts.cpu.data.datasets[0].data.push(cpuUsage);
                    
                    if (dashboardCharts.cpu.data.labels.length > 10) {
                        dashboardCharts.cpu.data.labels.shift();
                        dashboardCharts.cpu.data.datasets[0].data.shift();
                    }
                    
                    dashboardCharts.cpu.update('none');
                    document.getElementById('dashboard-cpu').textContent = cpuUsage.toFixed(1) + '%';
                }
                
                // Update Memory
                if (dashboardCharts.memory && metrics.memory && metrics.memory.usage_percent !== undefined) {
                    const memUsage = metrics.memory.usage_percent;
                    dashboardCharts.memory.data.labels.push(now);
                    dashboardCharts.memory.data.datasets[0].data.push(memUsage);
                    
                    if (dashboardCharts.memory.data.labels.length > 10) {
                        dashboardCharts.memory.data.labels.shift();
                        dashboardCharts.memory.data.datasets[0].data.shift();
                    }
                    
                    dashboardCharts.memory.update('none');
                    document.getElementById('dashboard-memory').textContent = memUsage.toFixed(1) + '%';
                }
                
                // Update Disk
                if (dashboardCharts.disk && metrics.disk) {
                    const diskData = Object.values(metrics.disk)[0];
                    if (diskData && diskData.usage_percent !== undefined) {
                        const diskUsage = diskData.usage_percent;
                        dashboardCharts.disk.data.labels.push(now);
                        dashboardCharts.disk.data.datasets[0].data.push(diskUsage);
                        
                        if (dashboardCharts.disk.data.labels.length > 10) {
                            dashboardCharts.disk.data.labels.shift();
                            dashboardCharts.disk.data.datasets[0].data.shift();
                        }
                        
                        dashboardCharts.disk.update('none');
                        document.getElementById('dashboard-disk').textContent = diskUsage.toFixed(1) + '%';
                    }
                }
                
                // Update Load
                if (dashboardCharts.load && metrics.performance && metrics.performance.system_load_score !== undefined) {
                    const loadScore = metrics.performance.system_load_score;
                    dashboardCharts.load.data.labels.push(now);
                    dashboardCharts.load.data.datasets[0].data.push(loadScore);
                    
                    if (dashboardCharts.load.data.labels.length > 10) {
                        dashboardCharts.load.data.labels.shift();
                        dashboardCharts.load.data.datasets[0].data.shift();
                    }
                    
                    dashboardCharts.load.update('none');
                    document.getElementById('dashboard-load').textContent = loadScore.toFixed(1) + '%';
                }
            }
            
            // Helper functions
            function formatUptime(seconds) {
                if (!seconds || isNaN(seconds)) return '--';
                let s = Math.floor(seconds);
                let m = Math.floor(s / 60); s = s % 60;
                let h = Math.floor(m / 60); m = m % 60;
                let d = Math.floor(h / 24); h = h % 24;
                let str = '';
                if (d > 0) str += d + 'd ';
                if (h > 0) str += h + 'h ';
                if (m > 0) str += m + 'm ';
                str += s + 's';
                return str;
            }
            
            function formatBytes(bytes) {
                if (!bytes || isNaN(bytes)) return '--';
                if (bytes < 1024) return bytes + ' B';
                let kb = bytes / 1024;
                if (kb < 1024) return kb.toFixed(1) + ' KB';
                let mb = kb / 1024;
                if (mb < 1024) return mb.toFixed(1) + ' MB';
                let gb = mb / 1024;
                return gb.toFixed(2) + ' GB';
            }
            
            // Chart instances for metrics section
            let charts = {};
            let autoRefresh = true;
            let refreshInterval;
            
            // Initialize charts for metrics section
            function initializeCharts() {
                const chartOptions = {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 750,
                        easing: 'easeInOutQuart'
                    },
                    scales: {
                        x: {
                            display: true,
                            grid: {
                                color: 'rgba(255,255,255,0.1)'
                            },
                            ticks: {
                                color: '#a0aec0',
                                maxTicksLimit: 8
                            }
                        },
                        y: {
                            display: true,
                            grid: {
                                color: 'rgba(255,255,255,0.1)'
                            },
                            ticks: {
                                color: '#a0aec0',
                                callback: function(value) {
                                    return value + '%';
                                }
                            },
                            min: 0,
                            max: 100
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    elements: {
                        point: {
                            radius: 0
                        },
                        line: {
                            tension: 0.4
                        }
                    }
                };
                
                // CPU Chart
                const cpuCtx = document.getElementById('cpu-chart');
                if (cpuCtx) {
                    charts.cpu = new Chart(cpuCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'CPU Usage',
                                data: [],
                                borderColor: '#6366f1',
                                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                                borderWidth: 2,
                                fill: true
                            }]
                        },
                        options: chartOptions
                    });
                }
                
                // Memory Chart
                const memoryCtx = document.getElementById('memory-chart');
                if (memoryCtx) {
                    charts.memory = new Chart(memoryCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Memory Usage',
                                data: [],
                                borderColor: '#8b5cf6',
                                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                                borderWidth: 2,
                                fill: true
                            }]
                        },
                        options: chartOptions
                    });
                }
                
                // Disk Chart
                const diskCtx = document.getElementById('disk-chart');
                if (diskCtx) {
                    charts.disk = new Chart(diskCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Disk Usage',
                                data: [],
                                borderColor: '#f59e0b',
                                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                borderWidth: 2,
                                fill: true
                            }]
                        },
                        options: chartOptions
                    });
                }
                
                // Load Chart
                const loadCtx = document.getElementById('load-chart');
                if (loadCtx) {
                    charts.load = new Chart(loadCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'System Load',
                                data: [],
                                borderColor: '#10b981',
                                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                borderWidth: 2,
                                fill: true
                            }]
                        },
                        options: chartOptions
                    });
                }
                
                // Network Chart
                const networkCtx = document.getElementById('network-chart');
                if (networkCtx) {
                    charts.network = new Chart(networkCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Network In',
                                data: [],
                                borderColor: '#3b82f6',
                                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                borderWidth: 2,
                                fill: false
                            }, {
                                label: 'Network Out',
                                data: [],
                                borderColor: '#ef4444',
                                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                borderWidth: 2,
                                fill: false
                            }]
                        },
                        options: {
                            ...chartOptions,
                            scales: {
                                ...chartOptions.scales,
                                y: {
                                    ...chartOptions.scales.y,
                                    ticks: {
                                        color: '#a0aec0',
                                        callback: function(value) {
                                            return formatBytes(value);
                                        }
                                    }
                                }
                            }
                        }
                    });
                }
            }
            
            // Update charts with new data
            function updateCharts(metrics) {
                const now = new Date().toLocaleTimeString();
                
                // Update CPU chart
                if (charts.cpu && metrics.cpu && metrics.cpu.usage_percent !== undefined) {
                    const cpuUsage = metrics.cpu.usage_percent;
                    charts.cpu.data.labels.push(now);
                    charts.cpu.data.datasets[0].data.push(cpuUsage);
                    
                    // Keep only last 20 data points
                    if (charts.cpu.data.labels.length > 20) {
                        charts.cpu.data.labels.shift();
                        charts.cpu.data.datasets[0].data.shift();
                    }
                    
                    charts.cpu.update('none');
                    document.getElementById('cpu-value').textContent = cpuUsage.toFixed(1) + '%';
                }
                
                // Update Memory chart
                if (charts.memory && metrics.memory && metrics.memory.usage_percent !== undefined) {
                    const memUsage = metrics.memory.usage_percent;
                    charts.memory.data.labels.push(now);
                    charts.memory.data.datasets[0].data.push(memUsage);
                    
                    if (charts.memory.data.labels.length > 20) {
                        charts.memory.data.labels.shift();
                        charts.memory.data.datasets[0].data.shift();
                    }
                    
                    charts.memory.update('none');
                    document.getElementById('memory-value').textContent = memUsage.toFixed(1) + '%';
                }
                
                // Update Disk chart (use first disk found)
                if (charts.disk && metrics.disk) {
                    const diskData = Object.values(metrics.disk)[0];
                    if (diskData && diskData.usage_percent !== undefined) {
                        const diskUsage = diskData.usage_percent;
                        charts.disk.data.labels.push(now);
                        charts.disk.data.datasets[0].data.push(diskUsage);
                        
                        if (charts.disk.data.labels.length > 20) {
                            charts.disk.data.labels.shift();
                            charts.disk.data.datasets[0].data.shift();
                        }
                        
                        charts.disk.update('none');
                        document.getElementById('disk-value').textContent = diskUsage.toFixed(1) + '%';
                    }
                }
                
                // Update Load chart
                if (charts.load && metrics.performance && metrics.performance.system_load_score !== undefined) {
                    const loadScore = metrics.performance.system_load_score;
                    charts.load.data.labels.push(now);
                    charts.load.data.datasets[0].data.push(loadScore);
                    
                    if (charts.load.data.labels.length > 20) {
                        charts.load.data.labels.shift();
                        charts.load.data.datasets[0].data.shift();
                    }
                    
                    charts.load.update('none');
                    document.getElementById('load-value').textContent = loadScore.toFixed(1) + '%';
                }
                
                // Update Network chart
                if (charts.network && metrics.network) {
                    const netData = Object.values(metrics.network)[0];
                    if (netData && netData.bytes_recv !== undefined && netData.bytes_sent !== undefined) {
                        charts.network.data.labels.push(now);
                        charts.network.data.datasets[0].data.push(netData.bytes_recv);
                        charts.network.data.datasets[1].data.push(netData.bytes_sent);
                        
                        if (charts.network.data.labels.length > 20) {
                            charts.network.data.labels.shift();
                            charts.network.data.datasets[0].data.shift();
                            charts.network.data.datasets[1].data.shift();
                        }
                        
                        charts.network.update('none');
                        document.getElementById('network-value').textContent = formatBytes(netData.bytes_recv);
                    }
                }
            }
            
            // Update system info
            function updateSystemInfo(metrics) {
                const infoContainer = document.getElementById('system-info');
                if (!infoContainer || !metrics.system_info) return;
                
                const info = metrics.system_info;
                infoContainer.innerHTML = `
                    <div class='info-item'>
                        <span class='info-label'>Platform:</span>
                        <span class='info-value'>${info.platform || 'Unknown'}</span>
                    </div>
                    <div class='info-item'>
                        <span class='info-label'>Hostname:</span>
                        <span class='info-value'>${info.hostname || 'Unknown'}</span>
                    </div>
                    <div class='info-item'>
                        <span class='info-label'>Architecture:</span>
                        <span class='info-value'>${info.architecture || 'Unknown'}</span>
                    </div>
                    <div class='info-item'>
                        <span class='info-label'>Processor:</span>
                        <span class='info-value'>${info.processor || 'Unknown'}</span>
                    </div>
                    <div class='info-item'>
                        <span class='info-label'>Uptime:</span>
                        <span class='info-value'>${formatUptime(info.uptime || 0)}</span>
                    </div>
                    <div class='info-item'>
                        <span class='info-label'>Last Update:</span>
                        <span class='info-value'>${metrics.timestamp ? new Date(metrics.timestamp).toLocaleTimeString() : 'Unknown'}</span>
                    </div>
                `;
            }
            
            // Toggle auto-refresh
            function toggleAutoRefresh() {
                autoRefresh = !autoRefresh;
                const indicator = document.getElementById('refresh-indicator');
                indicator.textContent = `Auto-refresh: ${autoRefresh ? 'ON' : 'OFF'}`;
                
                if (autoRefresh) {
                    startAutoRefresh();
                } else {
                    stopAutoRefresh();
                }
            }
            
            // Start auto-refresh
            function startAutoRefresh() {
                if (refreshInterval) clearInterval(refreshInterval);
                refreshInterval = setInterval(loadMetricsData, 2000);
            }
            
            // Stop auto-refresh
            function stopAutoRefresh() {
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                    refreshInterval = null;
                }
            }
            
            // Load metrics data
            async function loadMetricsData() {
                try {
                    const response = await fetch('/api/metrics');
                    const metrics = await response.json();
                    
                    if (metrics && typeof metrics === 'object' && !metrics.error) {
                        updateCharts(metrics);
                        updateSystemInfo(metrics);
                    } else {
                        console.error('No metrics available:', metrics.error || 'Metrics not collected yet');
                    }
                } catch (error) {
                    console.error('Failed to load metrics:', error);
                }
            }
            
            // Initialize when metrics section is shown
            let metricsInitialized = false;
            const originalLoadSectionData = loadSectionData;
            loadSectionData = function(section) {
                originalLoadSectionData(section);
                
                if (section === 'metrics' && !metricsInitialized) {
                    setTimeout(() => {
                        initializeCharts();
                        loadMetricsData();
                        startAutoRefresh();
                        metricsInitialized = true;
                    }, 100);
                } else if (section !== 'metrics' && metricsInitialized) {
                    stopAutoRefresh();
                }
            };
        </script>
    </body>
    </html>
    """


@app.get("/api/system")
async def get_system_info():
    """Get comprehensive system information."""
    try:
        return orchestrator.get_system_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents")
async def get_agents():
    """Get status of all agents."""
    try:
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
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/metrics")
async def get_current_metrics():
    """Get current system metrics."""
    try:
        # Get metrics from sensor agent if available
        sensor_agent = orchestrator.agents.get("sensor")
        if sensor_agent and hasattr(sensor_agent, "get_current_metrics"):
            return sensor_agent.get_current_metrics() or {}
        return {"error": "Metrics not available"}
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

        await orchestrator.send_command(command, target)
        return {"status": "success", "message": f"Command '{command}' sent to {target}"}
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
        # This is a simplified implementation
        # In production, you'd want more sophisticated config management
        return {
            "status": "success",
            "message": "Configuration update not implemented yet",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        return {
            "status": "healthy" if system_running else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "system_health": orchestrator.system_health,
            "agents_running": sum(
                1 for agent in orchestrator.agents.values() if agent.running
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs")
async def get_logs(limit: int = 100):
    """Get recent system logs."""
    try:
        # In a real implementation, you'd read from the log file
        # For now, return a placeholder
        return {
            "message": "Log retrieval not implemented",
            "log_file": config.logging.log_file,
        }
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
    log_pattern = re.compile(r"\[(.*?)\] (WARNING|ERROR|CRITICAL)\s+([\S]+): (.+)")
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
                alert_lines.append({
                    "timestamp": timestamp,
                    "severity": severity,
                    "agent": agent_name,
                    "emoji": emoji,
                    "message": message.strip(),
                })
                if len(alert_lines) >= limit:
                    break
        # Return in chronological order (oldest first)
        return list(reversed(alert_lines))
    except Exception as e:
        return {"error": str(e)}


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
    """Start the web interface."""
    if not config.web_interface_enabled:
        print("Web interface is disabled in configuration")
        return

    print(f"🌐 Starting web interface on http://{config.web_host}:{config.web_port}")
    print(f"📊 Dashboard: http://{config.web_host}:{config.web_port}/")
    print(f"🔧 API Docs: http://{config.web_host}:{config.web_port}/docs")

    uvicorn.run(app, host=config.web_host, port=config.web_port, log_level="info")


if __name__ == "__main__":
    start_web_interface()
