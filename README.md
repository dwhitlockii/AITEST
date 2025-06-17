# 🤖 GPT-Driven Multi-Agent System Monitoring & Self-Healing

A production-grade Python system that demonstrates intelligent, GPT-powered multi-agent coordination for real-time system monitoring and automated self-healing. Think of it as having a team of AI specialists watching your system 24/7, each with their own expertise and the ability to take action when things go wrong.

## 🎯 What This System Does

This isn't your typical monitoring system. It's a **living, breathing, thinking** monitoring solution that:

- **Gathers real system metrics** (CPU, memory, disk, services) using `psutil` and Windows-specific tools
- **Uses GPT for intelligent analysis** - not just threshold checking, but actual reasoning about system health
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
   - Uses GPT to analyze metrics and detect patterns
   - Identifies trends and predicts potential issues
   - Provides intelligent reasoning about system health
   - Generates alerts with context and suggested actions

3. **🔧 RemediatorAgent** - The fixer
   - Takes automated recovery actions based on GPT recommendations
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
- **GPT Integration** - OpenAI API for intelligent decision-making
- **Configuration Management** - Centralized, dynamic configuration
- **Logging System** - Rich, colorful logging with personality

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Windows 10/11 (for full service monitoring capabilities)
- OpenAI API key (optional - system works without it but with reduced intelligence)

### Installation

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd multi-agent-monitoring
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
# Create .env file
echo "OPENAI_API_KEY=your_api_key_here" > .env
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

### GPT Configuration
```python
model = "gpt-4"          # Which GPT model to use
temperature = 0.3        # Creativity vs consistency
max_tokens = 500         # Response length limit
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
- **Uses GPT to understand context** - "CPU is high because of a backup job" vs "CPU is high because of a runaway process"
- **Learns from patterns** - Recognizes normal vs abnormal behavior
- **Provides reasoning** - Explains why it's taking actions
- **Adapts strategies** - Changes approach based on what works

### Production-Grade Features

- **Fault tolerance** - Agents restart automatically if they fail
- **Graceful degradation** - Works without GPT (just less intelligent)
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
2. Update GPT prompts to suggest new actions
3. Add safety checks and cooldowns

## 📊 Performance & Scaling

### Current Capabilities
- **Real-time monitoring** - Updates every 5-15 seconds
- **Low resource usage** - Minimal CPU/memory overhead
- **Windows-native** - Full integration with Windows services
- **GPT-powered analysis** - Intelligent decision making

### Scaling Considerations
- **Multiple systems** - Can monitor multiple machines
- **Distributed agents** - Agents can run on different machines
- **Database integration** - Can add persistent storage
- **Alert integration** - Can integrate with PagerDuty, Slack, etc.

## 🚨 Troubleshooting

### Common Issues

1. **GPT not working**: Check API key in `.env` file
2. **Agents not starting**: Check Windows service permissions
3. **High resource usage**: Adjust check intervals in config
4. **Web interface not loading**: Check if port 8000 is available

### Debug Information

- **Logs**: `debug_output/agent_system.log`
- **System status**: `debug_output/system_status.json`
- **API health**: `GET /api/health`
- **Agent details**: Use CLI or web interface

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