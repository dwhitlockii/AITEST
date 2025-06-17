# 🧠 Multi-Agent System: Architecture & Operation Overview

## 1. System Startup & Orchestration
- **System Orchestrator** (`system_orchestrator.py`):
  - Acts as the "conductor" for all agents.
  - Initializes the message bus and launches four specialized agents:
    - **SensorAgent** (metrics collector)
    - **AnalyzerAgent** (AI analyst)
    - **RemediatorAgent** (self-healing fixer)
    - **CommunicatorAgent** (logger, notifier, and status broadcaster)
  - Manages agent lifecycles, restarts failed agents, and coordinates system-wide health checks.

## 2. Agent Roles & Responsibilities

### SensorAgent
- Gathers real system metrics (CPU, memory, disk, network, services, processes).
- Broadcasts metrics to the message bus for other agents.
- Adds witty, personality-infused logs for each metric event.

### AnalyzerAgent
- Listens for new metrics on the message bus.
- Uses GPT (OpenAI API) to analyze, detect anomalies, generate alerts, and recommend actions.
- Broadcasts analysis results and alerts.

### RemediatorAgent
- Listens for alerts and analysis results.
- Decides (with GPT's help) if and how to remediate issues (restart services, clean disk, etc.).
- Tracks remediation attempts, success rates, and cooldowns.
- Broadcasts remediation actions and results.

### CommunicatorAgent
- Subscribes to all message types.
- Logs every event, action, and message with personality.
- Maintains a history of system activity and agent status.
- Provides user notifications and system summaries.
- Makes all information available to the web and CLI interfaces.

## 3. Message Bus: The Nervous System
- **MessageBus** (`utils/message_bus.py`):
  - Asynchronous, priority-based communication channel for all agents.
  - Supports different message types (metrics, alerts, commands, status, coordination, etc.).
  - Maintains a history of all messages for debugging and live feeds.
  - Ensures agents can "talk" to each other without direct references.

## 4. Web Interface: Mission Control
- **Web Dashboard** (`web_interface.py`):
  - Built with FastAPI and Uvicorn.
  - Shows real-time system status, agent health, metrics, and activity.
  - Action buttons send commands to the orchestrator, which broadcasts them to all agents.
  - Live Agent Messages feed shows every message exchanged, labeled by agent and role.
  - Recent Activity shows user-facing events and notifications.

## 5. How Agents Collaborate (Example Flow)
1. **SensorAgent** collects a metric (e.g., high CPU usage) and broadcasts it.
2. **AnalyzerAgent** receives the metric, uses GPT to analyze, and detects a potential issue.
3. **AnalyzerAgent** broadcasts an alert and analysis result.
4. **RemediatorAgent** receives the alert, consults GPT for a safe remediation, and (if safe) restarts a service or cleans disk space.
5. **RemediatorAgent** broadcasts the remediation action and result.
6. **CommunicatorAgent** logs all these events, updates the activity feed, and notifies the user if needed.
7. **Web/CLI Interface** displays all this in real time.

## 6. User Interaction
- **Web Dashboard**: View system and agent health, metrics, and live activity. Use action buttons to trigger system-wide commands. See every agent's message, labeled by name and role, in the live feed.
- **CLI Interface**: Terminal-based control panel with menus for status, agent details, metrics, analysis, remediation, message bus, configuration, and live monitoring.
- **API**: REST endpoints for all system data and commands (see `/docs` for full API).

## 7. Self-Healing & Safety
- **Automated Remediation**: RemediatorAgent only takes safe, pre-approved actions. Cooldowns and max attempt limits prevent repeated or dangerous actions. All actions are logged and visible to the user.
- **Graceful Degradation**: If GPT is unavailable, the system falls back to rule-based analysis and remediation.

## 8. Extensibility
- Add new agents by subclassing `BaseAgent`.
- Add new metrics in `SensorAgent`.
- Add new actions in `RemediatorAgent`.
- Tune thresholds and intervals in `config.py`.
- Integrate with other tools via the API or by extending the message bus.

## 9. Where to See the Action
- **Web Dashboard**: [http://localhost:8000/](http://localhost:8000/) (Live agent messages, system status, and activity feed)
- **Logs**: `debug_output/agent_system.log` (full, detailed logs)
- **CLI**: `python cli_interface.py` for a terminal-based experience.

## 10. Troubleshooting & FAQ
- **Web interface not loading?** Check if port 8000 is available and the backend is running.
- **Agents not collaborating?** Ensure the message bus is running and agents are not in a failed state.
- **GPT not responding?** Check your OpenAI API key and network connectivity.
- **Want to simulate an issue?** Use the CLI or web dashboard to trigger commands and watch the agents collaborate in real time.

---

This document provides a comprehensive overview of how the system operates, how agents collaborate, and how you can interact, extend, and troubleshoot the system. 