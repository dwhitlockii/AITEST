"""
AnalyzerAgent - The brain that spots trouble before it becomes a disaster.
This agent uses GPT to analyze system metrics and provide intelligent insights.
Think of it as the Sherlock Holmes of system monitoring.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from agents.base_agent import BaseAgent
from utils.message_bus import MessageType, MessagePriority
from utils.ollama_client import ollama_client
from config import config
from utils.persistence import PersistenceManager


class AnalyzerAgent(BaseAgent):
    """Agent responsible for analyzing system metrics and detecting issues."""

    def __init__(self):
        super().__init__("AnalyzerAgent")

        # Force Ollama as the only LLM provider
        self.llm_provider = "ollama"
        self.llm_client = ollama_client

        # Analysis state
        self.metric_history: List[Dict[str, Any]] = []
        self.analysis_history: List[Dict[str, Any]] = []
        self.detected_issues: List[Dict[str, Any]] = []
        self.trend_analysis: Dict[str, Any] = {}

        # Threshold tracking
        self.threshold_violations: Dict[str, List[Dict[str, Any]]] = {}

        # GPT analysis cache
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

        # Persistence integration
        self.persistence_enabled = getattr(config, "persistence_enabled", True)
        self.db_path = getattr(config, "db_path", "data/agent_system.db")
        self.persistence = PersistenceManager(self.db_path)

        self.logger.info("AnalyzerAgent initialized - ready to analyze system patterns")

    async def _perform_check(self):
        """Analyze recent metrics and detect issues."""
        try:
            self.last_check_time = datetime.now()

            # Get recent metrics from message bus
            recent_metrics = await self._get_recent_metrics()

            if not recent_metrics:
                self.logger.debug("No recent metrics to analyze")
                return

            # Perform comprehensive analysis
            analysis_result = await self._analyze_system_health(recent_metrics)

            # Store analysis result
            self.analysis_history.append(analysis_result)
            if len(self.analysis_history) > 50:
                self.analysis_history.pop(0)

            # Persist analysis if enabled
            if self.persistence_enabled:
                try:
                    await self.persistence.insert_analysis(
                        timestamp=analysis_result.get("timestamp", datetime.now().isoformat()),
                        agent=self.agent_name,
                        summary=str(analysis_result.get("gpt_analysis", {})),
                        issues=str(analysis_result.get("issues_detected", [])),
                    )
                except Exception as e:
                    self.logger.error(f"Failed to persist analysis: {e}")
                    self.add_issue(f"Persistence error: {str(e)}", "high")

            # Check for threshold violations
            violations = await self._check_threshold_violations(recent_metrics)

            # Detect trends
            trends = await self._analyze_trends(recent_metrics)

            # Generate alerts if needed
            if violations or analysis_result.get("issues_detected"):
                await self._generate_alerts(violations, analysis_result)

            # Broadcast analysis results
            await self._broadcast_analysis_results(analysis_result, violations, trends)

            self.success_count += 1

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to analyze metrics: {e}")
            self.add_issue(f"Analysis failed: {str(e)}", "high")

    async def _get_recent_metrics(self) -> List[Dict[str, Any]]:
        """Get recent metrics from the message bus."""
        # In a real implementation, you'd query the message bus for recent metric data
        # For now, we'll simulate this by checking if we have any cached metrics
        return self.metric_history[-10:] if self.metric_history else []

    async def _analyze_system_health(
        self, metrics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use Ollama to analyze system health."""
        if not metrics:
            return {"error": "No metrics to analyze"}
        latest_metrics = metrics[-1]
        context = self._build_analysis_context(metrics)
        try:
            gpt_decision = await ollama_client.analyze_metrics(latest_metrics, context)
            if hasattr(gpt_decision, "decision") and hasattr(gpt_decision, "reasoning"):
                self.log_gpt_decision(gpt_decision.decision, gpt_decision.reasoning)
                analysis_result = {
                    "timestamp": datetime.now().isoformat(),
                    "gpt_analysis": gpt_decision,
                    "issues_detected": self._extract_issues_from_gpt(gpt_decision),
                    "system_health_score": self._calculate_health_score(latest_metrics),
                    "bottlenecks": latest_metrics.get("performance", {}).get(
                        "bottlenecks", []
                    ),
                    "performance_trend": latest_metrics.get("performance", {}).get(
                        "performance_trend", "unknown"
                    ),
                    "llm_provider": self.llm_provider,
                }
                return analysis_result
            elif isinstance(gpt_decision, dict):
                self.logger.warning(
                    "Ollama returned a dict instead of decision object. Using dict keys."
                )
                self.log_gpt_decision(
                    gpt_decision.get("decision", "?"),
                    gpt_decision.get("reasoning", "?"),
                )
                analysis_result = {
                    "timestamp": datetime.now().isoformat(),
                    "gpt_analysis": gpt_decision,
                    "issues_detected": gpt_decision.get("issues_detected", []),
                    "system_health_score": self._calculate_health_score(latest_metrics),
                    "bottlenecks": latest_metrics.get("performance", {}).get(
                        "bottlenecks", []
                    ),
                    "performance_trend": latest_metrics.get("performance", {}).get(
                        "performance_trend", "unknown"
                    ),
                    "llm_provider": self.llm_provider,
                }
                return analysis_result
            else:
                self.logger.error(f"Ollama returned unexpected type: {type(gpt_decision)}")
                return {
                    "timestamp": datetime.now().isoformat(),
                    "error": f"Ollama returned unexpected type: {type(gpt_decision)}",
                    "fallback_analysis": self._fallback_analysis(latest_metrics),
                    "llm_provider": self.llm_provider,
                }
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": f"LLM analysis failed: {str(e)}",
                "fallback_analysis": self._fallback_analysis(latest_metrics),
                "llm_provider": self.llm_provider,
            }

    def _build_analysis_context(self, metrics: List[Dict[str, Any]]) -> str:
        """Build context for GPT analysis."""
        if len(metrics) < 2:
            return "Initial system analysis - limited historical data available"

        # Get recent trends
        recent_cpu = []
        recent_memory = []
        recent_disk = []

        for metric in metrics[-5:]:  # Last 5 data points
            if "cpu" in metric and "usage_percent" in metric["cpu"]:
                recent_cpu.append(metric["cpu"]["usage_percent"])
            if "memory" in metric and "usage_percent" in metric["memory"]:
                recent_memory.append(metric["memory"]["usage_percent"])
            if "disk" in metric:
                for path, disk_data in metric["disk"].items():
                    if "usage_percent" in disk_data:
                        recent_disk.append(disk_data["usage_percent"])

        context_parts = []

        if recent_cpu:
            avg_cpu = sum(recent_cpu) / len(recent_cpu)
            cpu_trend = (
                "increasing"
                if recent_cpu[-1] > recent_cpu[0]
                else "decreasing" if recent_cpu[-1] < recent_cpu[0] else "stable"
            )
            context_parts.append(
                f"CPU usage: {avg_cpu:.1f}% average, {cpu_trend} trend"
            )

        if recent_memory:
            avg_memory = sum(recent_memory) / len(recent_memory)
            memory_trend = (
                "increasing"
                if recent_memory[-1] > recent_memory[0]
                else "decreasing" if recent_memory[-1] < recent_memory[0] else "stable"
            )
            context_parts.append(
                f"Memory usage: {avg_memory:.1f}% average, {memory_trend} trend"
            )

        if recent_disk:
            avg_disk = sum(recent_disk) / len(recent_disk)
            context_parts.append(f"Disk usage: {avg_disk:.1f}% average")

        # Add performance context
        latest_performance = metrics[-1].get("performance", {})
        if "health_status" in latest_performance:
            context_parts.append(
                f"Overall health: {latest_performance['health_status']}"
            )

        if "bottlenecks" in latest_performance and latest_performance["bottlenecks"]:
            context_parts.append(
                f"Bottlenecks: {', '.join(latest_performance['bottlenecks'])}"
            )

        return (
            " | ".join(context_parts) if context_parts else "Standard system monitoring"
        )

    def _extract_issues_from_gpt(self, gpt_decision) -> List[Dict[str, Any]]:
        """Extract issues from GPT decision."""
        issues = []

        # Check risk level
        if gpt_decision.risk_level in ["high", "critical"]:
            issues.append(
                {
                    "type": "gpt_risk_assessment",
                    "severity": gpt_decision.risk_level,
                    "description": f"GPT identified {gpt_decision.risk_level} risk: {gpt_decision.decision}",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check alternatives for potential issues
        for alternative in gpt_decision.alternatives:
            if any(
                keyword in alternative.lower()
                for keyword in ["restart", "kill", "stop", "clean", "free"]
            ):
                issues.append(
                    {
                        "type": "gpt_recommended_action",
                        "severity": "medium",
                        "description": f"GPT alternative: {alternative}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        return issues

    def _calculate_health_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall system health score (0-100)."""
        try:
            score = 100.0

            # CPU penalty
            if "cpu" in metrics and "usage_percent" in metrics["cpu"]:
                cpu_usage = metrics["cpu"]["usage_percent"]
                if cpu_usage > config.thresholds.cpu_critical:
                    score -= 30
                elif cpu_usage > config.thresholds.cpu_warning:
                    score -= 15

            # Memory penalty
            if "memory" in metrics and "usage_percent" in metrics["memory"]:
                memory_usage = metrics["memory"]["usage_percent"]
                if memory_usage > config.thresholds.memory_critical:
                    score -= 30
                elif memory_usage > config.thresholds.memory_warning:
                    score -= 15

            # Disk penalty
            for path, disk_data in metrics.get("disk", {}).items():
                if "usage_percent" in disk_data:
                    disk_usage = disk_data["usage_percent"]
                    if disk_usage > config.thresholds.disk_critical:
                        score -= 20
                    elif disk_usage > config.thresholds.disk_warning:
                        score -= 10

            # Service penalty
            for service_name, service_data in metrics.get("services", {}).items():
                if isinstance(service_data, dict) and not service_data.get(
                    "running", True
                ):
                    score -= 5

            return max(0.0, score)

        except Exception as e:
            self.logger.error(f"Failed to calculate health score: {e}")
            return 50.0  # Default to neutral score

    def _fallback_analysis(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analysis when GPT is unavailable."""
        issues = []

        # Check CPU
        if "cpu" in metrics and "usage_percent" in metrics["cpu"]:
            cpu_usage = metrics["cpu"]["usage_percent"]
            if cpu_usage > config.thresholds.cpu_critical:
                issues.append(f"Critical CPU usage: {cpu_usage}%")
            elif cpu_usage > config.thresholds.cpu_warning:
                issues.append(f"High CPU usage: {cpu_usage}%")

        # Check memory
        if "memory" in metrics and "usage_percent" in metrics["memory"]:
            memory_usage = metrics["memory"]["usage_percent"]
            if memory_usage > config.thresholds.memory_critical:
                issues.append(f"Critical memory usage: {memory_usage}%")
            elif memory_usage > config.thresholds.memory_warning:
                issues.append(f"High memory usage: {memory_usage}%")

        # Check disk
        for path, disk_data in metrics.get("disk", {}).items():
            if "usage_percent" in disk_data:
                disk_usage = disk_data["usage_percent"]
                if disk_usage > config.thresholds.disk_critical:
                    issues.append(f"Critical disk usage on {path}: {disk_usage}%")
                elif disk_usage > config.thresholds.disk_warning:
                    issues.append(f"High disk usage on {path}: {disk_usage}%")

        return {
            "issues_detected": issues,
            "health_score": self._calculate_health_score(metrics),
            "method": "fallback_threshold_check",
        }

    async def _check_threshold_violations(
        self, metrics: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check for threshold violations in recent metrics."""
        violations = []

        if not metrics:
            return violations

        latest_metrics = metrics[-1]

        # Check CPU threshold violations
        if "cpu" in latest_metrics and "usage_percent" in latest_metrics["cpu"]:
            cpu_usage = latest_metrics["cpu"]["usage_percent"]
            if cpu_usage > config.thresholds.cpu_critical:
                violations.append(
                    {
                        "metric": "cpu_usage",
                        "value": cpu_usage,
                        "threshold": config.thresholds.cpu_critical,
                        "severity": "critical",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            elif cpu_usage > config.thresholds.cpu_warning:
                violations.append(
                    {
                        "metric": "cpu_usage",
                        "value": cpu_usage,
                        "threshold": config.thresholds.cpu_warning,
                        "severity": "warning",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # Check memory threshold violations
        if "memory" in latest_metrics and "usage_percent" in latest_metrics["memory"]:
            memory_usage = latest_metrics["memory"]["usage_percent"]
            if memory_usage > config.thresholds.memory_critical:
                violations.append(
                    {
                        "metric": "memory_usage",
                        "value": memory_usage,
                        "threshold": config.thresholds.memory_critical,
                        "severity": "critical",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            elif memory_usage > config.thresholds.memory_warning:
                violations.append(
                    {
                        "metric": "memory_usage",
                        "value": memory_usage,
                        "threshold": config.thresholds.memory_warning,
                        "severity": "warning",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # Check disk threshold violations
        for path, disk_data in latest_metrics.get("disk", {}).items():
            if "usage_percent" in disk_data:
                disk_usage = disk_data["usage_percent"]
                if disk_usage > config.thresholds.disk_critical:
                    violations.append(
                        {
                            "metric": f"disk_usage_{path}",
                            "value": disk_usage,
                            "threshold": config.thresholds.disk_critical,
                            "severity": "critical",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                elif disk_usage > config.thresholds.disk_warning:
                    violations.append(
                        {
                            "metric": f"disk_usage_{path}",
                            "value": disk_usage,
                            "threshold": config.thresholds.disk_warning,
                            "severity": "warning",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

        return violations

    async def _analyze_trends(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in system metrics using Ollama only."""
        if len(metrics) < 3:
            return {"error": "Insufficient data for trend analysis"}
        try:
            gpt_decision = await ollama_client.detect_anomalies(
                metrics, self.metric_history[-10:]
            )
            trends = {
                "timestamp": datetime.now().isoformat(),
                "trend_analysis": {
                    "decision": gpt_decision.decision,
                    "reasoning": gpt_decision.reasoning,
                    "confidence": gpt_decision.confidence,
                    "risk_level": gpt_decision.risk_level,
                    "anomalies_detected": gpt_decision.metadata.get(
                        "anomalies_detected", []
                    ),
                    "severity": gpt_decision.metadata.get("severity", "unknown"),
                    "affected_metrics": gpt_decision.metadata.get(
                        "affected_metrics", []
                    ),
                },
                "calculated_trends": self._calculate_trends(metrics),
            }
            return trends
        except Exception as e:
            self.logger.error(f"Trend analysis failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": f"Trend analysis failed: {str(e)}",
                "calculated_trends": self._calculate_trends(metrics),
            }

    def _calculate_trends(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trends from metric data."""
        trends = {}

        if len(metrics) < 2:
            return {"error": "Insufficient data"}

        # CPU trend
        cpu_values = []
        for metric in metrics:
            if "cpu" in metric and "usage_percent" in metric["cpu"]:
                cpu_values.append(metric["cpu"]["usage_percent"])

        if len(cpu_values) >= 2:
            cpu_trend = (
                "increasing"
                if cpu_values[-1] > cpu_values[0]
                else "decreasing" if cpu_values[-1] < cpu_values[0] else "stable"
            )
            trends["cpu_trend"] = {
                "direction": cpu_trend,
                "change_percent": (
                    ((cpu_values[-1] - cpu_values[0]) / cpu_values[0] * 100)
                    if cpu_values[0] > 0
                    else 0
                ),
            }

        # Memory trend
        memory_values = []
        for metric in metrics:
            if "memory" in metric and "usage_percent" in metric["memory"]:
                memory_values.append(metric["memory"]["usage_percent"])

        if len(memory_values) >= 2:
            memory_trend = (
                "increasing"
                if memory_values[-1] > memory_values[0]
                else "decreasing" if memory_values[-1] < memory_values[0] else "stable"
            )
            trends["memory_trend"] = {
                "direction": memory_trend,
                "change_percent": (
                    ((memory_values[-1] - memory_values[0]) / memory_values[0] * 100)
                    if memory_values[0] > 0
                    else 0
                ),
            }

        return trends

    async def _generate_alerts(
        self, violations: List[Dict[str, Any]], analysis_result: Dict[str, Any]
    ):
        """Generate alerts for detected issues."""
        alerts = []

        # Add threshold violations as alerts
        for violation in violations:
            alerts.append(
                {
                    "type": "threshold_violation",
                    "severity": violation["severity"],
                    "message": f"{violation['metric']} exceeded threshold: {violation['value']} > {violation['threshold']}",
                    "timestamp": violation["timestamp"],
                }
            )

        # Add GPT-detected issues as alerts
        for issue in analysis_result.get("issues_detected", []):
            alerts.append(
                {
                    "type": "gpt_analysis",
                    "severity": issue.get("severity", "medium"),
                    "message": issue["description"],
                    "timestamp": issue["timestamp"],
                }
            )

        # Send alerts to message bus
        for alert in alerts:
            await self.message_bus.broadcast(
                sender=self.agent_name,
                message_type=MessageType.ALERT,
                content=alert,
                priority=(
                    MessagePriority.HIGH
                    if alert["severity"] in ["critical", "high"]
                    else MessagePriority.NORMAL
                ),
            )

            self.logger.warning(f"Alert generated: {alert['message']}")

    async def _broadcast_analysis_results(
        self,
        analysis_result: Dict[str, Any],
        violations: List[Dict[str, Any]],
        trends: Dict[str, Any],
    ):
        """Broadcast analysis results to other agents."""
        results = {
            "analysis": analysis_result,
            "violations": violations,
            "trends": trends,
            "timestamp": datetime.now().isoformat(),
        }

        await self.message_bus.broadcast(
            sender=self.agent_name,
            message_type=MessageType.TREND_ANALYSIS,
            content=results,
            priority=MessagePriority.NORMAL,
        )

    async def _setup_subscriptions(self):
        """Set up message subscriptions for the analyzer."""
        await super()._setup_subscriptions()

        # Subscribe to metric data
        await self.message_bus.subscribe(
            MessageType.METRIC_DATA, self._handle_metric_data
        )
        self.subscribed_message_types.append(MessageType.METRIC_DATA)

    async def _handle_metric_data(self, message):
        """Handle incoming metric data."""
        if message.sender == self.agent_name:
            return  # Ignore our own messages

        # Store metrics for analysis
        self.metric_history.append(message.content)
        if len(self.metric_history) > 100:
            self.metric_history.pop(0)

        self.logger.debug(f"Received metrics from {message.sender}")

        # Analyze the new metric
        analysis_result = await self._analyze_system_health(self.metric_history[-10:])
        self.analysis_history.append(analysis_result)
        if len(self.analysis_history) > 50:
            self.analysis_history.pop(0)

        # Broadcast analysis results
        await self.message_bus.broadcast(
            sender=self.agent_name,
            message_type=MessageType.TREND_ANALYSIS,
            content=analysis_result,
            priority=MessagePriority.NORMAL,
        )

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get a summary of recent analysis results."""
        if not self.analysis_history:
            return {"error": "No analysis history available"}

        latest_analysis = self.analysis_history[-1]

        return {
            "latest_analysis": latest_analysis,
            "total_analyses": len(self.analysis_history),
            "health_score": latest_analysis.get("system_health_score", 0),
            "issues_detected": len(latest_analysis.get("issues_detected", [])),
            "gpt_confidence": latest_analysis.get("gpt_analysis", {}).get(
                "confidence", 0
            ),
            "risk_level": latest_analysis.get("gpt_analysis", {}).get(
                "risk_level", "unknown"
            ),
        }

    async def _perform_gpt_analysis(
        self, metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Perform GPT-based analysis of system metrics."""
        try:
            # Create context for GPT analysis
            context = f"System analysis for {self.agent_name}"

            # Use the new GPT client method
            gpt_decision = await ollama_client.analyze_metrics(metrics, context)

            # Log the GPT decision
            self.log_gpt_decision(gpt_decision.decision, gpt_decision.reasoning)

            return {
                "gpt_analysis": gpt_decision.decision,
                "reasoning": gpt_decision.reasoning,
                "confidence": gpt_decision.confidence,
                "risk_level": gpt_decision.risk_level,
                "alternatives": gpt_decision.alternatives,
                "metadata": gpt_decision.metadata,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"GPT analysis failed: {e}")
            return None

    async def _perform_trend_analysis(
        self, metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Perform trend analysis using GPT."""
        try:
            # Get historical context for trend analysis
            historical_context = (
                self.metric_history[-10:]
                if len(self.metric_history) >= 10
                else self.metric_history
            )

            # Use the new GPT client method for anomaly detection
            gpt_decision = await ollama_client.detect_anomalies(
                metrics, historical_context
            )

            # Log the GPT decision
            self.log_gpt_decision(gpt_decision.decision, gpt_decision.reasoning)

            return {
                "trend_analysis": gpt_decision.decision,
                "reasoning": gpt_decision.reasoning,
                "confidence": gpt_decision.confidence,
                "risk_level": gpt_decision.risk_level,
                "anomalies_detected": gpt_decision.metadata.get(
                    "anomalies_detected", []
                ),
                "severity": gpt_decision.metadata.get("severity", "unknown"),
                "affected_metrics": gpt_decision.metadata.get("affected_metrics", []),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Trend analysis failed: {e}")
            return None

    async def clear_llm_fallback(self):
        """Clear the LLM fallback state and broadcast an alert-clear message."""
        from utils.message_bus import message_bus, MessageType, MessagePriority
        config.clear_llm_fallback()
        await message_bus.broadcast(
            sender=self.agent_name,
            message_type=MessageType.ALERT,
            content={
                "type": "llm_quota_cleared",
                "severity": "info",
                "message": "OpenAI quota restored. System will resume using OpenAI for LLM tasks.",
                "timestamp": datetime.now().isoformat(),
            },
            priority=MessagePriority.NORMAL,
        )
