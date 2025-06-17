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

from system_orchestrator import orchestrator
from utils.message_bus import message_bus
from config import config

# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Monitoring System",
    description="GPT-driven system monitoring and self-healing",
    version="1.0.0"
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
    <html>
    <head>
        <title>Multi-Agent Monitoring System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .status-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .status-card h3 { margin-top: 0; color: #2c3e50; }
            .health-healthy { color: #27ae60; }
            .health-warning { color: #f39c12; }
            .health-critical { color: #e74c3c; }
            .health-unknown { color: #95a5a6; }
            .button { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
            .button:hover { background: #2980b9; }
            .button.danger { background: #e74c3c; }
            .button.danger:hover { background: #c0392b; }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
            .metric { background: #ecf0f1; padding: 10px; border-radius: 4px; text-align: center; }
            .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
            .metric-label { font-size: 12px; color: #7f8c8d; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Multi-Agent Monitoring System</h1>
                <p>GPT-driven system monitoring and automated self-healing</p>
            </div>
            
            <div class="status-grid">
                <div class="status-card">
                    <h3>System Status</h3>
                    <div id="system-status">Loading...</div>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value" id="uptime">-</div>
                            <div class="metric-label">Uptime</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value" id="agents-running">-</div>
                            <div class="metric-label">Agents Running</div>
                        </div>
                    </div>
                </div>
                
                <div class="status-card">
                    <h3>Agent Health</h3>
                    <div id="agent-health">Loading...</div>
                </div>
                
                <div class="status-card">
                    <h3>System Metrics</h3>
                    <div id="system-metrics">Loading...</div>
                </div>
                
                <div class="status-card">
                    <h3>Actions</h3>
                    <button class="button" onclick="refreshData()">🔄 Refresh</button>
                    <button class="button" onclick="sendCommand('status')">📊 Status Check</button>
                    <button class="button" onclick="sendCommand('health_check')">🏥 Health Check</button>
                    <button class="button danger" onclick="sendCommand('restart')">🔄 Restart System</button>
                </div>
            </div>
            
            <div class="status-card">
                <h3>Recent Activity</h3>
                <div id="recent-activity">Loading...</div>
            </div>
            <div class="status-card">
                <h3>Live Agent Messages</h3>
                <div id="live-messages">Loading...</div>
            </div>
            <div class="status-card">
                <h3>LLM Status</h3>
                <div id="llm-status">Loading...</div>
            </div>
            <div class="status-card">
                <h3>Agent Recommendations</h3>
                <div id="agent-recommendations">Loading...</div>
            </div>
        </div>
        
        <script>
            async function refreshData() {
                try {
                    const [systemInfo, agentHealth, metrics, activity, messages, llmStatus, analysis, remediation, llmAgents] = await Promise.all([
                        fetch('/api/system').then(r => r.json()),
                        fetch('/api/agents').then(r => r.json()),
                        fetch('/api/metrics').then(r => r.json()),
                        fetch('/api/activity').then(r => r.json()),
                        fetch('/api/messages/recent').then(r => r.json()),
                        fetch('/api/llm_status').then(r => r.json()),
                        fetch('/api/analysis').then(r => r.json()),
                        fetch('/api/remediation').then(r => r.json()),
                        fetch('/api/llm_agents').then(r => r.json())
                    ]);
                    
                    updateSystemStatus(systemInfo);
                    updateAgentHealth(agentHealth, llmAgents, llmStatus);
                    updateSystemMetrics(metrics);
                    updateRecentActivity(activity);
                    updateLiveMessages(messages);
                    updateLLMStatus(llmStatus);
                    updateAgentRecommendations(analysis, remediation);
                } catch (error) {
                    console.error('Error refreshing data:', error);
                }
            }
            
            function updateSystemStatus(data) {
                const statusDiv = document.getElementById('system-status');
                const uptimeDiv = document.getElementById('uptime');
                const agentsDiv = document.getElementById('agents-running');
                
                const healthClass = `health-${data.system_health || 'unknown'}`;
                statusDiv.innerHTML = `<span class="${healthClass}">● ${data.system_health || 'Unknown'}</span>`;
                
                const uptimeHours = Math.floor(data.uptime / 3600);
                const uptimeMinutes = Math.floor((data.uptime % 3600) / 60);
                uptimeDiv.textContent = `${uptimeHours}h ${uptimeMinutes}m`;
                
                agentsDiv.textContent = `${data.running_agents || 0}/${data.total_agents || 0}`;
            }
            
            function updateAgentHealth(data, llmAgents, llmStatus) {
                const div = document.getElementById('agent-health');
                let html = '';
                for (const [name, agent] of Object.entries(data)) {
                    const healthClass = `health-${agent.health || 'unknown'}`;
                    let llm = llmAgents && llmAgents[name] ? llmAgents[name] : 'none';
                    let llmDisplay = '';
                    if (llm === 'openai') {
                        llmDisplay = `<span title='OpenAI' style='color:${llmStatus.openai === 'online' ? '#27ae60' : '#e74c3c'}'>🧠 OpenAI${llmStatus.openai !== 'online' ? ' (offline)' : ''}</span>`;
                    } else if (llm === 'gemini') {
                        llmDisplay = `<span title='Gemini' style='color:${llmStatus.gemini === 'online' ? '#27ae60' : '#e74c3c'}'>🔮 Gemini${llmStatus.gemini !== 'online' ? ' (offline)' : ''}</span>`;
                    } else {
                        llmDisplay = `<span style='color:#95a5a6'>None</span>`;
                    }
                    html += `<div><strong>${name}:</strong> <span class="${healthClass}">${agent.health || 'Unknown'}</span> | LLM: ${llmDisplay}</div>`;
                }
                div.innerHTML = html;
            }
            
            function updateSystemMetrics(data) {
                const div = document.getElementById('system-metrics');
                let html = '';
                
                if (data.cpu) {
                    html += `<div><strong>CPU:</strong> ${data.cpu.usage_percent?.toFixed(1) || 'N/A'}%</div>`;
                }
                if (data.memory) {
                    html += `<div><strong>Memory:</strong> ${data.memory.usage_percent?.toFixed(1) || 'N/A'}%</div>`;
                }
                if (data.disk) {
                    for (const [path, disk] of Object.entries(data.disk)) {
                        html += `<div><strong>Disk ${path}:</strong> ${disk.usage_percent?.toFixed(1) || 'N/A'}%</div>`;
                    }
                }
                
                div.innerHTML = html;
            }
            
            function updateRecentActivity(data) {
                const div = document.getElementById('recent-activity');
                let html = '';
                
                for (const event of data.slice(0, 10)) {
                    html += `<div>${event.timestamp}: ${event.description}</div>`;
                }
                
                div.innerHTML = html;
            }
            
            function updateLiveMessages(data) {
                const div = document.getElementById('live-messages');
                let html = '';
                for (const msg of data) {
                    const agentRole = msg.sender && msg.sender.toLowerCase().includes('sensor') ? 'sensor' :
                                      msg.sender && msg.sender.toLowerCase().includes('analyzer') ? 'analyzer' :
                                      msg.sender && msg.sender.toLowerCase().includes('remediator') ? 'remediator' :
                                      msg.sender && msg.sender.toLowerCase().includes('communicator') ? 'communicator' :
                                      msg.sender && msg.sender.toLowerCase().includes('orchestrator') ? 'orchestrator' : 'unknown';
                    let summary = '';
                    if (typeof msg.content === 'string') summary = msg.content;
                    else if (msg.content && msg.content.info) summary = msg.content.info;
                    else if (msg.content && msg.content.message) summary = msg.content.message;
                    else summary = JSON.stringify(msg.content);
                    html += `<div>[${msg.timestamp}] <b>${msg.sender} (${agentRole})</b> <span style='color:#888;'>[${msg.type}]</span>: ${summary}</div>`;
                }
                div.innerHTML = html;
            }
            
            function updateLLMStatus(data) {
                const div = document.getElementById('llm-status');
                let html = '';
                html += `<div><strong>ChatGPT (OpenAI):</strong> <span style='color:${data.openai === 'online' ? '#27ae60' : '#e74c3c'}'>${data.openai}</span></div>`;
                html += `<div><strong>Gemini (Google):</strong> <span style='color:${data.gemini === 'online' ? '#27ae60' : '#e74c3c'}'>${data.gemini}</span></div>`;
                div.innerHTML = html;
            }
            
            function updateAgentRecommendations(analysis, remediation) {
                const div = document.getElementById('agent-recommendations');
                let html = '';
                // AnalyzerAgent
                if (analysis && analysis.latest_analysis && analysis.latest_analysis.gpt_analysis) {
                    const gpt = analysis.latest_analysis.gpt_analysis;
                    html += `<div><strong>AnalyzerAgent:</strong><br/>`;
                    html += `<b>Decision:</b> ${gpt.decision || '-'}<br/>`;
                    html += `<b>Reasoning:</b> ${gpt.reasoning || '-'}<br/>`;
                    if (gpt.alternatives && gpt.alternatives.length > 0) {
                        html += `<b>Alternatives:</b><ul>`;
                        for (const alt of gpt.alternatives) {
                            html += `<li>${alt}</li>`;
                        }
                        html += `</ul>`;
                    }
                    html += `</div>`;
                }
                // RemediatorAgent
                if (remediation && remediation.recent_attempts && remediation.recent_attempts.length > 0) {
                    const last = remediation.recent_attempts[remediation.recent_attempts.length - 1];
                    html += `<div style='margin-top:10px;'><strong>RemediatorAgent:</strong><br/>`;
                    html += `<b>Decision:</b> ${last.llm_decision || '-'}<br/>`;
                    html += `<b>Reasoning:</b> ${last.llm_reasoning || '-'}<br/>`;
                    if (last.action) {
                        html += `<b>Action:</b> ${last.action}<br/>`;
                    }
                    html += `</div>`;
                }
                if (!html) html = 'No recommendations available.';
                div.innerHTML = html;
            }
            
            async function sendCommand(command) {
                try {
                    await fetch('/api/command', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({command: command})
                    });
                    setTimeout(refreshData, 1000);
                    setTimeout(refreshData, 2000);
                } catch (error) {
                    console.error('Error sending command:', error);
                }
            }
            
            // Initial load
            refreshData();
            
            // Auto-refresh every 30 seconds
            setInterval(refreshData, 30000);
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
        for agent_name in ["sensor", "analyzer", "remediator", "communicator"]:
            stats = orchestrator.get_agent_stats(agent_name)
            if stats:
                agents[agent_name] = {
                    "health": stats.get("health_status", "unknown"),
                    "status": stats.get("running", False),
                    "uptime": stats.get("uptime", 0),
                    "check_count": stats.get("check_count", 0),
                    "error_count": stats.get("error_count", 0)
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
        if sensor_agent and hasattr(sensor_agent, 'get_current_metrics'):
            return sensor_agent.get_current_metrics() or {}
        return {"error": "Metrics not available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics/history")
async def get_metric_history(limit: int = 50):
    """Get metric history."""
    try:
        sensor_agent = orchestrator.agents.get("sensor")
        if sensor_agent and hasattr(sensor_agent, 'get_metric_history'):
            return sensor_agent.get_metric_history(limit)
        return {"error": "Metric history not available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis")
async def get_analysis_results():
    """Get recent analysis results."""
    try:
        analyzer_agent = orchestrator.agents.get("analyzer")
        if analyzer_agent and hasattr(analyzer_agent, 'get_analysis_summary'):
            return analyzer_agent.get_analysis_summary()
        return {"error": "Analysis results not available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/remediation")
async def get_remediation_summary():
    """Get remediation summary."""
    try:
        remediator_agent = orchestrator.agents.get("remediator")
        if remediator_agent and hasattr(remediator_agent, 'get_remediation_summary'):
            return remediator_agent.get_remediation_summary()
        return {"error": "Remediation summary not available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/activity")
async def get_recent_activity(limit: int = 50):
    """Get recent system activity."""
    try:
        communicator_agent = orchestrator.agents.get("communicator")
        if communicator_agent and hasattr(communicator_agent, 'get_communication_summary'):
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
        return {"status": "success", "message": "Configuration update not implemented yet"}
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
            "agents_running": sum(1 for agent in orchestrator.agents.values() if agent.running)
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
            "log_file": config.logging.log_file
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/llm_status")
async def get_llm_status():
    """Get the health status of external LLMs (OpenAI and Gemini)."""
    from utils.gpt_client import gpt_client
    from utils.gemini_client import gemini_client
    openai_status = await gpt_client.health_check()
    gemini_status = await gemini_client.health_check()
    return {
        "openai": "online" if openai_status else "offline",
        "gemini": "online" if gemini_status else "offline"
    }

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

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "detail": str(exc)}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

def start_web_interface():
    """Start the web interface."""
    if not config.web_interface_enabled:
        print("Web interface is disabled in configuration")
        return
    
    print(f"🌐 Starting web interface on http://{config.web_host}:{config.web_port}")
    print(f"📊 Dashboard: http://{config.web_host}:{config.web_port}/")
    print(f"🔧 API Docs: http://{config.web_host}:{config.web_port}/docs")
    
    uvicorn.run(
        app,
        host=config.web_host,
        port=config.web_port,
        log_level="info"
    )

if __name__ == "__main__":
    start_web_interface() 