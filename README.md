# 🤖 GPT-Driven Multi-Agent System Monitoring & Self-Healing

A production-grade Python system that demonstrates intelligent, Ollama-powered multi-agent coordination for real-time system monitoring and automated self-healing. Think of it as having a team of AI specialists watching your system 24/7, each with their own expertise and the ability to take action when things go wrong.

## 🎯 What This System Does

This isn't your typical monitoring system. It's a **living, breathing, thinking** monitoring solution that:

- **Gathers real system metrics** (CPU, memory, disk, services) using `psutil` and Windows-specific tools
- **Uses Ollama for intelligent analysis** - not just threshold checking, but actual reasoning about system health
- **Coordinates multiple specialized agents** that communicate and work together
- **Performs automated self-healing** - restarts services, cleans up disk space, and takes other recovery actions
- **Adapts dynamically** - changes thresholds, escalates issues, and modifies strategies based on conditions
- **Provides beautiful monitoring interfaces** - both web dashboard and CLI

## 🏗️ Architecture Overview

### The Agent Team

Each agent has a specific role and personality:

1. **🤖 SensorAgent** - The eyes and ears
   - Gathers comprehensive system metrics every 5 seconds
   - Monitors CPU, memory, disk, network, services, and processes
   - Provides witty commentary on system state ("CPU's spiking harder than my coffee intake")

2. **🧠 AnalyzerAgent** - The brain
   - Uses Ollama to analyze metrics and detect patterns
   - Identifies trends and predicts potential issues
   - Provides intelligent reasoning about system health
   - Generates alerts with context and suggested actions

3. **🔧 RemediatorAgent** - The fixer
   - Takes automated recovery actions based on Ollama recommendations
   - Restarts failed services, cleans up disk space
   - Implements safety measures and cooldown periods
   - Tracks remediation success rates

4. **📡 CommunicatorAgent** - The mouthpiece
   - Logs all system activity with personality
   - Manages user notifications and status updates
   - Maintains system health history
   - Provides communication between agents

### The Nervous System

- **Message Bus** - Asynchronous communication between agents
- **Ollama Integration** - Local LLM for intelligent decision-making (no API keys required)
- **Configuration Management** - Centralized, dynamic configuration
- **Logging System** - Rich, colorful logging with personality

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Windows 10/11 (for full service monitoring capabilities)
- **Ollama installed** (see OLLAMA_SETUP.md)
- **No API keys required**

### Installation

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd multi-agent-monitoring
pip install -r requirements.txt
```

2. **Install and configure Ollama:**
   - See `OLLAMA_SETUP.md` for full instructions
   - Example (Windows):
```powershell
winget install Ollama.Ollama
ollama pull mistral
```

3. **Run the system:**
```bash
# Start the full system with web interface
python web_interface.py

# Or run CLI-only version
python cli_interface.py

# Or run the core system directly
python system_orchestrator.py
```

### Access Points

- **🌐 Web Dashboard**: http://localhost:8000
- **🔧 API Documentation**: http://localhost:8000/docs
- **📊 Health Check**: http://localhost:8000/api/health
- **💻 CLI Interface**: Run `python cli_interface.py`

## 🎮 Usage Examples

### Web Interface

The web dashboard provides real-time monitoring with:
- System health status and uptime
- Agent health indicators
- Live system metrics (CPU, memory, disk)
- Recent activity feed
- Action buttons for system control

### CLI Interface

Interactive command-line interface with options:
```bash
1. 📊 System Status
2. 🤖 Agent Details  
3. 📈 System Metrics
4. 🧠 Analysis Results
5. 🔧 Remediation Status
6. 📡 Message Bus
7. ⚙️ Configuration
8. 🎮 Send Commands
9. 📋 Live Monitoring
```

### API Endpoints

RESTful API for integration:
```bash
# Get system status
GET /api/system

# Get agent details
GET /api/agents

# Get current metrics
GET /api/metrics

