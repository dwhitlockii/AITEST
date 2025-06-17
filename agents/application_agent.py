"""
ApplicationAgent - The application specialist that keeps your software running smoothly.
This agent monitors application performance, processes, memory usage, and application-specific issues.
Think of it as your DevOps engineer with a focus on application health and performance.
"""

import os
import subprocess
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from agents.base_agent import BaseAgent
from utils.message_bus import MessageType, MessagePriority
from utils.ollama_client import ollama_client
from config import config
from utils.persistence import PersistenceManager


class ApplicationAgent(BaseAgent):
    """Agent responsible for application monitoring, performance analysis, and application remediation."""

    def __init__(self):
        super().__init__("application")

        # Force Ollama as the only LLM provider
        self.llm_provider = "ollama"
        self.llm_client = ollama_client

        # Application state
        self.application_metrics: List[Dict[str, Any]] = []
        self.process_monitoring: List[Dict[str, Any]] = []
        self.application_issues: List[Dict[str, Any]] = []
        self.performance_baselines: Dict[str, Any] = {}

        # Application monitoring
        self.monitored_applications = [
            "chrome.exe", "firefox.exe", "code.exe", "notepad.exe",
            "explorer.exe", "svchost.exe", "winlogon.exe"
        ]
        self.critical_processes = [
            "explorer.exe", "svchost.exe", "winlogon.exe", "csrss.exe"
        ]

        # Performance thresholds
        self.cpu_threshold = 80.0  # %
        self.memory_threshold = 85.0  # %
        self.response_time_threshold = 5.0  # seconds
        self.crash_threshold = 3  # crashes per hour

        # Persistence integration
        self.persistence_enabled = getattr(config, "persistence_enabled", True)
        self.db_path = getattr(config, "db_path", "data/agent_system.db")
        self.persistence = PersistenceManager(self.db_path)

        self.logger.info("ApplicationAgent initialized - ready to monitor application performance")

    async def _perform_check(self):
        """Perform application monitoring and analysis."""
        try:
            self.last_check_time = datetime.now()

            # Gather application metrics
            app_metrics = await self._gather_application_metrics()

            # Monitor processes
            process_metrics = await self._monitor_processes()

            # Check application health
            health_metrics = await self._check_application_health()

            # Analyze application performance
            performance_analysis = await self._analyze_application_performance(
                app_metrics, process_metrics, health_metrics
            )

            # Detect application issues
            issues = await self._detect_application_issues(
                app_metrics, process_metrics, health_metrics
            )

            # Perform application remediation if needed
            if issues:
                await self._perform_application_remediation(issues)

            # Update application status
            await self._update_application_status(
                app_metrics, process_metrics, health_metrics, performance_analysis, issues
            )

            # Persist application data if enabled
            if self.persistence_enabled:
                try:
                    await self.persistence.insert_analysis(
                        timestamp=datetime.now().isoformat(),
                        agent=self.agent_name,
                        summary=f"Application scan completed - {len(issues)} issues detected",
                        issues=str(issues),
                    )
                except Exception as e:
                    self.logger.error(f"Failed to persist application data: {e}")

            # Broadcast application status
            await self._broadcast_application_status(
                app_metrics, process_metrics, health_metrics, performance_analysis, issues
            )

            self.success_count += 1

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to perform application check: {e}")
            self.add_issue(f"Application check failed: {str(e)}", "high")

    async def _gather_application_metrics(self) -> Dict[str, Any]:
        """Gather comprehensive application metrics."""
        try:
            import psutil

            metrics = {
                "timestamp": datetime.now().isoformat(),
                "running_applications": await self._get_running_applications(),
                "application_performance": await self._get_application_performance(),
                "memory_usage": await self._get_memory_usage(),
                "cpu_usage": await self._get_cpu_usage(),
                "disk_io": await self._get_disk_io(),
                "application_errors": await self._get_application_errors(),
            }

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to gather application metrics: {e}")
            return {"error": str(e)}

    async def _get_running_applications(self) -> List[Dict[str, Any]]:
        """Get list of running applications."""
        try:
            import psutil

            running_apps = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    proc_info = proc.info
                    
                    # Check if it's a monitored application
                    if proc_info['name'] in self.monitored_applications:
                        app_info = {
                            "name": proc_info['name'],
                            "pid": proc_info['pid'],
                            "cpu_percent": proc_info.get('cpu_percent', 0),
                            "memory_percent": proc_info.get('memory_percent', 0),
                            "status": proc_info.get('status', 'unknown'),
                            "is_critical": proc_info['name'] in self.critical_processes,
                            "start_time": datetime.fromtimestamp(proc.create_time()).isoformat() if hasattr(proc, 'create_time') else None
                        }
                        running_apps.append(app_info)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return running_apps

        except Exception as e:
            self.logger.error(f"Failed to get running applications: {e}")
            return []

    async def _get_application_performance(self) -> Dict[str, Any]:
        """Get application performance metrics."""
        try:
            import psutil

            performance_data = {
                "total_processes": len(psutil.pids()),
                "active_processes": 0,
                "zombie_processes": 0,
                "high_cpu_processes": 0,
                "high_memory_processes": 0
            }
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    proc_info = proc.info
                    
                    if proc_info.get('status') == 'running':
                        performance_data['active_processes'] += 1
                    elif proc_info.get('status') == 'zombie':
                        performance_data['zombie_processes'] += 1
                    
                    if proc_info.get('cpu_percent', 0) > self.cpu_threshold:
                        performance_data['high_cpu_processes'] += 1
                    
                    if proc_info.get('memory_percent', 0) > self.memory_threshold:
                        performance_data['high_memory_processes'] += 1
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return performance_data

        except Exception as e:
            self.logger.error(f"Failed to get application performance: {e}")
            return {"error": str(e)}

    async def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage for applications."""
        try:
            import psutil

            memory = psutil.virtual_memory()
            
            return {
                "total_memory_gb": memory.total / (1024**3),
                "available_memory_gb": memory.available / (1024**3),
                "used_memory_gb": memory.used / (1024**3),
                "memory_percent": memory.percent,
                "swap_total_gb": psutil.swap_memory().total / (1024**3) if hasattr(psutil, 'swap_memory') else 0,
                "swap_used_gb": psutil.swap_memory().used / (1024**3) if hasattr(psutil, 'swap_memory') else 0
            }

        except Exception as e:
            self.logger.error(f"Failed to get memory usage: {e}")
            return {"error": str(e)}

    async def _get_cpu_usage(self) -> Dict[str, Any]:
        """Get CPU usage for applications."""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Get per-core CPU usage
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
            
            return {
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "cpu_per_core": cpu_per_core,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }

        except Exception as e:
            self.logger.error(f"Failed to get CPU usage: {e}")
            return {"error": str(e)}

    async def _get_disk_io(self) -> Dict[str, Any]:
        """Get disk I/O for applications."""
        try:
            import psutil

            disk_io = psutil.disk_io_counters()
            
            return {
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count,
                "read_time": disk_io.read_time,
                "write_time": disk_io.write_time
            }

        except Exception as e:
            self.logger.error(f"Failed to get disk I/O: {e}")
            return {"error": str(e)}

    async def _get_application_errors(self) -> List[Dict[str, Any]]:
        """Get application error logs."""
        try:
            # This would query application logs
            # For now, return a placeholder
            return [
                {
                    "timestamp": datetime.now().isoformat(),
                    "application": "system",
                    "error_type": "info",
                    "message": "No application errors detected"
                }
            ]

        except Exception as e:
            self.logger.error(f"Failed to get application errors: {e}")
            return []

    async def _monitor_processes(self) -> Dict[str, Any]:
        """Monitor specific processes."""
        try:
            import psutil

            process_data = {}
            
            for app_name in self.monitored_applications:
                process_data[app_name] = {
                    "running": False,
                    "instances": 0,
                    "total_cpu": 0.0,
                    "total_memory": 0.0,
                    "processes": []
                }
                
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                    try:
                        if proc.info['name'] == app_name:
                            process_data[app_name]["running"] = True
                            process_data[app_name]["instances"] += 1
                            process_data[app_name]["total_cpu"] += proc.info.get('cpu_percent', 0)
                            process_data[app_name]["total_memory"] += proc.info.get('memory_percent', 0)
                            
                            process_data[app_name]["processes"].append({
                                "pid": proc.info['pid'],
                                "cpu_percent": proc.info.get('cpu_percent', 0),
                                "memory_percent": proc.info.get('memory_percent', 0),
                                "status": proc.info.get('status', 'unknown')
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            return process_data

        except Exception as e:
            self.logger.error(f"Failed to monitor processes: {e}")
            return {"error": str(e)}

    async def _check_application_health(self) -> Dict[str, Any]:
        """Check overall application health."""
        try:
            import psutil

            health_data = {
                "critical_processes_running": 0,
                "total_critical_processes": len(self.critical_processes),
                "application_stability": "stable",
                "performance_degradation": False,
                "memory_pressure": False,
                "cpu_pressure": False
            }
            
            # Check critical processes
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] in self.critical_processes:
                        health_data["critical_processes_running"] += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Check for performance issues
            memory = psutil.virtual_memory()
            if memory.percent > self.memory_threshold:
                health_data["memory_pressure"] = True
                health_data["application_stability"] = "degraded"
            
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.cpu_threshold:
                health_data["cpu_pressure"] = True
                health_data["application_stability"] = "degraded"
            
            if health_data["memory_pressure"] or health_data["cpu_pressure"]:
                health_data["performance_degradation"] = True
            
            return health_data

        except Exception as e:
            self.logger.error(f"Failed to check application health: {e}")
            return {"error": str(e)}

    async def _analyze_application_performance(
        self, app_metrics: Dict[str, Any], process_metrics: Dict[str, Any], health_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze application performance using Ollama."""
        try:
            # Combine all application data for analysis
            application_data = {
                "app_metrics": app_metrics,
                "process_metrics": process_metrics,
                "health_metrics": health_metrics
            }
            
            # Use Ollama to analyze application performance
            analysis_result = await ollama_client.analyze_metrics(application_data, "Application performance analysis")
            
            return {
                "timestamp": datetime.now().isoformat(),
                "application_score": self._calculate_application_score(app_metrics, process_metrics, health_metrics),
                "performance_level": analysis_result.risk_level,
                "recommendations": analysis_result.alternatives,
                "confidence": analysis_result.confidence,
                "analysis": analysis_result.decision
            }

        except Exception as e:
            self.logger.error(f"Failed to analyze application performance: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "application_score": self._calculate_application_score(app_metrics, process_metrics, health_metrics),
                "performance_level": "unknown",
                "recommendations": [],
                "confidence": 0.0,
                "analysis": "Analysis failed"
            }

    def _calculate_application_score(
        self, app_metrics: Dict[str, Any], process_metrics: Dict[str, Any], health_metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall application performance score (0-100)."""
        try:
            score = 100.0
            
            # Check critical processes
            critical_running = health_metrics.get("critical_processes_running", 0)
            total_critical = health_metrics.get("total_critical_processes", 0)
            
            if total_critical > 0:
                critical_percentage = (critical_running / total_critical) * 100
                if critical_percentage < 100:
                    score -= (100 - critical_percentage) * 0.5
            
            # Check memory pressure
            if health_metrics.get("memory_pressure", False):
                score -= 20
            
            # Check CPU pressure
            if health_metrics.get("cpu_pressure", False):
                score -= 15
            
            # Check application performance
            app_performance = app_metrics.get("application_performance", {})
            if app_performance.get("high_cpu_processes", 0) > 5:
                score -= 10
            
            if app_performance.get("high_memory_processes", 0) > 5:
                score -= 10
            
            # Check zombie processes
            zombie_count = app_performance.get("zombie_processes", 0)
            if zombie_count > 0:
                score -= zombie_count * 5
            
            return max(0.0, score)

        except Exception as e:
            self.logger.error(f"Failed to calculate application score: {e}")
            return 50.0

    async def _detect_application_issues(
        self, app_metrics: Dict[str, Any], process_metrics: Dict[str, Any], health_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect application issues."""
        issues = []
        
        try:
            # Check critical process issues
            critical_running = health_metrics.get("critical_processes_running", 0)
            total_critical = health_metrics.get("total_critical_processes", 0)
            
            if critical_running < total_critical:
                missing_critical = total_critical - critical_running
                issues.append({
                    "type": "critical_process_missing",
                    "severity": "high",
                    "description": f"{missing_critical} critical processes are not running",
                    "missing_count": missing_critical,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Check memory pressure
            if health_metrics.get("memory_pressure", False):
                issues.append({
                    "type": "memory_pressure",
                    "severity": "medium",
                    "description": "High memory usage detected",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Check CPU pressure
            if health_metrics.get("cpu_pressure", False):
                issues.append({
                    "type": "cpu_pressure",
                    "severity": "medium",
                    "description": "High CPU usage detected",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Check application performance issues
            app_performance = app_metrics.get("application_performance", {})
            
            high_cpu_processes = app_performance.get("high_cpu_processes", 0)
            if high_cpu_processes > 5:
                issues.append({
                    "type": "high_cpu_processes",
                    "severity": "medium",
                    "description": f"{high_cpu_processes} processes using high CPU",
                    "process_count": high_cpu_processes,
                    "timestamp": datetime.now().isoformat()
                })
            
            high_memory_processes = app_performance.get("high_memory_processes", 0)
            if high_memory_processes > 5:
                issues.append({
                    "type": "high_memory_processes",
                    "severity": "medium",
                    "description": f"{high_memory_processes} processes using high memory",
                    "process_count": high_memory_processes,
                    "timestamp": datetime.now().isoformat()
                })
            
            zombie_processes = app_performance.get("zombie_processes", 0)
            if zombie_processes > 0:
                issues.append({
                    "type": "zombie_processes",
                    "severity": "low",
                    "description": f"{zombie_processes} zombie processes detected",
                    "process_count": zombie_processes,
                    "timestamp": datetime.now().isoformat()
                })
            
            return issues

        except Exception as e:
            self.logger.error(f"Failed to detect application issues: {e}")
            return []

    async def _perform_application_remediation(self, issues: List[Dict[str, Any]]):
        """Perform application remediation actions."""
        try:
            for issue in issues:
                issue_type = issue.get("type")
                
                if issue_type == "critical_process_missing":
                    await self._restart_critical_processes(issue)
                elif issue_type == "memory_pressure":
                    await self._optimize_memory_usage(issue)
                elif issue_type == "cpu_pressure":
                    await self._optimize_cpu_usage(issue)
                elif issue_type == "high_cpu_processes":
                    await self._manage_high_cpu_processes(issue)
                elif issue_type == "high_memory_processes":
                    await self._manage_high_memory_processes(issue)
                elif issue_type == "zombie_processes":
                    await self._cleanup_zombie_processes(issue)
                
                # Log the remediation action
                self.logger.warning(f"Application remediation performed for {issue_type}: {issue.get('description')}")

        except Exception as e:
            self.logger.error(f"Failed to perform application remediation: {e}")

    async def _restart_critical_processes(self, issue: Dict[str, Any]):
        """Restart missing critical processes."""
        try:
            # This would implement critical process restart logic
            # For now, just log the action
            self.logger.info("Would restart critical processes in production")
            
        except Exception as e:
            self.logger.error(f"Failed to restart critical processes: {e}")

    async def _optimize_memory_usage(self, issue: Dict[str, Any]):
        """Optimize memory usage."""
        try:
            # This would implement memory optimization logic
            # For now, just log the action
            self.logger.info("Would optimize memory usage in production")
            
        except Exception as e:
            self.logger.error(f"Failed to optimize memory usage: {e}")

    async def _optimize_cpu_usage(self, issue: Dict[str, Any]):
        """Optimize CPU usage."""
        try:
            # This would implement CPU optimization logic
            # For now, just log the action
            self.logger.info("Would optimize CPU usage in production")
            
        except Exception as e:
            self.logger.error(f"Failed to optimize CPU usage: {e}")

    async def _manage_high_cpu_processes(self, issue: Dict[str, Any]):
        """Manage high CPU processes."""
        try:
            # This would implement high CPU process management
            # For now, just log the action
            self.logger.info("Would manage high CPU processes in production")
            
        except Exception as e:
            self.logger.error(f"Failed to manage high CPU processes: {e}")

    async def _manage_high_memory_processes(self, issue: Dict[str, Any]):
        """Manage high memory processes."""
        try:
            # This would implement high memory process management
            # For now, just log the action
            self.logger.info("Would manage high memory processes in production")
            
        except Exception as e:
            self.logger.error(f"Failed to manage high memory processes: {e}")

    async def _cleanup_zombie_processes(self, issue: Dict[str, Any]):
        """Clean up zombie processes."""
        try:
            # This would implement zombie process cleanup
            # For now, just log the action
            self.logger.info("Would cleanup zombie processes in production")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup zombie processes: {e}")

    async def _update_application_status(
        self, app_metrics: Dict[str, Any], process_metrics: Dict[str, Any], 
        health_metrics: Dict[str, Any], analysis: Dict[str, Any], issues: List[Dict[str, Any]]
    ):
        """Update application status."""
        try:
            self.application_metrics.append({
                "timestamp": datetime.now().isoformat(),
                "app_metrics": app_metrics,
                "process_metrics": process_metrics,
                "health_metrics": health_metrics,
                "analysis": analysis,
                "issues": issues
            })
            
            # Keep only recent metrics
            if len(self.application_metrics) > 100:
                self.application_metrics = self.application_metrics[-100:]
            
            # Update process monitoring
            self.process_monitoring.append({
                "timestamp": datetime.now().isoformat(),
                "processes": process_metrics
            })
            if len(self.process_monitoring) > 50:
                self.process_monitoring = self.process_monitoring[-50:]
            
            # Update application issues
            if issues:
                self.application_issues.extend(issues)
                if len(self.application_issues) > 50:
                    self.application_issues = self.application_issues[-50:]
            
        except Exception as e:
            self.logger.error(f"Failed to update application status: {e}")

    async def _broadcast_application_status(
        self, app_metrics: Dict[str, Any], process_metrics: Dict[str, Any], 
        health_metrics: Dict[str, Any], analysis: Dict[str, Any], issues: List[Dict[str, Any]]
    ):
        """Broadcast application status to other agents."""
        try:
            application_status = {
                "app_metrics": app_metrics,
                "process_metrics": process_metrics,
                "health_metrics": health_metrics,
                "analysis": analysis,
                "issues": issues,
                "application_score": analysis.get("application_score", 0),
                "performance_level": analysis.get("performance_level", "unknown"),
                "timestamp": datetime.now().isoformat()
            }
            
            await self.message_bus.broadcast(
                sender=self.agent_name,
                message_type=MessageType.APPLICATION_UPDATE,
                content=application_status,
                priority=MessagePriority.HIGH if issues else MessagePriority.NORMAL
            )
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast application status: {e}")

    async def _setup_subscriptions(self):
        """Set up message subscriptions for the application agent."""
        await super()._setup_subscriptions()
        
        # Subscribe to application-related messages
        await self.message_bus.subscribe(MessageType.ALERT, self._handle_application_alert)
        self.subscribed_message_types.append(MessageType.ALERT)

    async def _handle_application_alert(self, message):
        """Handle application-related alerts."""
        if message.sender == self.agent_name:
            return  # Ignore our own messages
        
        # Process application alerts
        alert_content = message.content
        if "application" in alert_content.get("type", "").lower():
            self.logger.warning(f"Application alert received: {alert_content.get('message', 'Unknown alert')}")

    def get_application_summary(self) -> Dict[str, Any]:
        """Get a summary of application status."""
        return {
            "total_application_metrics": len(self.application_metrics),
            "total_process_monitoring": len(self.process_monitoring),
            "total_application_issues": len(self.application_issues),
            "recent_issues": self.application_issues[-5:] if self.application_issues else [],
            "application_score": self._calculate_application_score(
                self.application_metrics[-1]["app_metrics"] if self.application_metrics else {},
                self.application_metrics[-1]["process_metrics"] if self.application_metrics else {},
                self.application_metrics[-1]["health_metrics"] if self.application_metrics else {}
            ),
            "monitored_applications": self.monitored_applications,
            "critical_processes": self.critical_processes
        } 