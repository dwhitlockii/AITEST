"""
SensorAgent - The eyes and ears of the system.
This agent gathers all the metrics that other agents need to make intelligent decisions.
Think of it as the surveillance system that never sleeps.
"""

import psutil
import subprocess
import platform
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from agents.base_agent import BaseAgent
from utils.message_bus import MessageType, MessagePriority
from config import config
from utils.persistence import PersistenceManager


class SensorAgent(BaseAgent):
    """Agent responsible for gathering system metrics and sensor data."""

    def __init__(self):
        super().__init__("SensorAgent")

        # Metric collection state
        self.metric_history: List[Dict[str, Any]] = []
        self.max_history_size = 100

        # Windows-specific monitoring
        self.is_windows = platform.system() == "Windows"

        # Service monitoring cache
        self.service_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 30  # seconds

        # Persistence integration
        self.persistence_enabled = getattr(config, "persistence_enabled", True)
        self.db_path = getattr(config, "db_path", "data/agent_system.db")
        self.persistence = PersistenceManager(self.db_path)

        self.logger.info(
            "SensorAgent initialized - ready to gather system intelligence"
        )

    async def _perform_check(self):
        """Gather all system metrics and broadcast them."""
        try:
            self.last_check_time = datetime.now()

            # Gather comprehensive system metrics
            metrics = await self._gather_system_metrics()

            # Add to history
            self.metric_history.append(metrics)
            if len(self.metric_history) > self.max_history_size:
                self.metric_history.pop(0)

            # Persist metrics if enabled
            if self.persistence_enabled:
                try:
                    await self.persistence.insert_metric(
                        timestamp=metrics["timestamp"],
                        agent=self.agent_name,
                        metric_type="system_metrics",
                        value=str(
                            metrics
                        ),  # Store as stringified dict (could use json.dumps)
                    )
                except Exception as e:
                    self.logger.error(f"Failed to persist metrics: {e}")
                    self.add_issue(f"Persistence error: {str(e)}", "high")

            # Broadcast metrics to other agents
            await self.message_bus.broadcast(
                sender=self.agent_name,
                message_type=MessageType.METRIC_DATA,
                content=metrics,
                priority=MessagePriority.NORMAL,
            )
            self.logger.info("Broadcasted metrics to message bus")

            # Log key metrics
            self._log_key_metrics(metrics)

            self.success_count += 1

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to gather metrics: {e}")
            self.add_issue(f"Metric collection failed: {str(e)}", "high")

    async def _gather_system_metrics(self) -> Dict[str, Any]:
        """Gather comprehensive system metrics."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system_info": await self._get_system_info(),
            "cpu": await self._get_cpu_metrics(),
            "memory": await self._get_memory_metrics(),
            "disk": await self._get_disk_metrics(),
            "network": await self._get_network_metrics(),
            "services": await self._get_service_metrics(),
            "processes": await self._get_process_metrics(),
            "performance": await self._get_performance_metrics(),
        }

        return metrics

    async def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        try:
            return {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.architecture()[0],
                "hostname": platform.node(),
                "processor": platform.processor(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                "uptime": time.time() - psutil.boot_time(),
            }
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {"error": str(e)}

    async def _get_cpu_metrics(self) -> Dict[str, Any]:
        """Get CPU-related metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            # Get per-CPU usage
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)

            # Get CPU load average (if available)
            try:
                load_avg = psutil.getloadavg()
            except AttributeError:
                load_avg = None

            metrics = {
                "usage_percent": cpu_percent,
                "core_count": cpu_count,
                "per_core_usage": cpu_per_core,
                "frequency_mhz": cpu_freq.current if cpu_freq else None,
                "load_average": load_avg,
                "thresholds": {
                    "warning": config.thresholds.cpu_warning,
                    "critical": config.thresholds.cpu_critical,
                },
            }

            # Log CPU usage with personality
            if cpu_percent > config.thresholds.cpu_critical:
                self.logger.warning(
                    f"CPU's spiking harder than my coffee intake: {cpu_percent}%"
                )
            elif cpu_percent > config.thresholds.cpu_warning:
                self.logger.info(f"CPU usage getting warm: {cpu_percent}%")

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to get CPU metrics: {e}")
            return {"error": str(e)}

    async def _get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory-related metrics."""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            metrics = {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "usage_percent": memory.percent,
                "swap_total_gb": swap.total / (1024**3),
                "swap_used_gb": swap.used / (1024**3),
                "swap_usage_percent": swap.percent,
                "thresholds": {
                    "warning": config.thresholds.memory_warning,
                    "critical": config.thresholds.memory_critical,
                },
            }

            # Log memory usage with personality
            if memory.percent > config.thresholds.memory_critical:
                self.logger.warning(
                    f"Memory usage is through the roof: {memory.percent}%"
                )
            elif memory.percent > config.thresholds.memory_warning:
                self.logger.info(f"Memory getting a bit tight: {memory.percent}%")

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to get memory metrics: {e}")
            return {"error": str(e)}

    async def _get_disk_metrics(self) -> Dict[str, Any]:
        """Get disk-related metrics."""
        try:
            disk_metrics = {}

            for path in config.monitoring.disk_paths:
                try:
                    usage = psutil.disk_usage(path)
                    io_counters = psutil.disk_io_counters()

                    disk_metrics[path] = {
                        "total_gb": usage.total / (1024**3),
                        "used_gb": usage.used / (1024**3),
                        "free_gb": usage.free / (1024**3),
                        "usage_percent": usage.percent,
                        "read_bytes": io_counters.read_bytes if io_counters else 0,
                        "write_bytes": io_counters.write_bytes if io_counters else 0,
                        "read_count": io_counters.read_count if io_counters else 0,
                        "write_count": io_counters.write_count if io_counters else 0,
                        "thresholds": {
                            "warning": config.thresholds.disk_warning,
                            "critical": config.thresholds.disk_critical,
                        },
                    }

                    # Log disk usage with personality
                    if usage.percent > config.thresholds.disk_critical:
                        self.logger.warning(
                            f"Disk {path} is fuller than a Thanksgiving turkey: {usage.percent}%"
                        )
                    elif usage.percent > config.thresholds.disk_warning:
                        self.logger.info(f"Disk {path} getting cozy: {usage.percent}%")

                except Exception as e:
                    self.logger.error(f"Failed to get disk metrics for {path}: {e}")
                    disk_metrics[path] = {"error": str(e)}

            return disk_metrics

        except Exception as e:
            self.logger.error(f"Failed to get disk metrics: {e}")
            return {"error": str(e)}

    async def _get_network_metrics(self) -> Dict[str, Any]:
        """Get network-related metrics."""
        try:
            network_metrics = {}

            # Get network interfaces
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            net_io_counters = psutil.net_io_counters(pernic=True)

            for interface in config.monitoring.network_interfaces:
                try:
                    if interface in net_if_addrs:
                        addrs = net_if_addrs[interface]
                        stats = net_if_stats.get(interface, {})
                        io = net_io_counters.get(interface, {})

                        network_metrics[interface] = {
                            "addresses": [
                                addr.address for addr in addrs if addr.family == 2
                            ],  # IPv4
                            "is_up": stats.isup if stats else False,
                            "speed_mbps": stats.speed if stats else None,
                            "bytes_sent": io.bytes_sent if io else 0,
                            "bytes_recv": io.bytes_recv if io else 0,
                            "packets_sent": io.packets_sent if io else 0,
                            "packets_recv": io.packets_recv if io else 0,
                            "error_in": io.errin if io else 0,
                            "error_out": io.errout if io else 0,
                            "drop_in": io.dropin if io else 0,
                            "drop_out": io.dropout if io else 0,
                        }
                    else:
                        network_metrics[interface] = {"error": "Interface not found"}

                except Exception as e:
                    self.logger.error(
                        f"Failed to get network metrics for {interface}: {e}"
                    )
                    network_metrics[interface] = {"error": str(e)}

            return network_metrics

        except Exception as e:
            self.logger.error(f"Failed to get network metrics: {e}")
            return {"error": str(e)}

    async def _get_service_metrics(self) -> Dict[str, Any]:
        """Get Windows service metrics."""
        try:
            service_metrics = {}

            if not self.is_windows:
                return {"note": "Service monitoring only available on Windows"}

            for service_name in config.monitoring.services_to_monitor:
                try:
                    # Check if we have cached data that's still valid
                    if (
                        service_name in self.service_cache
                        and (
                            datetime.now()
                            - self.service_cache[service_name]["timestamp"]
                        ).seconds
                        < self.cache_ttl
                    ):
                        service_metrics[service_name] = self.service_cache[
                            service_name
                        ]["data"]
                        continue

                    # Query service status using sc command
                    result = subprocess.run(
                        ["sc", "query", service_name],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    service_data = {
                        "status": "unknown",
                        "start_type": "unknown",
                        "running": False,
                        "last_check": datetime.now().isoformat(),
                    }

                    if result.returncode == 0:
                        output = result.stdout.lower()

                        # Parse service status
                        if "running" in output:
                            service_data["status"] = "running"
                            service_data["running"] = True
                        elif "stopped" in output:
                            service_data["status"] = "stopped"
                        elif "paused" in output:
                            service_data["status"] = "paused"

                        # Parse start type
                        if "automatic" in output:
                            service_data["start_type"] = "automatic"
                        elif "manual" in output:
                            service_data["start_type"] = "manual"
                        elif "disabled" in output:
                            service_data["start_type"] = "disabled"

                    service_metrics[service_name] = service_data

                    # Cache the result
                    self.service_cache[service_name] = {
                        "data": service_data,
                        "timestamp": datetime.now(),
                    }

                    # Log service status with personality
                    if not service_data["running"]:
                        self.logger.warning(f"Service {service_name} is taking a nap")

                except subprocess.TimeoutExpired:
                    self.logger.error(
                        f"Timeout getting service status for {service_name}"
                    )
                    service_metrics[service_name] = {"error": "timeout"}
                except Exception as e:
                    self.logger.error(
                        f"Failed to get service metrics for {service_name}: {e}"
                    )
                    service_metrics[service_name] = {"error": str(e)}

            return service_metrics

        except Exception as e:
            self.logger.error(f"Failed to get service metrics: {e}")
            return {"error": str(e)}

    async def _get_process_metrics(self) -> Dict[str, Any]:
        """Get process-related metrics."""
        try:
            # Get top processes by CPU and memory usage
            processes = []

            for proc in psutil.process_iter(
                ["pid", "name", "cpu_percent", "memory_percent", "status"]
            ):
                try:
                    proc_info = proc.info
                    if proc_info["cpu_percent"] > 0 or proc_info["memory_percent"] > 0:
                        processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU usage and get top 10
            top_cpu = sorted(processes, key=lambda x: x["cpu_percent"], reverse=True)[
                :10
            ]
            top_memory = sorted(
                processes, key=lambda x: x["memory_percent"], reverse=True
            )[:10]

            return {
                "total_processes": len(psutil.pids()),
                "top_cpu_processes": top_cpu,
                "top_memory_processes": top_memory,
            }

        except Exception as e:
            self.logger.error(f"Failed to get process metrics: {e}")
            return {"error": str(e)}

    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get overall system performance metrics."""
        try:
            # Calculate system load score (0-100)
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent

            # Simple load calculation
            system_load = (cpu_usage + memory_usage) / 2

            # Determine system health
            if system_load > 80:
                health_status = "critical"
            elif system_load > 60:
                health_status = "warning"
            elif system_load > 30:
                health_status = "normal"
            else:
                health_status = "excellent"

            return {
                "system_load_score": system_load,
                "health_status": health_status,
                "performance_trend": self._calculate_performance_trend(),
                "bottlenecks": self._identify_bottlenecks(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e)}

    def _calculate_performance_trend(self) -> str:
        """Calculate performance trend based on recent history."""
        if len(self.metric_history) < 3:
            return "insufficient_data"

        recent_loads = []
        for metrics in self.metric_history[-3:]:
            if (
                "performance" in metrics
                and "system_load_score" in metrics["performance"]
            ):
                recent_loads.append(metrics["performance"]["system_load_score"])

        if len(recent_loads) < 2:
            return "insufficient_data"

        # Calculate trend
        if recent_loads[-1] > recent_loads[0] * 1.1:
            return "increasing"
        elif recent_loads[-1] < recent_loads[0] * 0.9:
            return "decreasing"
        else:
            return "stable"

    def _identify_bottlenecks(self) -> List[str]:
        """Identify system bottlenecks."""
        bottlenecks = []

        try:
            # Check CPU
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > config.thresholds.cpu_warning:
                bottlenecks.append(f"High CPU usage: {cpu_percent}%")

            # Check memory
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > config.thresholds.memory_warning:
                bottlenecks.append(f"High memory usage: {memory_percent}%")

            # Check disk
            for path in config.monitoring.disk_paths:
                try:
                    disk_usage = psutil.disk_usage(path).percent
                    if disk_usage > config.thresholds.disk_warning:
                        bottlenecks.append(f"High disk usage on {path}: {disk_usage}%")
                except Exception as e:
                    self.logger.error(f"Failed to check disk usage for {path}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to identify bottlenecks: {e}")

        return bottlenecks

    def _log_key_metrics(self, metrics: Dict[str, Any]):
        """Log key metrics with personality."""
        try:
            # Log CPU
            if "cpu" in metrics and "usage_percent" in metrics["cpu"]:
                self.log_metric(
                    "CPU Usage",
                    metrics["cpu"]["usage_percent"],
                    config.thresholds.cpu_warning,
                )
            # Log memory
            if "memory" in metrics and "usage_percent" in metrics["memory"]:
                self.log_metric(
                    "Memory Usage",
                    metrics["memory"]["usage_percent"],
                    config.thresholds.memory_warning,
                )
            # Log disk
            for path, disk_data in metrics.get("disk", {}).items():
                if "usage_percent" in disk_data:
                    self.log_metric(
                        f"Disk Usage ({path})",
                        disk_data["usage_percent"],
                        config.thresholds.disk_warning,
                    )
            # Log system load
            if (
                "performance" in metrics
                and "system_load_score" in metrics["performance"]
            ):
                load_score = metrics["performance"]["system_load_score"]
                self.log_metric("System Load", load_score, None)
        except Exception as e:
            self.logger.error(f"Failed to log key metrics: {e}")

    def get_metric_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent metric history."""
        return self.metric_history[-limit:] if self.metric_history else []

    def get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """Get the most recent metrics."""
        return self.metric_history[-1] if self.metric_history else None