# Send commands
POST /api/command
{"command": "health_check", "target": "all"}
```

## 🔧 Configuration

The system is highly configurable through `config.py`:

### Thresholds
```python
cpu_critical = 90.0      # CPU usage % that triggers panic mode
cpu_warning = 75.0       # CPU usage % that raises eyebrows
memory_critical = 95.0   # Memory usage % that makes us sweat
disk_critical = 95.0     # Disk usage % that's basically full
```

### Agent Settings
```python
check_interval = 5.0     # How often agents check (seconds)
max_concurrent_actions = 2  # Safety limit on concurrent actions
healing_cooldown = 60    # Seconds between healing attempts
```

### Ollama Configuration
```python
ollama_url = "http://localhost:11434"
ollama_model = "mistral"  # Default model
ollama_timeout = 30
ollama_retry_attempts = 3
ollama_retry_delay = 2
```

## 🧪 Testing & Simulation

### Simulating Issues

The system can detect and respond to real issues, but you can also simulate problems:

1. **High CPU Usage**: Run CPU-intensive tasks
2. **Memory Pressure**: Allocate large amounts of memory
3. **Disk Space**: Fill up disk with large files
4. **Service Failures**: Stop Windows services manually

### Monitoring the Response

Watch how the system responds:
- Check logs in `debug_output/agent_system.log`
- Monitor the web dashboard
- Use CLI interface for detailed status
- Check API endpoints for programmatic access

## 🔍 What Makes This Special

### Real Intelligence, Not Just Rules

Unlike traditional monitoring that just checks thresholds, this system:
- **Uses Ollama to understand context** - "CPU is high because of a backup job" vs "CPU is high because of a runaway process"
- **Learns from patterns** - Recognizes normal vs abnormal behavior
- **Provides reasoning** - Explains why it's taking actions
- **Adapts strategies** - Changes approach based on what works

### Production-Grade Features

- **Fault tolerance** - Agents restart automatically if they fail
- **Graceful degradation** - Works without LLM (just less intelligent)
- **Comprehensive logging** - Everything is tracked and searchable
- **Multiple interfaces** - Web, CLI, and API access
- **Real system integration** - Uses actual Windows APIs and services

### Personality and Style

The system has character:
- Witty log messages ("CPU's spiking harder than my coffee intake")
- Emoji-rich interfaces
- Conversational error messages
- Professional but approachable tone

## 🛠️ Development & Extension

### Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`
2. Implement the `_perform_check()` method
3. Add configuration in `config.py`
4. Register in `system_orchestrator.py`

### Adding New Metrics

1. Extend `SensorAgent._gather_system_metrics()`
2. Add threshold configuration
3. Update analysis logic in `AnalyzerAgent`

### Custom Remediation Actions

1. Add new methods to `RemediatorAgent`
2. Update prompts to suggest new actions
3. Add safety checks and cooldowns

## 📊 Performance & Scaling

### Current Capabilities
- **Real-time monitoring** - Updates every 5-15 seconds
- **Low resource usage** - Minimal CPU/memory overhead
- **Windows-native** - Full integration with Windows services
- **Ollama-powered analysis** - Intelligent decision making

### Scaling Considerations
- **Multiple systems** - Can monitor multiple machines
- **Distributed agents** - Agents can run on different machines
- **Database integration** - Can add persistent storage
- **Alert integration** - Can integrate with PagerDuty, Slack, etc.

## 🚨 Troubleshooting

### Common Issues
- **Web interface not loading:** Ensure port 8000 is free and `web_interface.py` is running.
- **Agents not collaborating:** Check logs in `debug_output/agent_system.log` for errors. Restart the orchestrator if needed.
- **Ollama not responding:** Verify Ollama is running and the model is available. See `OLLAMA_SETUP.md` for troubleshooting.
- **Disk space warnings:** If disk usage is high, let the RemediatorAgent run or manually clean up space.
- **Permission errors:** Some actions (like service restarts) require running as administrator.

### Where to Find Logs
- All agent/system logs: `debug_output/agent_system.log`
- System status snapshots: `debug_output/system_status.json`

## 🚀 Deployment Instructions

1. **Production Setup**
   - Use a virtual environment: `python -m venv venv && venv\Scripts\activate`
   - Install dependencies: `pip install -r requirements.txt`
   - Run with: `python web_interface.py` (for web) or `python cli_interface.py` (for CLI)
   - For background/daemon use, consider a process manager (e.g., `pm2`, `systemd`, or Windows Task Scheduler)

