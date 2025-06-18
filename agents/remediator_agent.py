"""
RemediatorAgent - The fixer that makes things work again.
This agent takes action when things go wrong - restarting services, clearing disk space, etc.
Think of it as the IT superhero that swoops in to save the day.
"""

import asyncio
import subprocess
import shutil
import os
import hashlib
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from agents.base_agent import BaseAgent
from utils.message_bus import MessageType
from utils.ollama_client import ollama_client, truncate_prompt, estimate_token_count
from config import config
from utils.persistence import PersistenceManager


class RemediatorAgent(BaseAgent):
    """Agent responsible for automated remediation and self-healing actions."""

    def __init__(self):
        super().__init__("RemediatorAgent")

        # Force Ollama as the only LLM provider
        self.llm_provider = "ollama"
        self.llm_client = ollama_client

        # Remediation state
        self.remediation_history: List[Dict[str, Any]] = []
        self.active_remediations: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, int] = {}

        # Action tracking
        self.actions_performed = 0
        self.successful_remediations = 0
        self.failed_remediations = 0

        # Cooldown tracking
        self.last_remediation_time: Optional[datetime] = None
        self.remediation_cooldowns: Dict[str, datetime] = {}

        # Windows-specific
        self.is_windows = os.name == "nt"

        # Persistence integration
        self.persistence_enabled = getattr(config, "persistence_enabled", True)
        self.db_path = getattr(config, "db_path", "data/agent_system.db")
        self.persistence = PersistenceManager(self.db_path)

        self.logger.info("RemediatorAgent initialized - ready to fix what's broken")

    async def start(self):
        # Stagger start to avoid LLM spikes
        await asyncio.sleep(random.uniform(0, 10))
        await super().start()

    def _target_hash(self, target):
        import json

        return hashlib.sha256(json.dumps(target, sort_keys=True).encode()).hexdigest()

    async def _perform_check(self):
        """Check for issues that need remediation and take action."""
        try:
            self.last_check_time = datetime.now()
            self.logger.debug("RemediatorAgent check cycle alive")
            # Check if we're in cooldown
            if self._is_in_cooldown():
                self.logger.debug("In remediation cooldown, skipping check")
                return
            # Get recent alerts and analysis
            recent_alerts = await self._get_recent_alerts()
            recent_analysis = await self._get_recent_analysis()
            # Always log that the agent is alive, even if nothing to do
            if not recent_alerts and not recent_analysis:
                self.logger.debug("No remediation needed this cycle.")
                self.success_count += 1
                return
            # Determine what needs remediation
            remediation_targets = await self._identify_remediation_targets(
                recent_alerts, recent_analysis
            )
            if not remediation_targets:
                self.logger.debug("No remediation targets identified")
                self.success_count += 1
                return
            # Perform remediation actions
            for target in remediation_targets:
                await self._perform_remediation(target)
            self.success_count += 1
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to perform remediation check: {e}")
            self.add_issue(f"Remediation check failed: {str(e)}", "high")

    def _is_in_cooldown(self) -> bool:
        """Check if we're in a global cooldown period."""
        if not self.last_remediation_time:
            return False

        cooldown_duration = timedelta(seconds=config.healing_cooldown)
        return datetime.now() - self.last_remediation_time < cooldown_duration

    async def _get_recent_alerts(self) -> List[Dict[str, Any]]:
        """Get recent alerts from the message bus."""
        # In a real implementation, you'd query the message bus for recent alerts
        # For now, we'll return an empty list and rely on analysis data
        return []

    async def _get_recent_analysis(self) -> List[Dict[str, Any]]:
        """Get recent analysis results from the message bus."""
        # In a real implementation, you'd query the message bus for recent analysis
        # For now, we'll return an empty list
        return []

    async def _identify_remediation_targets(
        self, alerts: List[Dict[str, Any]], analysis: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify what needs to be remediated."""
        targets = []

        # Check for critical threshold violations
        for alert in alerts:
            if alert.get("severity") in ["critical", "high"]:
                targets.append(
                    {
                        "type": "threshold_violation",
                        "issue": alert.get("message", "Unknown issue"),
                        "severity": alert.get("severity", "medium"),
                        "source": "alert",
                    }
                )

        # Check for GPT-recommended actions
        for analysis_result in analysis:
            if "gpt_analysis" in analysis_result:
                gpt_analysis = analysis_result["gpt_analysis"]
                for action in gpt_analysis.get("suggested_actions", []):
                    if self._is_remediable_action(action):
                        targets.append(
                            {
                                "type": "gpt_recommendation",
                                "issue": f"GPT recommends: {action}",
                                "action": action,
                                "severity": gpt_analysis.get("risk_level", "medium"),
                                "source": "gpt_analysis",
                            }
                        )

        # Check for service issues
        service_issues = await self._check_service_health()
        targets.extend(service_issues)

        # Check for disk space issues
        disk_issues = await self._check_disk_space()
        targets.extend(disk_issues)

        return targets

    def _is_remediable_action(self, action: str) -> bool:
        """Check if an action is safe to perform automatically."""
        action_lower = action.lower()

        # Safe actions we can perform
        safe_keywords = [
            "restart service",
            "restart process",
            "clear cache",
            "free memory",
            "clean temp",
            "clean temporary",
            "disk cleanup",
            "service restart",
            "browser cache",
            "flush dns",
            "reset network",
            "user process restart",
        ]

        # Dangerous actions we should avoid
        dangerous_keywords = [
            "delete",
            "remove",
            "kill",
            "terminate",
            "shutdown",
            "reboot",
            "format",
            "wipe",
            "uninstall",
            "disable service",
        ]

        for keyword in dangerous_keywords:
            if keyword in action_lower:
                return False
        for keyword in safe_keywords:
            if keyword in action_lower:
                return True
        return False

    async def _check_service_health(self) -> List[Dict[str, Any]]:
        """Check for services that need attention."""
        targets = []

        if not self.is_windows:
            return targets

        for service_name in config.monitoring.services_to_monitor:
            try:
                # Check service status
                result = subprocess.run(
                    ["sc", "query", service_name],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    output = result.stdout.lower()
                    if "stopped" in output:
                        targets.append(
                            {
                                "type": "service_stopped",
                                "issue": f"Service {service_name} is stopped",
                                "service_name": service_name,
                                "severity": "medium",
                                "source": "service_check",
                            }
                        )

            except Exception as e:
                self.logger.error(f"Failed to check service {service_name}: {e}")

        return targets

    async def _check_disk_space(self) -> List[Dict[str, Any]]:
        """Check for disk space issues."""
        targets = []

        for path in config.monitoring.disk_paths:
            try:
                total, used, free = shutil.disk_usage(path)
                usage_percent = (used / total) * 100

                if usage_percent > config.thresholds.disk_critical:
                    targets.append(
                        {
                            "type": "disk_critical",
                            "issue": f"Critical disk usage on {path}: {usage_percent:.1f}%",
                            "path": path,
                            "usage_percent": usage_percent,
                            "severity": "critical",
                            "source": "disk_check",
                        }
                    )
                elif usage_percent > config.thresholds.disk_warning:
                    targets.append(
                        {
                            "type": "disk_warning",
                            "issue": f"High disk usage on {path}: {usage_percent:.1f}%",
                            "path": path,
                            "usage_percent": usage_percent,
                            "severity": "warning",
                            "source": "disk_check",
                        }
                    )

            except Exception as e:
                self.logger.error(f"Failed to check disk space for {path}: {e}")

        return targets

    async def _perform_remediation(self, target: Dict[str, Any]):
        """Perform remediation for a specific target."""
        try:
            # Check if we've tried this too many times
            target_key = f"{target['type']}_{target.get('issue', 'unknown')}"
            if (
                self.failed_attempts.get(target_key, 0)
                >= config.max_healing_attempts_per_issue
            ):
                self.logger.warning(f"Max attempts reached for {target_key}, skipping")
                return

            # Check cooldown for this specific issue
            if self._is_issue_in_cooldown(target_key):
                self.logger.debug(f"Issue {target_key} is in cooldown")
                return

            self.logger.info(f"Performing remediation for: {target['issue']}")

            # Get LLM recommendation for this specific issue
            llm_decision = await self._get_remediation_plan(target)

            # Perform the remediation
            success = await self._execute_remediation(target, llm_decision)

            # Record the attempt
            await self._record_remediation_attempt(target, llm_decision, success)

            if success:
                self.successful_remediations += 1
                self.logger.success(f"Successfully remediated: {target['issue']}")
            else:
                self.failed_remediations += 1
                self.failed_attempts[target_key] = (
                    self.failed_attempts.get(target_key, 0) + 1
                )
                self.logger.error(f"Failed to remediate: {target['issue']}")

            # Set cooldown
            self.last_remediation_time = datetime.now()
            self.remediation_cooldowns[target_key] = datetime.now()

        except Exception as e:
            self.logger.error(f"Error during remediation: {e}")
            self.failed_remediations += 1

    def _is_issue_in_cooldown(self, issue_key: str) -> bool:
        """Check if a specific issue is in cooldown."""
        if issue_key not in self.remediation_cooldowns:
            return False

        cooldown_duration = timedelta(seconds=config.healing_cooldown)
        return (
            datetime.now() - self.remediation_cooldowns[issue_key] < cooldown_duration
        )

    async def _get_remediation_plan(self, target: Dict[str, Any]) -> Any:
        """Get remediation plan from Ollama for the given target."""
        try:
            # Validate input
            if not isinstance(target, dict):
                self.logger.error("Invalid target for remediation plan")
                return self._get_fallback_remediation_plan(target)
            # Use Ollama for remediation planning
            plan = await self.llm_client.recommend_remediation(
                issue=target.get("type", "unknown_issue"),
                metrics=target,
                available_actions=["restart_service", "cleanup_disk", "flush_dns", "clear_cache", "kill_process"]
            )
            if hasattr(plan, "dict"):
                plan = plan.dict()
            if not isinstance(plan, dict):
                self.logger.error(f"LLM remediation plan did not return a dict: {type(plan)}")
                return self._get_fallback_remediation_plan(target)
            return plan
        except Exception as e:
            self.logger.error(f"Failed to get remediation plan: {e}")
            return self._get_fallback_remediation_plan(target)

    async def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics for context."""
        # In a real implementation, you'd get this from the sensor agent
        # For now, return basic system info
        return {
            "timestamp": datetime.now().isoformat(),
            "platform": "Windows" if self.is_windows else "Unknown",
        }

    def _get_fallback_remediation_plan(self, target: Dict[str, Any]) -> Any:
        """Get fallback remediation plan when LLM is unavailable."""
        if target["type"] == "service_stopped":
            return {
                "decision": "Restart stopped service",
                "reasoning": "Service is stopped and needs to be restarted",
                "confidence": 0.8,
                "suggested_actions": [
                    f"Restart service {target.get('service_name', 'unknown')}"
                ],
                "risk_level": "low",
            }
        elif target["type"] in ["disk_critical", "disk_warning"]:
            return {
                "decision": "Clean up disk space",
                "reasoning": "Disk usage is high and needs cleanup",
                "confidence": 0.7,
                "suggested_actions": ["Clean temporary files", "Clear system cache"],
                "risk_level": "low",
            }
        else:
            return {
                "decision": "Monitor and investigate",
                "reasoning": "Issue requires manual investigation",
                "confidence": 0.3,
                "suggested_actions": ["Monitor system", "Check logs"],
                "risk_level": "medium",
            }

    async def _execute_remediation(self, target: Dict[str, Any], llm_decision) -> bool:
        """Execute the remediation action."""
        try:
            action_performed = None

            # Execute based on target type
            if target["type"] == "service_stopped":
                service_name = target.get("service_name")
                if isinstance(service_name, str) and service_name:
                    action_performed = await self._restart_service(service_name)
                else:
                    self.logger.error("No valid service_name provided for service_stopped remediation.")
                    action_performed = False
            elif target["type"] in ["disk_critical", "disk_warning"]:
                path = target.get("path")
                if isinstance(path, str) and path:
                    action_performed = await self._cleanup_disk_space(path)
                else:
                    self.logger.error("No valid path provided for disk remediation.")
                    action_performed = False
            elif target["type"] == "gpt_recommendation":
                action = target.get("action")
                if isinstance(action, str) and action:
                    action_performed = await self._execute_gpt_recommendation(action)
                else:
                    self.logger.error("No valid action provided for gpt_recommendation remediation.")
                    action_performed = False
            else:
                # Generic remediation based on LLM suggestions
                suggested_actions = llm_decision["suggested_actions"] if isinstance(llm_decision, dict) and "suggested_actions" in llm_decision else []
                if isinstance(suggested_actions, list) and suggested_actions:
                    action_performed = await self._execute_gpt_suggestions(suggested_actions)
                else:
                    self.logger.error("No valid suggested_actions for generic remediation.")
                    action_performed = False

            # Log the action
            if action_performed:
                self.log_action("remediation", target["issue"], "completed")
            else:
                self.log_action("remediation", target["issue"], "failed")

            return action_performed

        except Exception as e:
            self.logger.error(f"Error executing remediation: {e}")
            return False

    async def _restart_service(self, service_name: str) -> bool:
        """Restart a Windows service."""
        if not self.is_windows or not service_name:
            return False

        try:
            self.logger.info(f"Attempting to restart service: {service_name}")

            # Stop the service
            subprocess.run(
                ["sc", "stop", service_name], capture_output=True, text=True, timeout=30
            )

            # Wait a moment
            await asyncio.sleep(2)

            # Start the service
            start_result = subprocess.run(
                ["sc", "start", service_name],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if start_result.returncode == 0:
                self.logger.success(f"Successfully restarted service: {service_name}")
                return True
            else:
                self.logger.error(
                    f"Failed to restart service {service_name}: {start_result.stderr}"
                )
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout restarting service: {service_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error restarting service {service_name}: {e}")
            return False

    async def _cleanup_disk_space(self, path: str) -> bool:
        """Clean up disk space on the specified path."""
        try:
            self.logger.info(f"Cleaning up disk space on: {path}")

            # Clean temporary files
            temp_dirs = [
                os.path.join(os.environ.get("TEMP", ""), ""),
                os.path.join(os.environ.get("TMP", ""), ""),
                os.path.join(path, "Windows", "Temp"),
                os.path.join(path, "Users", "*", "AppData", "Local", "Temp"),
            ]

            files_cleaned = 0
            space_freed = 0

            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    try:
                        # Get directory size before cleanup
                        dir_size_before = self._get_directory_size(temp_dir)

                        # Clean old temporary files (older than 7 days)
                        cutoff_time = datetime.now() - timedelta(days=7)
                        cleaned = self._clean_old_files(temp_dir, cutoff_time)

                        # Get directory size after cleanup
                        dir_size_after = self._get_directory_size(temp_dir)

                        files_cleaned += cleaned
                        space_freed += dir_size_before - dir_size_after

                    except Exception as e:
                        self.logger.error(f"Error cleaning {temp_dir}: {e}")

            if space_freed > 0:
                self.logger.success(
                    f"Cleaned {files_cleaned} files, freed {space_freed / (1024**2):.1f} MB"
                )
                return True
            else:
                self.logger.info("No files cleaned during disk space cleanup")
                return False

        except Exception as e:
            self.logger.error(f"Error during disk cleanup: {e}")
            return False

    def _get_directory_size(self, path: str) -> int:
        """Get the total size of a directory in bytes."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        continue
        except Exception:
            pass
        return total_size

    def _clean_old_files(self, directory: str, cutoff_time: datetime) -> int:
        """Clean files older than the cutoff time."""
        files_cleaned = 0
        try:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                try:
                    if os.path.isfile(filepath):
                        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                        if file_time < cutoff_time:
                            os.remove(filepath)
                            files_cleaned += 1
                except (OSError, FileNotFoundError):
                    continue
        except Exception:
            pass
        return files_cleaned

    async def _execute_gpt_recommendation(self, action: str) -> bool:
        """Execute a specific GPT recommendation."""
        try:
            self.logger.info(f"Executing GPT recommendation: {action}")
            action_lower = action.lower()
            if "restart service" in action_lower:
                # Extract service name from action
                return await self._restart_service("spooler")  # Default service
            elif "clean" in action_lower and "temp" in action_lower:
                if config.temp_cleanup_enabled:
                    return await self._cleanup_disk_space("C:\\")
                else:
                    self.logger.info("Temp cleanup is disabled in config.")
                    return False
            elif "browser cache" in action_lower:
                if config.browser_cache_cleanup_enabled:
                    return await self._cleanup_browser_cache()
                else:
                    self.logger.info("Browser cache cleanup is disabled in config.")
                    return False
            elif (
                "user process restart" in action_lower
                or "restart explorer" in action_lower
            ):
                if config.user_process_restart_enabled:
                    return await self._restart_user_process("explorer.exe")
                else:
                    self.logger.info("User process restart is disabled in config.")
                    return False
            elif "flush dns" in action_lower:
                if config.dns_flush_enabled:
                    return await self._flush_dns_cache()
                else:
                    self.logger.info("DNS flush is disabled in config.")
                    return False
            else:
                self.logger.warning(f"Unknown GPT recommendation: {action}")
                return False
        except Exception as e:
            self.logger.error(f"Error executing GPT recommendation: {e}")
            return False

    async def _cleanup_browser_cache(self) -> bool:
        """Clean browser cache for common browsers (Windows)."""
        try:
            import shutil
            import glob
            import getpass

            user = getpass.getuser()
            cleaned = 0
            # Chrome
            chrome_cache = (
                f"C:/Users/{user}/AppData/Local/Google/Chrome/User Data/Default/Cache"
            )
            if os.path.exists(chrome_cache):
                for file in glob.glob(f"{chrome_cache}/*"):
                    try:
                        if os.path.isfile(file):
                            os.remove(file)
                            cleaned += 1
                        elif os.path.isdir(file):
                            shutil.rmtree(file, ignore_errors=True)
                            cleaned += 1
                    except Exception:
                        continue
            # Edge
            edge_cache = (
                f"C:/Users/{user}/AppData/Local/Microsoft/Edge/User Data/Default/Cache"
            )
            if os.path.exists(edge_cache):
                for file in glob.glob(f"{edge_cache}/*"):
                    try:
                        if os.path.isfile(file):
                            os.remove(file)
                            cleaned += 1
                        elif os.path.isdir(file):
                            shutil.rmtree(file, ignore_errors=True)
                            cleaned += 1
                    except Exception:
                        continue
            # Firefox
            firefox_cache_root = (
                f"C:/Users/{user}/AppData/Local/Mozilla/Firefox/Profiles"
            )
            if os.path.exists(firefox_cache_root):
                for profile in os.listdir(firefox_cache_root):
                    cache_path = os.path.join(firefox_cache_root, profile, "cache2")
                    if os.path.exists(cache_path):
                        for file in glob.glob(f"{cache_path}/*"):
                            try:
                                if os.path.isfile(file):
                                    os.remove(file)
                                    cleaned += 1
                                elif os.path.isdir(file):
                                    shutil.rmtree(file, ignore_errors=True)
                                    cleaned += 1
                            except Exception:
                                continue
            self.logger.success(f"Cleaned {cleaned} browser cache files/folders.")
            return cleaned > 0
        except Exception as e:
            self.logger.error(f"Error cleaning browser cache: {e}")
            return False

    async def _restart_user_process(self, process_name: str) -> bool:
        """Restart a user process (e.g., explorer.exe)."""
        try:
            import psutil

            killed = 0
            for proc in psutil.process_iter(["name"]):
                if (
                    proc.info["name"]
                    and proc.info["name"].lower() == process_name.lower()
                ):
                    proc.kill()
                    killed += 1
            await asyncio.sleep(2)
            if process_name.lower() == "explorer.exe":
                subprocess.Popen(["explorer.exe"])
            self.logger.success(f"Restarted {process_name} ({killed} instances killed)")
            return killed > 0
        except Exception as e:
            self.logger.error(f"Error restarting user process {process_name}: {e}")
            return False

    async def _flush_dns_cache(self) -> bool:
        """Flush the Windows DNS cache."""
        try:
            result = subprocess.run(
                ["ipconfig", "/flushdns"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.logger.success("Flushed DNS cache successfully.")
                return True
            else:
                self.logger.error(f"Failed to flush DNS cache: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error flushing DNS cache: {e}")
            return False

    async def _execute_gpt_suggestions(self, suggestions: List[str]) -> bool:
        """Execute GPT suggestions."""
        success_count = 0

        for suggestion in suggestions:
            try:
                if await self._execute_gpt_recommendation(suggestion):
                    success_count += 1
            except Exception as e:
                self.logger.error(f"Error executing suggestion '{suggestion}': {e}")

        return success_count > 0

    async def _record_remediation_attempt(
        self, target: Dict[str, Any], llm_decision, success: bool
    ):
        """Record a remediation attempt."""
        target_key = f"{target['type']}_{target.get('issue', 'unknown')}"

        attempt = {
            "timestamp": datetime.now().isoformat(),
            "target": target,
            "llm_decision": (
                llm_decision["decision"] if llm_decision else "No LLM decision"
            ),
            "llm_reasoning": (
                llm_decision["reasoning"] if llm_decision else "No LLM reasoning"
            ),
            "action": (
                llm_decision["suggested_actions"][0]
                if llm_decision and llm_decision["suggested_actions"]
                else "Unknown action"
            ),
            "success": success,
            "target_key": target_key,
        }

        self.remediation_history.append(attempt)
        if len(self.remediation_history) > 100:
            self.remediation_history.pop(0)

        self.actions_performed += 1

        # Persist remediation if enabled
        if self.persistence_enabled:
            try:
                import json

                await self.persistence.insert_remediation(
                    timestamp=attempt["timestamp"],
                    agent=self.agent_name,
                    action=attempt["action"],
                    result=json.dumps(
                        {
                            "success": success,
                            "target": target,
                            "llm_decision": llm_decision,
                        }
                    ),
                )
            except Exception as e:
                self.logger.error(f"Failed to persist remediation: {e}")
                self.add_issue(f"Persistence error: {str(e)}", "high")

    async def _setup_subscriptions(self):
        """Set up message subscriptions for the remediator."""
        await super()._setup_subscriptions()

        # Subscribe to alerts
        await self.message_bus.subscribe(MessageType.ALERT, self._handle_alert)
        self.subscribed_message_types.append(MessageType.ALERT)

        # Subscribe to trend analysis
        await self.message_bus.subscribe(
            MessageType.TREND_ANALYSIS, self._handle_trend_analysis
        )
        self.subscribed_message_types.append(MessageType.TREND_ANALYSIS)

    async def _handle_alert(self, message):
        """Handle incoming alerts."""
        if message.sender == self.agent_name:
            return  # Ignore our own messages

        self.logger.info(
            f"Received alert: {message.content.get('message', 'Unknown alert')}"
        )

        # Store alert for processing in next check cycle
        await self._perform_remediation_from_alert(message.content)

    async def _handle_trend_analysis(self, message):
        """Handle incoming trend analysis."""
        if message.sender == self.agent_name:
            return  # Ignore our own messages

        self.logger.debug(f"Received trend analysis from {message.sender}")

        # Store analysis for processing in next check cycle
        await self._perform_remediation_from_analysis(message.content)

    async def _perform_remediation_from_alert(self, alert):
        # Simple remediation logic for demo: if critical, act
        if alert.get("severity") in ["critical", "high"]:
            await self._perform_remediation(alert)

    async def _perform_remediation_from_analysis(self, analysis):
        # If analysis contains issues_detected, act
        issues = analysis.get("issues_detected", [])
        for issue in issues:
            if issue.get("severity") in ["critical", "high"]:
                await self._perform_remediation(issue)

    def get_remediation_summary(self) -> Dict[str, Any]:
        """Get a summary of remediation activities."""
        return {
            "total_actions": self.actions_performed,
            "successful_remediations": self.successful_remediations,
            "failed_remediations": self.failed_remediations,
            "success_rate": (
                self.successful_remediations / max(self.actions_performed, 1)
            )
            * 100,
            "active_remediations": len(self.active_remediations),
            "recent_attempts": (
                self.remediation_history[-10:] if self.remediation_history else []
            ),
            "failed_attempts": dict(self.failed_attempts),
        }

    async def _analyze_trends(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in system metrics using Ollama only."""
        if len(metrics) < 3:
            return {"error": "Insufficient data for trend analysis"}
        try:
            latest_metrics = metrics[-1]
            historical_context = metrics[:-1] if len(metrics) > 1 else []
            # Truncate context if needed
            import json
            context_str = truncate_prompt(json.dumps(historical_context), max_tokens=4096)
            self.logger.debug(f"Ollama trend context length: {estimate_token_count(context_str)} tokens")
            gpt_decision = await ollama_client.detect_anomalies(latest_metrics, historical_context)
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
                "calculated_trends": {},
            }
            return trends
        except Exception as e:
            self.logger.error(f"Trend analysis failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": f"Trend analysis failed: {str(e)}",
                "calculated_trends": {},
            }
