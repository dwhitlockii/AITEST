"""
SecurityAgent - The digital guardian that watches for threats and protects the system.
This agent monitors security events, detects anomalies, and manages security-related remediation.
Think of it as your cybersecurity specialist with a badge and a mission.
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


class SecurityAgent(BaseAgent):
    """Agent responsible for security monitoring, threat detection, and security remediation."""

    def __init__(self):
        super().__init__("security")

        # Force Ollama as the only LLM provider
        self.llm_provider = "ollama"
        self.llm_client = ollama_client

        # Security state
        self.security_events: List[Dict[str, Any]] = []
        self.threat_detections: List[Dict[str, Any]] = []
        self.security_incidents: List[Dict[str, Any]] = []
        self.blocked_ips: List[str] = []
        self.suspicious_processes: List[str] = []

        # Security thresholds
        self.failed_login_threshold = 5
        self.suspicious_activity_threshold = 3
        self.port_scan_threshold = 10

        # Security monitoring
        self.last_security_scan = None
        self.security_scan_interval = 300  # 5 minutes

        # Persistence integration
        self.persistence_enabled = getattr(config, "persistence_enabled", True)
        self.db_path = getattr(config, "db_path", "data/agent_system.db")
        self.persistence = PersistenceManager(self.db_path)

        self.logger.info("SecurityAgent initialized - ready to protect the system")

    async def _perform_check(self):
        """Perform security monitoring and threat detection."""
        try:
            self.last_check_time = datetime.now()

            # Gather security metrics
            security_metrics = await self._gather_security_metrics()

            # Analyze security data
            security_analysis = await self._analyze_security_data(security_metrics)

            # Detect threats
            threats = await self._detect_threats(security_metrics)

            # Perform security remediation if needed
            if threats:
                await self._perform_security_remediation(threats)

            # Update security status
            await self._update_security_status(security_metrics, security_analysis, threats)

            # Persist security data if enabled
            if self.persistence_enabled:
                try:
                    await self.persistence.insert_analysis(
                        timestamp=datetime.now().isoformat(),
                        agent=self.agent_name,
                        summary=f"Security scan completed - {len(threats)} threats detected",
                        issues=str(threats),
                    )
                except Exception as e:
                    self.logger.error(f"Failed to persist security data: {e}")

            # Broadcast security status
            await self._broadcast_security_status(security_metrics, security_analysis, threats)

            self.success_count += 1

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to perform security check: {e}")
            self.add_issue(f"Security check failed: {str(e)}", "high")

    async def _gather_security_metrics(self) -> Dict[str, Any]:
        """Gather comprehensive security metrics."""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "failed_logins": await self._get_failed_logins(),
                "suspicious_processes": await self._get_suspicious_processes(),
                "network_connections": await self._get_network_connections(),
                "open_ports": await self._get_open_ports(),
                "file_integrity": await self._check_file_integrity(),
                "user_activity": await self._get_user_activity(),
                "system_events": await self._get_system_events(),
                "antivirus_status": await self._get_antivirus_status(),
                "firewall_status": await self._get_firewall_status(),
            }

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to gather security metrics: {e}")
            return {"error": str(e)}

    async def _get_failed_logins(self) -> Dict[str, Any]:
        """Get failed login attempts."""
        try:
            # On Windows, check Windows Event Logs for failed logins
            if os.name == "nt":
                # Use PowerShell to query security events
                cmd = [
                    "powershell",
                    "-Command",
                    "Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4625} -MaxEvents 10 | Select-Object TimeCreated, Message | ConvertTo-Json"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    events = json.loads(result.stdout) if result.stdout.strip() else []
                    return {
                        "count": len(events),
                        "recent_events": events[:5],
                        "last_hour": len([e for e in events if self._is_recent(e.get("TimeCreated", ""))])
                    }
                else:
                    return {"count": 0, "recent_events": [], "last_hour": 0}
            else:
                # On Unix-like systems, check auth logs
                return {"count": 0, "recent_events": [], "last_hour": 0}

        except Exception as e:
            self.logger.error(f"Failed to get failed logins: {e}")
            return {"count": 0, "recent_events": [], "last_hour": 0}

    async def _get_suspicious_processes(self) -> List[Dict[str, Any]]:
        """Get suspicious processes."""
        try:
            import psutil
            
            suspicious_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    
                    # Check for suspicious patterns
                    if self._is_suspicious_process(proc_info):
                        suspicious_processes.append({
                            "pid": proc_info['pid'],
                            "name": proc_info['name'],
                            "cpu_percent": proc_info.get('cpu_percent', 0),
                            "memory_percent": proc_info.get('memory_percent', 0),
                            "reason": self._get_suspicious_reason(proc_info)
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return suspicious_processes

        except Exception as e:
            self.logger.error(f"Failed to get suspicious processes: {e}")
            return []

    async def _get_network_connections(self) -> Dict[str, Any]:
        """Get network connection information."""
        try:
            import psutil
            
            connections = psutil.net_connections()
            
            # Analyze connections for suspicious activity
            suspicious_connections = []
            external_connections = []
            
            for conn in connections:
                if conn.status == 'ESTABLISHED':
                    # Check for external connections
                    if conn.raddr and conn.raddr.ip != '127.0.0.1':
                        external_connections.append({
                            "local": f"{conn.laddr.ip}:{conn.laddr.port}",
                            "remote": f"{conn.raddr.ip}:{conn.raddr.port}",
                            "status": conn.status
                        })
                        
                        # Check if suspicious
                        if self._is_suspicious_connection(conn):
                            suspicious_connections.append({
                                "local": f"{conn.laddr.ip}:{conn.laddr.port}",
                                "remote": f"{conn.raddr.ip}:{conn.raddr.port}",
                                "status": conn.status,
                                "reason": "Suspicious external connection"
                            })
            
            return {
                "total_connections": len(connections),
                "established_connections": len([c for c in connections if c.status == 'ESTABLISHED']),
                "external_connections": external_connections,
                "suspicious_connections": suspicious_connections
            }

        except Exception as e:
            self.logger.error(f"Failed to get network connections: {e}")
            return {"error": str(e)}

    async def _get_open_ports(self) -> List[Dict[str, Any]]:
        """Get open ports and services."""
        try:
            import psutil
            
            open_ports = []
            
            for conn in psutil.net_connections():
                if conn.status == 'LISTEN':
                    open_ports.append({
                        "port": conn.laddr.port,
                        "address": conn.laddr.ip,
                        "status": conn.status
                    })
            
            return open_ports

        except Exception as e:
            self.logger.error(f"Failed to get open ports: {e}")
            return []

    async def _check_file_integrity(self) -> Dict[str, Any]:
        """Check file integrity for critical system files."""
        try:
            critical_files = [
                "C:\\Windows\\System32\\kernel32.dll",
                "C:\\Windows\\System32\\user32.dll",
                "C:\\Windows\\System32\\ntdll.dll"
            ]
            
            integrity_checks = {}
            
            for file_path in critical_files:
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    integrity_checks[file_path] = {
                        "exists": True,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "integrity": "unknown"  # Would need hash comparison in real implementation
                    }
                else:
                    integrity_checks[file_path] = {
                        "exists": False,
                        "integrity": "missing"
                    }
            
            return integrity_checks

        except Exception as e:
            self.logger.error(f"Failed to check file integrity: {e}")
            return {"error": str(e)}

    async def _get_user_activity(self) -> Dict[str, Any]:
        """Get user activity information."""
        try:
            import psutil
            
            users = psutil.users()
            active_users = []
            
            for user in users:
                active_users.append({
                    "name": user.name,
                    "terminal": user.terminal,
                    "host": user.host,
                    "started": datetime.fromtimestamp(user.started).isoformat()
                })
            
            return {
                "active_users": active_users,
                "total_users": len(users)
            }

        except Exception as e:
            self.logger.error(f"Failed to get user activity: {e}")
            return {"error": str(e)}

    async def _get_system_events(self) -> List[Dict[str, Any]]:
        """Get recent system events."""
        try:
            # This would query Windows Event Logs or system logs
            # For now, return a placeholder
            return [
                {
                    "type": "system_startup",
                    "timestamp": datetime.now().isoformat(),
                    "description": "System started normally"
                }
            ]

        except Exception as e:
            self.logger.error(f"Failed to get system events: {e}")
            return []

    async def _get_antivirus_status(self) -> Dict[str, Any]:
        """Get antivirus software status."""
        try:
            # Check for common antivirus processes
            import psutil
            
            antivirus_processes = [
                "msmpeng.exe",  # Windows Defender
                "avast.exe",    # Avast
                "avgui.exe",    # AVG
                "mcafee.exe",   # McAfee
                "norton.exe"    # Norton
            ]
            
            running_av = []
            
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'].lower() in [av.lower() for av in antivirus_processes]:
                        running_av.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "running_antivirus": running_av,
                "status": "protected" if running_av else "unprotected"
            }

        except Exception as e:
            self.logger.error(f"Failed to get antivirus status: {e}")
            return {"error": str(e)}

    async def _get_firewall_status(self) -> Dict[str, Any]:
        """Get firewall status."""
        try:
            if os.name == "nt":
                # Check Windows Firewall status
                cmd = ["netsh", "advfirewall", "show", "allprofiles"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    return {
                        "status": "enabled" if "ON" in result.stdout else "disabled",
                        "profiles": "configured"
                    }
                else:
                    return {"status": "unknown"}
            else:
                return {"status": "not_supported"}

        except Exception as e:
            self.logger.error(f"Failed to get firewall status: {e}")
            return {"error": str(e)}

    def _is_suspicious_process(self, proc_info: Dict[str, Any]) -> bool:
        """Check if a process is suspicious."""
        try:
            name = proc_info.get('name', '').lower()
            
            # Check for suspicious process names
            suspicious_names = [
                'cryptominer', 'miner', 'bitcoin', 'ethereum',
                'keylogger', 'spyware', 'trojan', 'backdoor',
                'ransomware', 'malware', 'virus'
            ]
            
            for suspicious in suspicious_names:
                if suspicious in name:
                    return True
            
            # Check for high resource usage
            if proc_info.get('cpu_percent', 0) > 80 or proc_info.get('memory_percent', 0) > 80:
                return True
            
            return False

        except Exception:
            return False

    def _get_suspicious_reason(self, proc_info: Dict[str, Any]) -> str:
        """Get reason why a process is considered suspicious."""
        name = proc_info.get('name', '').lower()
        
        if any(suspicious in name for suspicious in ['cryptominer', 'miner']):
            return "Potential cryptocurrency miner"
        elif any(suspicious in name for suspicious in ['keylogger', 'spyware']):
            return "Potential spyware"
        elif proc_info.get('cpu_percent', 0) > 80:
            return "High CPU usage"
        elif proc_info.get('memory_percent', 0) > 80:
            return "High memory usage"
        else:
            return "Suspicious behavior detected"

    def _is_suspicious_connection(self, conn) -> bool:
        """Check if a network connection is suspicious."""
        try:
            # Check for connections to known malicious IPs (simplified)
            suspicious_ips = [
                '192.168.1.100',  # Example suspicious IP
                '10.0.0.100'      # Example suspicious IP
            ]
            
            if conn.raddr and conn.raddr.ip in suspicious_ips:
                return True
            
            # Check for unusual ports
            unusual_ports = [22, 23, 3389, 5900]  # SSH, Telnet, RDP, VNC
            if conn.raddr and conn.raddr.port in unusual_ports:
                return True
            
            return False

        except Exception:
            return False

    def _is_recent(self, timestamp_str: str) -> bool:
        """Check if an event is recent (within last hour)."""
        try:
            # Parse timestamp and check if within last hour
            event_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return datetime.now(event_time.tzinfo) - event_time < timedelta(hours=1)
        except Exception:
            return False

    async def _analyze_security_data(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security data using Ollama."""
        try:
            # Use Ollama to analyze security metrics
            analysis_result = await ollama_client.analyze_metrics(metrics, "Security analysis")
            
            return {
                "timestamp": datetime.now().isoformat(),
                "security_score": self._calculate_security_score(metrics),
                "threat_level": analysis_result.risk_level,
                "recommendations": analysis_result.alternatives,
                "confidence": analysis_result.confidence,
                "analysis": analysis_result.decision
            }

        except Exception as e:
            self.logger.error(f"Failed to analyze security data: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "security_score": self._calculate_security_score(metrics),
                "threat_level": "unknown",
                "recommendations": [],
                "confidence": 0.0,
                "analysis": "Analysis failed"
            }

    def _calculate_security_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall security score (0-100)."""
        try:
            score = 100.0
            
            # Penalize for failed logins
            failed_logins = metrics.get("failed_logins", {})
            if failed_logins.get("last_hour", 0) > self.failed_login_threshold:
                score -= 20
            
            # Penalize for suspicious processes
            suspicious_processes = metrics.get("suspicious_processes", [])
            if len(suspicious_processes) > 0:
                score -= 15 * len(suspicious_processes)
            
            # Penalize for suspicious connections
            network_connections = metrics.get("network_connections", {})
            suspicious_connections = network_connections.get("suspicious_connections", [])
            if len(suspicious_connections) > 0:
                score -= 10 * len(suspicious_connections)
            
            # Penalize for unprotected system
            antivirus_status = metrics.get("antivirus_status", {})
            if antivirus_status.get("status") == "unprotected":
                score -= 30
            
            firewall_status = metrics.get("firewall_status", {})
            if firewall_status.get("status") == "disabled":
                score -= 20
            
            return max(0.0, score)

        except Exception as e:
            self.logger.error(f"Failed to calculate security score: {e}")
            return 50.0

    async def _detect_threats(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect security threats."""
        threats = []
        
        try:
            # Check for failed login attempts
            failed_logins = metrics.get("failed_logins", {})
            if failed_logins.get("last_hour", 0) > self.failed_login_threshold:
                threats.append({
                    "type": "brute_force_attempt",
                    "severity": "high",
                    "description": f"Multiple failed login attempts detected: {failed_logins.get('last_hour', 0)} in last hour",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Check for suspicious processes
            suspicious_processes = metrics.get("suspicious_processes", [])
            if len(suspicious_processes) > 0:
                threats.append({
                    "type": "suspicious_process",
                    "severity": "medium",
                    "description": f"Suspicious processes detected: {len(suspicious_processes)} processes",
                    "processes": suspicious_processes,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Check for suspicious network connections
            network_connections = metrics.get("network_connections", {})
            suspicious_connections = network_connections.get("suspicious_connections", [])
            if len(suspicious_connections) > 0:
                threats.append({
                    "type": "suspicious_connection",
                    "severity": "medium",
                    "description": f"Suspicious network connections detected: {len(suspicious_connections)} connections",
                    "connections": suspicious_connections,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Check for unprotected system
            antivirus_status = metrics.get("antivirus_status", {})
            if antivirus_status.get("status") == "unprotected":
                threats.append({
                    "type": "no_antivirus",
                    "severity": "high",
                    "description": "No antivirus software detected",
                    "timestamp": datetime.now().isoformat()
                })
            
            firewall_status = metrics.get("firewall_status", {})
            if firewall_status.get("status") == "disabled":
                threats.append({
                    "type": "firewall_disabled",
                    "severity": "medium",
                    "description": "Firewall is disabled",
                    "timestamp": datetime.now().isoformat()
                })
            
            return threats

        except Exception as e:
            self.logger.error(f"Failed to detect threats: {e}")
            return []

    async def _perform_security_remediation(self, threats: List[Dict[str, Any]]):
        """Perform security remediation actions."""
        try:
            for threat in threats:
                threat_type = threat.get("type")
                
                if threat_type == "brute_force_attempt":
                    await self._block_suspicious_ips(threat)
                elif threat_type == "suspicious_process":
                    await self._terminate_suspicious_processes(threat)
                elif threat_type == "suspicious_connection":
                    await self._block_suspicious_connections(threat)
                elif threat_type == "no_antivirus":
                    await self._enable_windows_defender()
                elif threat_type == "firewall_disabled":
                    await self._enable_firewall()
                
                # Log the remediation action
                self.logger.warning(f"Security remediation performed for {threat_type}: {threat.get('description')}")

        except Exception as e:
            self.logger.error(f"Failed to perform security remediation: {e}")

    async def _block_suspicious_ips(self, threat: Dict[str, Any]):
        """Block suspicious IP addresses."""
        try:
            # This would implement IP blocking logic
            # For now, just log the action
            self.logger.info("Would block suspicious IPs in production")
            
        except Exception as e:
            self.logger.error(f"Failed to block suspicious IPs: {e}")

    async def _terminate_suspicious_processes(self, threat: Dict[str, Any]):
        """Terminate suspicious processes."""
        try:
            processes = threat.get("processes", [])
            
            for proc_info in processes:
                try:
                    import psutil
                    proc = psutil.Process(proc_info["pid"])
                    proc.terminate()
                    self.logger.info(f"Terminated suspicious process: {proc_info['name']} (PID: {proc_info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            self.logger.error(f"Failed to terminate suspicious processes: {e}")

    async def _block_suspicious_connections(self, threat: Dict[str, Any]):
        """Block suspicious network connections."""
        try:
            # This would implement connection blocking logic
            # For now, just log the action
            self.logger.info("Would block suspicious connections in production")
            
        except Exception as e:
            self.logger.error(f"Failed to block suspicious connections: {e}")

    async def _enable_windows_defender(self):
        """Enable Windows Defender."""
        try:
            if os.name == "nt":
                # Enable Windows Defender via PowerShell
                cmd = ["powershell", "-Command", "Set-MpPreference -DisableRealtimeMonitoring $false"]
                subprocess.run(cmd, capture_output=True, timeout=10)
                self.logger.info("Windows Defender enabled")
            
        except Exception as e:
            self.logger.error(f"Failed to enable Windows Defender: {e}")

    async def _enable_firewall(self):
        """Enable firewall."""
        try:
            if os.name == "nt":
                # Enable Windows Firewall
                cmd = ["netsh", "advfirewall", "set", "allprofiles", "state", "on"]
                subprocess.run(cmd, capture_output=True, timeout=10)
                self.logger.info("Windows Firewall enabled")
            
        except Exception as e:
            self.logger.error(f"Failed to enable firewall: {e}")

    async def _update_security_status(self, metrics: Dict[str, Any], analysis: Dict[str, Any], threats: List[Dict[str, Any]]):
        """Update security status."""
        try:
            self.security_events.append({
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "analysis": analysis,
                "threats": threats
            })
            
            # Keep only recent events
            if len(self.security_events) > 100:
                self.security_events = self.security_events[-100:]
            
            # Update threat detections
            if threats:
                self.threat_detections.extend(threats)
                if len(self.threat_detections) > 50:
                    self.threat_detections = self.threat_detections[-50:]
            
        except Exception as e:
            self.logger.error(f"Failed to update security status: {e}")

    async def _broadcast_security_status(self, metrics: Dict[str, Any], analysis: Dict[str, Any], threats: List[Dict[str, Any]]):
        """Broadcast security status to other agents."""
        try:
            security_status = {
                "metrics": metrics,
                "analysis": analysis,
                "threats": threats,
                "security_score": analysis.get("security_score", 0),
                "threat_level": analysis.get("threat_level", "unknown"),
                "timestamp": datetime.now().isoformat()
            }
            
            await self.message_bus.broadcast(
                sender=self.agent_name,
                message_type=MessageType.SECURITY_UPDATE,
                content=security_status,
                priority=MessagePriority.HIGH if threats else MessagePriority.NORMAL
            )
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast security status: {e}")

    async def _setup_subscriptions(self):
        """Set up message subscriptions for the security agent."""
        await super()._setup_subscriptions()
        
        # Subscribe to security-related messages
        await self.message_bus.subscribe(MessageType.ALERT, self._handle_security_alert)
        self.subscribed_message_types.append(MessageType.ALERT)

    async def _handle_security_alert(self, message):
        """Handle security-related alerts."""
        if message.sender == self.agent_name:
            return  # Ignore our own messages
        
        # Process security alerts
        alert_content = message.content
        if "security" in alert_content.get("type", "").lower():
            self.logger.warning(f"Security alert received: {alert_content.get('message', 'Unknown alert')}")

    def get_security_summary(self) -> Dict[str, Any]:
        """Get a summary of security status."""
        return {
            "total_security_events": len(self.security_events),
            "total_threat_detections": len(self.threat_detections),
            "recent_threats": self.threat_detections[-5:] if self.threat_detections else [],
            "security_score": self._calculate_security_score(self.security_events[-1]["metrics"]) if self.security_events else 0,
            "blocked_ips": self.blocked_ips,
            "suspicious_processes": self.suspicious_processes
        } 