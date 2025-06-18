"""
NetworkAgent - The network specialist that keeps the digital highways flowing.
This agent monitors network performance, connectivity, bandwidth, and network-related issues.
Think of it as your network engineer with a toolkit and a mission to keep data flowing.
"""

import socket
import subprocess
import time
import hashlib
import asyncio
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os

from agents.base_agent import BaseAgent
from utils.message_bus import MessageType, MessagePriority
from utils.ollama_client import ollama_client, truncate_prompt, estimate_token_count
from config import config
from utils.persistence import PersistenceManager


class NetworkAgent(BaseAgent):
    """Agent responsible for network monitoring, performance analysis, and network remediation."""

    def __init__(self):
        super().__init__("network")

        # Force Ollama as the only LLM provider
        self.llm_provider = "ollama"
        self.llm_client = ollama_client

        # Network state
        self.network_metrics: List[Dict[str, Any]] = []
        self.connectivity_tests: List[Dict[str, Any]] = []
        self.bandwidth_tests: List[Dict[str, Any]] = []
        self.network_issues: List[Dict[str, Any]] = []

        # Network monitoring
        self.target_hosts = [
            "8.8.8.8",
            "1.1.1.1",
            "google.com",
        ]  # DNS servers and common sites
        self.bandwidth_threshold = 1.0  # Mbps
        self.latency_threshold = 100  # ms
        self.packet_loss_threshold = 5.0  # %

        # Network interfaces
        self.monitored_interfaces = ["Ethernet", "Wi-Fi"]

        # Persistence integration
        self.persistence_enabled = getattr(config, "persistence_enabled", True)
        self.db_path = getattr(config, "db_path", "data/agent_system.db")
        self.persistence = PersistenceManager(self.db_path)

        self.logger.info(
            "NetworkAgent initialized - ready to monitor network performance"
        )

    async def start(self):
        # Stagger start to avoid LLM spikes
        await asyncio.sleep(random.uniform(0, 10))
        await super().start()

    def _metrics_hash(self, metrics, connectivity, bandwidth):
        import json

        return hashlib.sha256(
            json.dumps(
                {
                    "metrics": metrics,
                    "connectivity": connectivity,
                    "bandwidth": bandwidth,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()

    async def _perform_check(self):
        """Perform network monitoring and analysis."""
        try:
            self.last_check_time = datetime.now()

            # Gather network metrics
            network_metrics = await self._gather_network_metrics()

            # Test connectivity
            connectivity_results = await self._test_connectivity()

            # Test bandwidth
            bandwidth_results = await self._test_bandwidth()

            # Analyze network performance
            performance_analysis = await self._analyze_network_performance(
                network_metrics, connectivity_results, bandwidth_results
            )

            # Detect network issues
            issues = await self._detect_network_issues(
                network_metrics, connectivity_results, bandwidth_results
            )

            # Perform network remediation if needed
            if issues:
                await self._perform_network_remediation(issues)

            # Update network status
            await self._update_network_status(
                network_metrics,
                connectivity_results,
                bandwidth_results,
                performance_analysis,
                issues,
            )

            # Persist network data if enabled
            if self.persistence_enabled:
                try:
                    await self.persistence.insert_analysis(
                        timestamp=datetime.now().isoformat(),
                        agent=self.agent_name,
                        summary=f"Network scan completed - {len(issues)} issues detected",
                        issues=str(issues),
                    )
                except Exception as e:
                    self.logger.error(f"Failed to persist network data: {e}")

            # Broadcast network status
            await self._broadcast_network_status(
                network_metrics,
                connectivity_results,
                bandwidth_results,
                performance_analysis,
                issues,
            )

            self.success_count += 1

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to perform network check: {e}")
            self.add_issue(f"Network check failed: {str(e)}", "high")

    async def _gather_network_metrics(self) -> Dict[str, Any]:
        """Gather comprehensive network metrics."""
        try:
            import psutil

            metrics = {
                "timestamp": datetime.now().isoformat(),
                "interfaces": await self._get_network_interfaces(),
                "connections": await self._get_network_connections(),
                "bandwidth_usage": await self._get_bandwidth_usage(),
                "dns_status": await self._test_dns_resolution(),
                "routing_table": await self._get_routing_table(),
                "network_errors": await self._get_network_errors(),
            }

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to gather network metrics: {e}")
            return {"error": str(e)}

    async def _get_network_interfaces(self) -> List[Dict[str, Any]]:
        """Get network interface information."""
        try:
            import psutil

            interfaces = []

            for interface, stats in psutil.net_if_stats().items():
                if interface in self.monitored_interfaces or any(
                    monitored in interface for monitored in self.monitored_interfaces
                ):
                    try:
                        addresses = psutil.net_if_addrs().get(interface, [])
                        interface_info = {
                            "name": interface,
                            "status": "up" if stats.isup else "down",
                            "speed": stats.speed if stats.speed > 0 else "unknown",
                            "mtu": stats.mtu,
                            "addresses": [
                                {
                                    "family": addr.family.name,
                                    "address": addr.address,
                                    "netmask": addr.netmask,
                                }
                                for addr in addresses
                            ],
                        }
                        interfaces.append(interface_info)
                    except Exception as e:
                        self.logger.error(
                            f"Failed to get interface info for {interface}: {e}"
                        )

            return interfaces

        except Exception as e:
            self.logger.error(f"Failed to get network interfaces: {e}")
            return []

    async def _get_network_connections(self) -> Dict[str, Any]:
        """Get network connection statistics."""
        try:
            import psutil

            connections = psutil.net_connections()

            # Categorize connections
            established = [c for c in connections if c.status == "ESTABLISHED"]
            listening = [c for c in connections if c.status == "LISTEN"]
            time_wait = [c for c in connections if c.status == "TIME_WAIT"]

            return {
                "total_connections": len(connections),
                "established": len(established),
                "listening": len(listening),
                "time_wait": len(time_wait),
                "connections_by_status": {
                    "ESTABLISHED": len(established),
                    "LISTEN": len(listening),
                    "TIME_WAIT": len(time_wait),
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get network connections: {e}")
            return {"error": str(e)}

    async def _get_bandwidth_usage(self) -> Dict[str, Any]:
        """Get current bandwidth usage."""
        try:
            import psutil

            # Get network I/O counters
            net_io = psutil.net_io_counters()

            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout,
            }

        except Exception as e:
            self.logger.error(f"Failed to get bandwidth usage: {e}")
            return {"error": str(e)}

    async def _test_dns_resolution(self) -> Dict[str, Any]:
        """Test DNS resolution."""
        try:
            test_domains = ["google.com", "microsoft.com", "github.com"]
            dns_results = {}

            for domain in test_domains:
                try:
                    start_time = time.time()
                    ip_address = socket.gethostbyname(domain)
                    resolution_time = (time.time() - start_time) * 1000  # Convert to ms

                    dns_results[domain] = {
                        "resolved": True,
                        "ip_address": ip_address,
                        "resolution_time_ms": resolution_time,
                    }
                except socket.gaierror:
                    dns_results[domain] = {
                        "resolved": False,
                        "error": "DNS resolution failed",
                    }

            return dns_results

        except Exception as e:
            self.logger.error(f"Failed to test DNS resolution: {e}")
            return {"error": str(e)}

    async def _get_routing_table(self) -> List[Dict[str, Any]]:
        """Get routing table information."""
        try:
            import psutil

            routes = []

            # Get routing table (simplified)
            try:
                # This is a simplified approach - in production you'd use more detailed routing info
                routes.append(
                    {
                        "destination": "default",
                        "gateway": "0.0.0.0",
                        "interface": "default",
                    }
                )
            except Exception:
                pass

            return routes

        except Exception as e:
            self.logger.error(f"Failed to get routing table: {e}")
            return []

    async def _get_network_errors(self) -> Dict[str, Any]:
        """Get network error statistics."""
        try:
            import psutil

            net_io = psutil.net_io_counters()

            return {
                "errors_in": net_io.errin,
                "errors_out": net_io.errout,
                "drops_in": net_io.dropin,
                "drops_out": net_io.dropout,
            }

        except Exception as e:
            self.logger.error(f"Failed to get network errors: {e}")
            return {"error": str(e)}

    async def _test_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to target hosts."""
        try:
            connectivity_results = {}

            for host in self.target_hosts:
                try:
                    # Test ping
                    ping_result = await self._ping_host(host)

                    # Test port connectivity (common ports)
                    port_results = await self._test_ports(host, [80, 443, 53])

                    connectivity_results[host] = {
                        "ping": ping_result,
                        "ports": port_results,
                        "overall_status": (
                            "reachable" if ping_result.get("success") else "unreachable"
                        ),
                    }

                except Exception as e:
                    connectivity_results[host] = {
                        "error": str(e),
                        "overall_status": "error",
                    }

            return connectivity_results

        except Exception as e:
            self.logger.error(f"Failed to test connectivity: {e}")
            return {"error": str(e)}

    async def _ping_host(self, host: str) -> Dict[str, Any]:
        """Ping a host to test connectivity."""
        try:
            if os.name == "nt":  # Windows
                cmd = ["ping", "-n", "1", "-w", "1000", host]
            else:  # Unix/Linux
                cmd = ["ping", "-c", "1", "-W", "1", host]

            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            ping_time = (time.time() - start_time) * 1000  # Convert to ms

            if result.returncode == 0:
                # Extract ping time from output
                output_lines = result.stdout.split("\n")
                for line in output_lines:
                    if "time=" in line or "time<" in line:
                        try:
                            # Extract time value
                            time_part = (
                                line.split("time=")[1].split()[0]
                                if "time=" in line
                                else "1"
                            )
                            ping_time = float(time_part.replace("ms", ""))
                        except:
                            pass
                        break

                return {"success": True, "latency_ms": ping_time, "packet_loss": 0.0}
            else:
                return {"success": False, "latency_ms": None, "packet_loss": 100.0}

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "latency_ms": None,
                "packet_loss": 100.0,
                "error": "Timeout",
            }
        except Exception as e:
            return {
                "success": False,
                "latency_ms": None,
                "packet_loss": 100.0,
                "error": str(e),
            }

    async def _test_ports(self, host: str, ports: List[int]) -> Dict[str, Any]:
        """Test port connectivity."""
        try:
            port_results = {}

            for port in ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((host, port))
                    sock.close()

                    port_results[port] = {
                        "open": result == 0,
                        "status": "open" if result == 0 else "closed",
                    }
                except Exception as e:
                    port_results[port] = {
                        "open": False,
                        "status": "error",
                        "error": str(e),
                    }

            return port_results

        except Exception as e:
            self.logger.error(f"Failed to test ports for {host}: {e}")
            return {"error": str(e)}

    async def _test_bandwidth(self) -> Dict[str, Any]:
        """Test network bandwidth."""
        try:
            # This is a simplified bandwidth test
            # In production, you'd use tools like iperf or speedtest-cli

            bandwidth_results = {
                "download_speed_mbps": 0.0,
                "upload_speed_mbps": 0.0,
                "test_time": datetime.now().isoformat(),
                "status": "not_implemented",
            }

            return bandwidth_results

        except Exception as e:
            self.logger.error(f"Failed to test bandwidth: {e}")
            return {"error": str(e)}

    async def _analyze_network_performance(
        self,
        metrics: Dict[str, Any],
        connectivity: Dict[str, Any],
        bandwidth: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze network performance using Ollama."""
        # Throttle/caching logic
        if not hasattr(self, "analysis_cache"):
            self.analysis_cache = {}
        cache_ttl = 300  # 5 min
        now = datetime.now()
        metrics_hash = self._metrics_hash(metrics, connectivity, bandwidth)
        cached = self.analysis_cache.get(metrics_hash)
        if cached and (now - datetime.fromisoformat(cached["timestamp"])) < timedelta(
            seconds=cache_ttl
        ):
            return cached["result"]
        try:
            network_data = {
                "metrics": metrics,
                "connectivity": connectivity,
                "bandwidth": bandwidth,
            }
            # Truncate prompt if needed
            import json
            prompt_str = truncate_prompt(json.dumps(network_data), max_tokens=4096)
            self.logger.debug(f"Ollama prompt length: {estimate_token_count(prompt_str)} tokens")
            # Validate input data
            if not isinstance(metrics, dict) or not isinstance(connectivity, dict) or not isinstance(bandwidth, dict):
                self.logger.error("Invalid input data for LLM analysis")
                return {"error": "Invalid input data for LLM analysis"}
            analysis_result = await self.llm_client.analyze_metrics(
                network_data, "Network performance analysis"
            )
            if hasattr(analysis_result, "dict"):
                analysis_result = analysis_result.dict()
            if not isinstance(analysis_result, dict):
                self.logger.error(f"LLM analysis did not return a dict: {type(analysis_result)}")
                return {
                    "timestamp": now.isoformat(),
                    "network_score": self._calculate_network_score(
                        metrics, connectivity, bandwidth
                    ),
                    "performance_level": "unknown",
                    "recommendations": [],
                    "confidence": 0.0,
                    "analysis": "Analysis failed (invalid LLM result)",
                }
            result = {
                "timestamp": now.isoformat(),
                "network_score": self._calculate_network_score(
                    metrics, connectivity, bandwidth
                ),
                "performance_level": analysis_result.get("risk_level", "unknown"),
                "recommendations": analysis_result.get("alternatives", []),
                "confidence": analysis_result.get("confidence", 0.0),
                "analysis": analysis_result.get("decision", "Analysis failed"),
            }
            self.analysis_cache[metrics_hash] = {
                "result": result,
                "timestamp": now.isoformat(),
            }
            return result
        except Exception as e:
            self.logger.error(f"Failed to analyze network performance: {e}")
            return {
                "timestamp": now.isoformat(),
                "network_score": self._calculate_network_score(
                    metrics, connectivity, bandwidth
                ),
                "performance_level": "unknown",
                "recommendations": [],
                "confidence": 0.0,
                "analysis": "Analysis failed",
            }

    def _calculate_network_score(
        self,
        metrics: Dict[str, Any],
        connectivity: Dict[str, Any],
        bandwidth: Dict[str, Any],
    ) -> float:
        """Calculate overall network performance score (0-100)."""
        try:
            score = 100.0

            # Check connectivity
            reachable_hosts = 0
            total_hosts = len(connectivity)

            for host, result in connectivity.items():
                if result.get("overall_status") == "reachable":
                    reachable_hosts += 1

                    # Check latency
                    ping_result = result.get("ping", {})
                    if ping_result.get("latency_ms", 0) > self.latency_threshold:
                        score -= 10

            # Penalize for unreachable hosts
            if total_hosts > 0:
                connectivity_percentage = (reachable_hosts / total_hosts) * 100
                if connectivity_percentage < 100:
                    score -= (100 - connectivity_percentage) * 0.5

            # Check network errors
            network_errors = metrics.get("network_errors", {})
            if (
                network_errors.get("errors_in", 0) > 0
                or network_errors.get("errors_out", 0) > 0
            ):
                score -= 15

            # Check DNS resolution
            dns_status = metrics.get("dns_status", {})
            dns_failures = sum(
                1 for result in dns_status.values() if not result.get("resolved", True)
            )
            if dns_failures > 0:
                score -= 10 * dns_failures

            return max(0.0, score)

        except Exception as e:
            self.logger.error(f"Failed to calculate network score: {e}")
            return 50.0

    async def _detect_network_issues(
        self,
        metrics: Dict[str, Any],
        connectivity: Dict[str, Any],
        bandwidth: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Detect network issues."""
        issues = []

        try:
            # Check connectivity issues
            for host, result in connectivity.items():
                if result.get("overall_status") != "reachable":
                    issues.append(
                        {
                            "type": "connectivity_issue",
                            "severity": "high",
                            "description": f"Host {host} is unreachable",
                            "host": host,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                else:
                    # Check latency issues
                    ping_result = result.get("ping", {})
                    if ping_result.get("latency_ms", 0) > self.latency_threshold:
                        issues.append(
                            {
                                "type": "high_latency",
                                "severity": "medium",
                                "description": f"High latency to {host}: {ping_result.get('latency_ms')}ms",
                                "host": host,
                                "latency_ms": ping_result.get("latency_ms"),
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

            # Check network errors
            network_errors = metrics.get("network_errors", {})
            if network_errors.get("errors_in", 0) > 0:
                issues.append(
                    {
                        "type": "network_errors",
                        "severity": "medium",
                        "description": f"Network input errors: {network_errors.get('errors_in')}",
                        "error_count": network_errors.get("errors_in"),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            if network_errors.get("errors_out", 0) > 0:
                issues.append(
                    {
                        "type": "network_errors",
                        "severity": "medium",
                        "description": f"Network output errors: {network_errors.get('errors_out')}",
                        "error_count": network_errors.get("errors_out"),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # Check DNS issues
            dns_status = metrics.get("dns_status", {})
            for domain, result in dns_status.items():
                if not result.get("resolved", True):
                    issues.append(
                        {
                            "type": "dns_issue",
                            "severity": "medium",
                            "description": f"DNS resolution failed for {domain}",
                            "domain": domain,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

            return issues

        except Exception as e:
            self.logger.error(f"Failed to detect network issues: {e}")
            return []

    async def _perform_network_remediation(self, issues: List[Dict[str, Any]]):
        """Perform network remediation actions."""
        try:
            for issue in issues:
                issue_type = issue.get("type")

                if issue_type == "connectivity_issue":
                    await self._restart_network_interface(issue)
                elif issue_type == "dns_issue":
                    await self._flush_dns_cache(issue)
                elif issue_type == "network_errors":
                    await self._reset_network_stack(issue)

                # Log the remediation action
                self.logger.warning(
                    f"Network remediation performed for {issue_type}: {issue.get('description')}"
                )

        except Exception as e:
            self.logger.error(f"Failed to perform network remediation: {e}")

    async def _restart_network_interface(self, issue: Dict[str, Any]):
        """Restart network interface."""
        try:
            # This would implement interface restart logic
            # For now, just log the action
            self.logger.info("Would restart network interface in production")

        except Exception as e:
            self.logger.error(f"Failed to restart network interface: {e}")

    async def _flush_dns_cache(self, issue: Dict[str, Any]):
        """Flush DNS cache."""
        try:
            if os.name == "nt":  # Windows
                cmd = ["ipconfig", "/flushdns"]
                subprocess.run(cmd, capture_output=True, timeout=10)
                self.logger.info("DNS cache flushed")
            else:  # Unix/Linux
                cmd = ["sudo", "systemctl", "restart", "systemd-resolved"]
                subprocess.run(cmd, capture_output=True, timeout=10)
                self.logger.info("DNS resolver restarted")

        except Exception as e:
            self.logger.error(f"Failed to flush DNS cache: {e}")

    async def _reset_network_stack(self, issue: Dict[str, Any]):
        """Reset network stack."""
        try:
            # This would implement network stack reset logic
            # For now, just log the action
            self.logger.info("Would reset network stack in production")

        except Exception as e:
            self.logger.error(f"Failed to reset network stack: {e}")

    async def _update_network_status(
        self,
        metrics: Dict[str, Any],
        connectivity: Dict[str, Any],
        bandwidth: Dict[str, Any],
        analysis: Dict[str, Any],
        issues: List[Dict[str, Any]],
    ):
        """Update network status."""
        try:
            self.network_metrics.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics,
                    "connectivity": connectivity,
                    "bandwidth": bandwidth,
                    "analysis": analysis,
                    "issues": issues,
                }
            )

            # Keep only recent metrics
            if len(self.network_metrics) > 100:
                self.network_metrics = self.network_metrics[-100:]

            # Update connectivity tests
            self.connectivity_tests.append(
                {"timestamp": datetime.now().isoformat(), "results": connectivity}
            )
            if len(self.connectivity_tests) > 50:
                self.connectivity_tests = self.connectivity_tests[-50:]

            # Update network issues
            if issues:
                self.network_issues.extend(issues)
                if len(self.network_issues) > 50:
                    self.network_issues = self.network_issues[-50:]

        except Exception as e:
            self.logger.error(f"Failed to update network status: {e}")

    async def _broadcast_network_status(
        self,
        metrics: Dict[str, Any],
        connectivity: Dict[str, Any],
        bandwidth: Dict[str, Any],
        analysis: Dict[str, Any],
        issues: List[Dict[str, Any]],
    ):
        """Broadcast network status to other agents."""
        try:
            network_status = {
                "metrics": metrics,
                "connectivity": connectivity,
                "bandwidth": bandwidth,
                "analysis": analysis,
                "issues": issues,
                "network_score": analysis.get("network_score", 0),
                "performance_level": analysis.get("performance_level", "unknown"),
                "timestamp": datetime.now().isoformat(),
            }

            await self.message_bus.broadcast(
                sender=self.agent_name,
                message_type=MessageType.NETWORK_UPDATE,
                content=network_status,
                priority=MessagePriority.HIGH if issues else MessagePriority.NORMAL,
            )

        except Exception as e:
            self.logger.error(f"Failed to broadcast network status: {e}")

    async def _setup_subscriptions(self):
        """Set up message subscriptions for the network agent."""
        await super()._setup_subscriptions()

        # Subscribe to network-related messages
        await self.message_bus.subscribe(MessageType.ALERT, self._handle_network_alert)
        self.subscribed_message_types.append(MessageType.ALERT)

    async def _handle_network_alert(self, message):
        """Handle network-related alerts."""
        if message.sender == self.agent_name:
            return  # Ignore our own messages

        # Process network alerts
        alert_content = message.content
        if "network" in alert_content.get("type", "").lower():
            self.logger.warning(
                f"Network alert received: {alert_content.get('message', 'Unknown alert')}"
            )

    def get_network_summary(self) -> Dict[str, Any]:
        """Get a summary of network status."""
        return {
            "total_network_metrics": len(self.network_metrics),
            "total_connectivity_tests": len(self.connectivity_tests),
            "total_network_issues": len(self.network_issues),
            "recent_issues": self.network_issues[-5:] if self.network_issues else [],
            "network_score": self._calculate_network_score(
                self.network_metrics[-1]["metrics"] if self.network_metrics else {},
                (
                    self.network_metrics[-1]["connectivity"]
                    if self.network_metrics
                    else {}
                ),
                self.network_metrics[-1]["bandwidth"] if self.network_metrics else {},
            ),
            "target_hosts": self.target_hosts,
        }

    async def _analyze_trends_llm(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in network metrics using Ollama only (LLM-based)."""
        if len(metrics) < 3:
            return {"error": "Insufficient data for trend analysis"}
        try:
            latest_metrics = metrics[-1]
            historical_context = metrics[:-1] if len(metrics) > 1 else []
            gpt_decision = await self.llm_client.detect_anomalies(latest_metrics, historical_context)
            trends = {
                "timestamp": datetime.now().isoformat(),
                "trend_analysis": {
                    "decision": gpt_decision.decision,
                    "reasoning": gpt_decision.reasoning,
                    "confidence": gpt_decision.confidence,
                    "risk_level": gpt_decision.risk_level,
                    "anomalies_detected": gpt_decision.metadata.get("anomalies_detected", []),
                    "severity": gpt_decision.metadata.get("severity", "unknown"),
                    "affected_metrics": gpt_decision.metadata.get("affected_metrics", []),
                },
                # Optionally add calculated trends if needed
            }
            return trends
        except Exception as e:
            self.logger.error(f"Trend analysis failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": f"Trend analysis failed: {str(e)}",
            }