2. **Security Best Practices**
   - Run on trusted systems only
   - Regularly update dependencies

## 📚 More Usage Examples

### CLI: Send a Command
```bash
python cli_interface.py
# Choose option 8 to send a command, e.g. 'health_check' to all agents
```

### API: Trigger Remediation
```bash
curl -X POST http://localhost:8000/api/command -H "Content-Type: application/json" -d '{"command": "restart", "target": "remediator"}'
```

### Web: Live Monitoring
- Open [http://localhost:8000](http://localhost:8000) in your browser
- Use the dashboard to view agent health, metrics, and send actions

## 🤝 Contributing

This is a demonstration system, but contributions are welcome:

1. **Report bugs** - Use GitHub issues
2. **Suggest features** - What would make this more useful?
3. **Improve documentation** - Help others understand the system
4. **Add new capabilities** - Extend the agent team

## 📄 License

This project is for educational and demonstration purposes. Feel free to use, modify, and extend for your own monitoring needs.

## 🎉 What You've Built

You now have a **production-ready, intelligent monitoring system** that:

- ✅ Monitors real system metrics
- ✅ Uses AI for intelligent analysis  
- ✅ Coordinates multiple specialized agents
- ✅ Performs automated self-healing
- ✅ Provides beautiful monitoring interfaces
- ✅ Handles failures gracefully
- ✅ Scales and extends easily

This isn't just monitoring - it's **AI-powered system guardianship**. Your systems now have intelligent, autonomous defenders that work 24/7 to keep everything running smoothly.

---

*"DevOps Engineer = SysAdmin with YAML and anxiety."* 

*"Let's make this thing production-ready, not some half-baked science fair project."*

*"Oops, That Was Production: Tales from the Infra Trenches."* 

## 🧩 Plugin API & Extension Points

### How Plugins Work
- Plugins are Python modules in the `plugins/` directory.
- Each plugin must subclass `BasePlugin` (see `plugins/base_plugin.py`).
- Plugins are loaded at startup if listed in `config.plugins_to_load`.
- Each plugin receives a `system_context` dict with references to the orchestrator, config, and message bus.
- Plugins can register new agents, remediation actions, metrics, or other system extensions.
- Each plugin can have its own config section in `config.plugin_configs`.

### BasePlugin Interface
```python
from plugins.base_plugin import BasePlugin

class MyPlugin(BasePlugin):
    def register(self, system_context):
        # Register new actions, agents, or metrics here
        pass

    def get_config(self):
        return self.config
```

### Extension Points
- **Remediation Actions:** Register new methods on RemediatorAgent (e.g., `remediator.custom_action = self.custom_action`).
- **Metrics:** Register new metric collection routines with SensorAgent.
- **Agents:** Register and start new agent classes via the orchestrator.
- **Event Hooks:** Subscribe to message bus events or broadcast new message types.

### Sample Plugin: Custom Remediation Action
```python
from plugins.base_plugin import BasePlugin

class SampleRemediationPlugin(BasePlugin):
    def register(self, system_context):
        remediator = system_context['orchestrator'].agents.get('remediator')
        if remediator:
            remediator.clear_event_logs = self.clear_event_logs
            remediator.logger.info("Registered clear_event_logs action.")

    async def clear_event_logs(self):
        # Custom remediation logic here
        pass

    def get_config(self):
        return self.config
```

### Best Practices
- Always validate and sanitize input in plugins.
- Use config toggles to enable/disable plugin features.
- Document all plugin actions and extension points.
- Only use trusted plugins—plugins run with full Python privileges.

See `plugins/base_plugin.py` and `plugins/sample_remediation_plugin.py` for real examples.

## LLM Provider: Ollama Only

This system is now **Ollama-only** for all LLM operations. No OpenAI or Gemini support. All LLM-using agents use Ollama (local, API key-free) exclusively.

- **No API keys required**
- **No data leaves your machine**
- **All LLM analysis and remediation is handled locally**

See `OLLAMA_SETUP.md` for full setup and troubleshooting instructions. 