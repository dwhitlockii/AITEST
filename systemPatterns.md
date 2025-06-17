# System Patterns: Architecture & Design

## Architecture Overview
- Modular, multi-agent system: SensorAgent, AnalyzerAgent, RemediatorAgent, CommunicatorAgent
- Asynchronous message bus for decoupled, event-driven communication
- Central orchestrator manages agent lifecycle and health
- Web (FastAPI) and CLI interfaces for user interaction
- Persistence layer (SQLite, async, config-driven) for historical data
- Plugin system: plugins/ directory, BasePlugin interface, config-driven loading, plugin loader utility

## Key Technical Decisions
- Use of GPT (OpenAI API) for intelligent analysis and recommendations
- Fault-tolerant agent design: agents auto-restart on failure
- Graceful degradation: rule-based fallback if GPT unavailable
- Configurable thresholds and intervals for all metrics
- Extensible via plugins and configuration
- Plugin loader supports dynamic extension via plugins/ directory and config
- Plugins must subclass BasePlugin and register with system context

## Design Patterns
- Observer pattern: agents subscribe to message types
- Command pattern: system commands broadcast to agents
- Strategy pattern: remediation logic adapts based on context
- Singleton/config pattern: centralized config management
- Plugin pattern: plugins discovered and registered at startup via loader

## Component Relationships
- SensorAgent → broadcasts metrics
- AnalyzerAgent → analyzes metrics, broadcasts alerts/analysis
- RemediatorAgent → listens for alerts/analysis, performs remediation
- CommunicatorAgent → logs, notifies, and summarizes system state
- Orchestrator → starts/stops/monitors all agents
- Web/CLI → display and control system state
- PersistenceManager <-> agents (Sensor, Analyzer, Remediator) for logging metrics, analysis, remediation 