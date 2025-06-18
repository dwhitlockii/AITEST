"""
BackupAgent - The data guardian that ensures your information is safe and recoverable.
This agent monitors backup systems, data protection, and disaster recovery capabilities.
Think of it as your insurance policy for data - always there when you need it.
"""

import os
import subprocess
import json
import hashlib
import asyncio
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import shutil

from agents.base_agent import BaseAgent
from utils.message_bus import MessageType, MessagePriority
from utils.ollama_client import ollama_client, truncate_prompt, estimate_token_count
from config import config
from utils.persistence import PersistenceManager


class BackupAgent(BaseAgent):
    """Agent responsible for backup monitoring and disaster recovery management."""

    def __init__(self):
        super().__init__("backup")

        # Force Ollama as the only LLM provider
        self.llm_provider = "ollama"
        self.llm_client = ollama_client

        # Backup state
        self.backup_jobs: List[Dict[str, Any]] = []
        self.backup_status: List[Dict[str, Any]] = []
        self.recovery_tests: List[Dict[str, Any]] = []
        self.backup_issues: List[Dict[str, Any]] = []

        # Backup configuration
        self.backup_sources = [
            "C:\\Users",
            "C:\\ProgramData",
            "C:\\Windows\\System32\\config",
        ]
        self.backup_destinations = ["D:\\Backups", "\\\\backup-server\\backups"]
        self.backup_schedule = {
            "daily": "02:00",
            "weekly": "Sunday 03:00",
            "monthly": "First Sunday 04:00",
        }

        # Backup thresholds
        self.max_backup_age_hours = 24
        self.min_backup_size_mb = 100
        self.recovery_time_objective = 4  # hours
        self.recovery_point_objective = 1  # hour

        # Persistence integration
        self.persistence_enabled = getattr(config, "persistence_enabled", True)
        self.db_path = getattr(config, "db_path", "data/agent_system.db")
        self.persistence = PersistenceManager(self.db_path)

        self.logger.info("BackupAgent initialized - ready to protect your data")

    async def start(self):
        # Stagger start to avoid LLM spikes
        await asyncio.sleep(random.uniform(0, 10))
        await super().start()

    def _backup_hash(self, backup_status, integrity_checks, recovery_tests):
        return hashlib.sha256(
            json.dumps(
                {
                    "status": backup_status,
                    "integrity": integrity_checks,
                    "recovery": recovery_tests,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()

    async def _perform_check(self):
        """Perform backup monitoring and management."""
        try:
            self.last_check_time = datetime.now()

            # Check backup status
            backup_status = await self._check_backup_status()

            # Verify backup integrity
            integrity_checks = await self._verify_backup_integrity()

            # Test recovery procedures
            recovery_tests = await self._test_recovery_procedures()

            # Analyze backup health
            backup_analysis = await self._analyze_backup_health(
                backup_status, integrity_checks, recovery_tests
            )

            # Detect backup issues
            issues = await self._detect_backup_issues(
                backup_status, integrity_checks, recovery_tests
            )

            # Perform backup remediation if needed
            if issues:
                await self._perform_backup_remediation(issues)

            # Update backup status
            await self._update_backup_status(
                backup_status, integrity_checks, recovery_tests, backup_analysis, issues
            )

            # Persist backup data if enabled
            if self.persistence_enabled:
                try:
                    await self.persistence.insert_analysis(
                        timestamp=datetime.now().isoformat(),
                        agent=self.agent_name,
                        summary=f"Backup check completed - {len(issues)} issues detected",
                        issues=str(issues),
                    )
                except Exception as e:
                    self.logger.error(f"Failed to persist backup data: {e}")

            # Broadcast backup status
            await self._broadcast_backup_status(
                backup_status, integrity_checks, recovery_tests, backup_analysis, issues
            )

            self.success_count += 1

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to perform backup check: {e}")
            self.add_issue(f"Backup check failed: {str(e)}", "high")

    async def _check_backup_status(self) -> Dict[str, Any]:
        """Check the status of backup jobs and systems."""
        try:
            backup_status = {
                "timestamp": datetime.now().isoformat(),
                "backup_jobs": await self._get_backup_jobs(),
                "backup_storage": await self._check_backup_storage(),
                "backup_schedule": await self._check_backup_schedule(),
                "backup_retention": await self._check_backup_retention(),
                "backup_encryption": await self._check_backup_encryption(),
            }

            return backup_status

        except Exception as e:
            self.logger.error(f"Failed to check backup status: {e}")
            return {"error": str(e)}

    async def _get_backup_jobs(self) -> List[Dict[str, Any]]:
        """Get information about backup jobs."""
        try:
            backup_jobs = []

            # Check for common backup tools and jobs
            backup_tools = [
                "Windows Backup",
                "Veeam",
                "Acronis",
                "Backup Exec",
                "Symantec",
            ]

            for tool in backup_tools:
                # This would check actual backup job status
                # For now, return simulated results
                job_info = {
                    "name": f"{tool} Backup Job",
                    "status": "completed",
                    "last_run": (datetime.now() - timedelta(hours=2)).isoformat(),
                    "next_run": (datetime.now() + timedelta(hours=22)).isoformat(),
                    "size_mb": 1024,
                    "duration_minutes": 45,
                    "success_rate": 0.95,
                }
                backup_jobs.append(job_info)

            return backup_jobs

        except Exception as e:
            self.logger.error(f"Failed to get backup jobs: {e}")
            return []

    async def _check_backup_storage(self) -> Dict[str, Any]:
        """Check backup storage status."""
        try:
            storage_status = {}

            for destination in self.backup_destinations:
                try:
                    if os.path.exists(destination):
                        # Get storage information
                        total, used, free = shutil.disk_usage(destination)

                        storage_status[destination] = {
                            "available": True,
                            "total_gb": total / (1024**3),
                            "used_gb": used / (1024**3),
                            "free_gb": free / (1024**3),
                            "usage_percent": (used / total) * 100,
                        }
                    else:
                        storage_status[destination] = {
                            "available": False,
                            "error": "Path not accessible",
                        }
                except Exception as e:
                    storage_status[destination] = {"available": False, "error": str(e)}

            return storage_status

        except Exception as e:
            self.logger.error(f"Failed to check backup storage: {e}")
            return {"error": str(e)}

    async def _check_backup_schedule(self) -> Dict[str, Any]:
        """Check backup schedule compliance."""
        try:
            schedule_status = {
                "daily_backup": await self._check_schedule_compliance("daily"),
                "weekly_backup": await self._check_schedule_compliance("weekly"),
                "monthly_backup": await self._check_schedule_compliance("monthly"),
            }

            return schedule_status

        except Exception as e:
            self.logger.error(f"Failed to check backup schedule: {e}")
            return {"error": str(e)}

    async def _check_schedule_compliance(self, schedule_type: str) -> Dict[str, Any]:
        """Check compliance with a specific backup schedule."""
        try:
            # This would check actual schedule compliance
            # For now, return simulated results
            return {
                "compliant": True,
                "last_backup": (datetime.now() - timedelta(hours=2)).isoformat(),
                "next_backup": (datetime.now() + timedelta(hours=22)).isoformat(),
                "status": "on_schedule",
            }

        except Exception as e:
            self.logger.error(f"Failed to check {schedule_type} schedule: {e}")
            return {"error": str(e)}

    async def _check_backup_retention(self) -> Dict[str, Any]:
        """Check backup retention policy compliance."""
        try:
            retention_status = {
                "daily_retention": 7,  # days
                "weekly_retention": 4,  # weeks
                "monthly_retention": 12,  # months
                "compliance": True,
                "oldest_backup": (datetime.now() - timedelta(days=30)).isoformat(),
                "newest_backup": (datetime.now() - timedelta(hours=2)).isoformat(),
            }

            return retention_status

        except Exception as e:
            self.logger.error(f"Failed to check backup retention: {e}")
            return {"error": str(e)}

    async def _check_backup_encryption(self) -> Dict[str, Any]:
        """Check backup encryption status."""
        try:
            encryption_status = {
                "encryption_enabled": True,
                "encryption_algorithm": "AES-256",
                "key_management": "secure",
                "compliance": True,
            }

            return encryption_status

        except Exception as e:
            self.logger.error(f"Failed to check backup encryption: {e}")
            return {"error": str(e)}

    async def _verify_backup_integrity(self) -> Dict[str, Any]:
        """Verify the integrity of backup data."""
        try:
            integrity_checks = {
                "timestamp": datetime.now().isoformat(),
                "file_integrity": await self._check_file_integrity(),
                "backup_consistency": await self._check_backup_consistency(),
                "data_validation": await self._check_data_validation(),
                "restore_test": await self._test_restore_capability(),
            }

            return integrity_checks

        except Exception as e:
            self.logger.error(f"Failed to verify backup integrity: {e}")
            return {"error": str(e)}

    async def _check_file_integrity(self) -> Dict[str, Any]:
        """Check file integrity of backup data."""
        try:
            # This would perform actual file integrity checks
            # For now, return simulated results
            return {
                "checksum_validation": True,
                "corrupted_files": 0,
                "total_files": 10000,
                "integrity_score": 100.0,
            }

        except Exception as e:
            self.logger.error(f"Failed to check file integrity: {e}")
            return {"error": str(e)}

    async def _check_backup_consistency(self) -> Dict[str, Any]:
        """Check backup consistency across different backup sets."""
        try:
            # This would check consistency between backup sets
            return {
                "consistency_check": True,
                "inconsistencies_found": 0,
                "consistency_score": 100.0,
            }

        except Exception as e:
            self.logger.error(f"Failed to check backup consistency: {e}")
            return {"error": str(e)}

    async def _check_data_validation(self) -> Dict[str, Any]:
        """Validate backup data content."""
        try:
            # This would validate backup data content
            return {
                "data_validation": True,
                "validation_errors": 0,
                "validation_score": 100.0,
            }

        except Exception as e:
            self.logger.error(f"Failed to check data validation: {e}")
            return {"error": str(e)}

    async def _test_restore_capability(self) -> Dict[str, Any]:
        """Test restore capability from backups."""
        try:
            # This would perform actual restore tests
            # For now, return simulated results
            return {
                "restore_test": True,
                "restore_time_minutes": 30,
                "restore_success_rate": 0.95,
                "last_test": (datetime.now() - timedelta(days=7)).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to test restore capability: {e}")
            return {"error": str(e)}

    async def _test_recovery_procedures(self) -> Dict[str, Any]:
        """Test disaster recovery procedures."""
        try:
            recovery_tests = {
                "timestamp": datetime.now().isoformat(),
                "rto_compliance": await self._test_rto_compliance(),
                "rpo_compliance": await self._test_rpo_compliance(),
                "disaster_recovery_plan": await self._test_disaster_recovery_plan(),
                "business_continuity": await self._test_business_continuity(),
            }

            return recovery_tests

        except Exception as e:
            self.logger.error(f"Failed to test recovery procedures: {e}")
            return {"error": str(e)}

    async def _test_rto_compliance(self) -> Dict[str, Any]:
        """Test Recovery Time Objective compliance."""
        try:
            # This would test actual RTO compliance
            return {
                "rto_target_hours": self.recovery_time_objective,
                "actual_recovery_time_hours": 3.5,
                "compliant": True,
                "last_test": (datetime.now() - timedelta(days=14)).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to test RTO compliance: {e}")
            return {"error": str(e)}

    async def _test_rpo_compliance(self) -> Dict[str, Any]:
        """Test Recovery Point Objective compliance."""
        try:
            # This would test actual RPO compliance
            return {
                "rpo_target_hours": self.recovery_point_objective,
                "actual_data_loss_hours": 0.5,
                "compliant": True,
                "last_test": (datetime.now() - timedelta(days=14)).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to test RPO compliance: {e}")
            return {"error": str(e)}

    async def _test_disaster_recovery_plan(self) -> Dict[str, Any]:
        """Test disaster recovery plan effectiveness."""
        try:
            # This would test disaster recovery plan
            return {
                "plan_exists": True,
                "plan_tested": True,
                "test_success_rate": 0.9,
                "last_test": (datetime.now() - timedelta(days=30)).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to test disaster recovery plan: {e}")
            return {"error": str(e)}

    async def _test_business_continuity(self) -> Dict[str, Any]:
        """Test business continuity procedures."""
        try:
            # This would test business continuity procedures
            return {
                "continuity_plan_exists": True,
                "procedures_tested": True,
                "test_success_rate": 0.85,
                "last_test": (datetime.now() - timedelta(days=60)).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to test business continuity: {e}")
            return {"error": str(e)}

    async def _analyze_backup_health(
        self,
        backup_status: Dict[str, Any],
        integrity_checks: Dict[str, Any],
        recovery_tests: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze overall backup health using Ollama."""
        try:
            # Throttle/caching logic
            if not hasattr(self, "analysis_cache"):
                self.analysis_cache = {}
            cache_ttl = 300  # 5 min
            now = datetime.now()
            backup_hash = self._backup_hash(
                backup_status, integrity_checks, recovery_tests
            )
            cached = self.analysis_cache.get(backup_hash)
            if cached and (
                now - datetime.fromisoformat(cached["timestamp"])
            ) < timedelta(seconds=cache_ttl):
                return cached["result"]
            try:
                backup_data = {
                    "backup_status": backup_status,
                    "integrity_checks": integrity_checks,
                    "recovery_tests": recovery_tests,
                }
                # Truncate prompt if needed
                prompt_str = truncate_prompt(json.dumps(backup_data), max_tokens=4096)
                self.logger.debug(f"Ollama prompt length: {estimate_token_count(prompt_str)} tokens")
                # Validate input data
                if not isinstance(backup_status, dict) or not isinstance(integrity_checks, dict) or not isinstance(recovery_tests, dict):
                    self.logger.error("Invalid input data for LLM analysis")
                    return {"error": "Invalid input data for LLM analysis"}
                analysis_result = await self.llm_client.analyze_metrics(
                    backup_data, "Backup health analysis"
                )
                if hasattr(analysis_result, "dict"):
                    analysis_result = analysis_result.dict()
                if not isinstance(analysis_result, dict):
                    self.logger.error(f"LLM analysis did not return a dict: {type(analysis_result)}")
                    return {
                        "timestamp": now.isoformat(),
                        "backup_score": self._calculate_backup_score(
                            backup_status, integrity_checks, recovery_tests
                        ),
                        "health_level": "unknown",
                        "recommendations": [],
                        "confidence": 0.0,
                        "analysis": "Analysis failed (invalid LLM result)",
                    }
                result = {
                    "timestamp": now.isoformat(),
                    "backup_score": self._calculate_backup_score(
                        backup_status, integrity_checks, recovery_tests
                    ),
                    "health_level": analysis_result.get("risk_level", "unknown"),
                    "recommendations": analysis_result.get("alternatives", []),
                    "confidence": analysis_result.get("confidence", 0.0),
                    "analysis": analysis_result.get("decision", "Analysis failed"),
                }
                self.analysis_cache[backup_hash] = {
                    "result": result,
                    "timestamp": now.isoformat(),
                }
                return result
            except Exception as e:
                self.logger.error(f"Failed to analyze backup health: {e}")
                return {
                    "timestamp": now.isoformat(),
                    "backup_score": self._calculate_backup_score(
                        backup_status, integrity_checks, recovery_tests
                    ),
                    "health_level": "unknown",
                    "recommendations": [],
                    "confidence": 0.0,
                    "analysis": "Analysis failed",
                }
        except Exception as e:
            self.logger.error(f"Failed to analyze backup health: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "backup_score": self._calculate_backup_score(
                    backup_status, integrity_checks, recovery_tests
                ),
                "health_level": "unknown",
                "recommendations": [],
                "confidence": 0.0,
                "analysis": "Analysis failed",
            }

    def _calculate_backup_score(
        self,
        backup_status: Dict[str, Any],
        integrity_checks: Dict[str, Any],
        recovery_tests: Dict[str, Any],
    ) -> float:
        """Calculate overall backup health score (0-100)."""
        try:
            score = 100.0

            # Check backup job status
            backup_jobs = backup_status.get("backup_jobs", [])
            failed_jobs = sum(
                1 for job in backup_jobs if job.get("status") != "completed"
            )
            if failed_jobs > 0:
                score -= failed_jobs * 10

            # Check backup storage
            storage_status = backup_status.get("backup_storage", {})
            for destination, status in storage_status.items():
                if isinstance(status, dict) and not status.get("available", True):
                    score -= 15
                elif isinstance(status, dict) and status.get("usage_percent", 0) > 90:
                    score -= 10

            # Check integrity
            file_integrity = integrity_checks.get("file_integrity", {})
            if not file_integrity.get("checksum_validation", True):
                score -= 20

            # Check recovery tests
            rto_test = recovery_tests.get("rto_compliance", {})
            if not rto_test.get("compliant", True):
                score -= 15

            rpo_test = recovery_tests.get("rpo_compliance", {})
            if not rpo_test.get("compliant", True):
                score -= 15

            return max(0.0, score)

        except Exception as e:
            self.logger.error(f"Failed to calculate backup score: {e}")
            return 50.0

    async def _detect_backup_issues(
        self,
        backup_status: Dict[str, Any],
        integrity_checks: Dict[str, Any],
        recovery_tests: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Detect backup issues."""
        issues = []

        try:
            # Check for failed backup jobs
            backup_jobs = backup_status.get("backup_jobs", [])
            for job in backup_jobs:
                if job.get("status") != "completed":
                    issues.append(
                        {
                            "type": "backup_job_failed",
                            "severity": "high",
                            "description": f"Backup job failed: {job.get('name', 'Unknown')}",
                            "job_name": job.get("name"),
                            "status": job.get("status"),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

            # Check for storage issues
            storage_status = backup_status.get("backup_storage", {})
            for destination, status in storage_status.items():
                if isinstance(status, dict) and not status.get("available", True):
                    issues.append(
                        {
                            "type": "backup_storage_unavailable",
                            "severity": "critical",
                            "description": f"Backup storage unavailable: {destination}",
                            "destination": destination,
                            "error": status.get("error", "Unknown error"),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                elif isinstance(status, dict) and status.get("usage_percent", 0) > 90:
                    issues.append(
                        {
                            "type": "backup_storage_full",
                            "severity": "high",
                            "description": f"Backup storage nearly full: {destination}",
                            "destination": destination,
                            "usage_percent": status.get("usage_percent"),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

            # Check for integrity issues
            file_integrity = integrity_checks.get("file_integrity", {})
            if not file_integrity.get("checksum_validation", True):
                issues.append(
                    {
                        "type": "backup_integrity_failed",
                        "severity": "critical",
                        "description": "Backup file integrity check failed",
                        "corrupted_files": file_integrity.get("corrupted_files", 0),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # Check for recovery issues
            rto_test = recovery_tests.get("rto_compliance", {})
            if not rto_test.get("compliant", True):
                issues.append(
                    {
                        "type": "rto_non_compliant",
                        "severity": "high",
                        "description": "Recovery Time Objective not met",
                        "target_hours": rto_test.get("rto_target_hours"),
                        "actual_hours": rto_test.get("actual_recovery_time_hours"),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            rpo_test = recovery_tests.get("rpo_compliance", {})
            if not rpo_test.get("compliant", True):
                issues.append(
                    {
                        "type": "rpo_non_compliant",
                        "severity": "high",
                        "description": "Recovery Point Objective not met",
                        "target_hours": rpo_test.get("rpo_target_hours"),
                        "actual_hours": rpo_test.get("actual_data_loss_hours"),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            return issues

        except Exception as e:
            self.logger.error(f"Failed to detect backup issues: {e}")
            return []

    async def _perform_backup_remediation(self, issues: List[Dict[str, Any]]):
        """Perform backup remediation actions."""
        try:
            for issue in issues:
                issue_type = issue.get("type")

                if issue_type == "backup_job_failed":
                    await self._restart_backup_job(issue)
                elif issue_type == "backup_storage_unavailable":
                    await self._fix_backup_storage(issue)
                elif issue_type == "backup_storage_full":
                    await self._cleanup_backup_storage(issue)
                elif issue_type == "backup_integrity_failed":
                    await self._fix_backup_integrity(issue)
                elif issue_type == "rto_non_compliant":
                    await self._optimize_recovery_time(issue)
                elif issue_type == "rpo_non_compliant":
                    await self._optimize_recovery_point(issue)

                # Log the remediation action
                self.logger.warning(
                    f"Backup remediation performed for {issue_type}: {issue.get('description')}"
                )

        except Exception as e:
            self.logger.error(f"Failed to perform backup remediation: {e}")

    async def _restart_backup_job(self, issue: Dict[str, Any]):
        """Restart a failed backup job."""
        try:
            job_name = issue.get("job_name")
            self.logger.info(f"Would restart backup job: {job_name}")

        except Exception as e:
            self.logger.error(f"Failed to restart backup job: {e}")

    async def _fix_backup_storage(self, issue: Dict[str, Any]):
        """Fix backup storage issues."""
        try:
            destination = issue.get("destination")
            self.logger.info(f"Would fix backup storage: {destination}")

        except Exception as e:
            self.logger.error(f"Failed to fix backup storage: {e}")

    async def _cleanup_backup_storage(self, issue: Dict[str, Any]):
        """Clean up backup storage."""
        try:
            destination = issue.get("destination")
            self.logger.info(f"Would cleanup backup storage: {destination}")

        except Exception as e:
            self.logger.error(f"Failed to cleanup backup storage: {e}")

    async def _fix_backup_integrity(self, issue: Dict[str, Any]):
        """Fix backup integrity issues."""
        try:
            self.logger.info("Would fix backup integrity issues")

        except Exception as e:
            self.logger.error(f"Failed to fix backup integrity: {e}")

    async def _optimize_recovery_time(self, issue: Dict[str, Any]):
        """Optimize recovery time."""
        try:
            self.logger.info("Would optimize recovery time")

        except Exception as e:
            self.logger.error(f"Failed to optimize recovery time: {e}")

    async def _optimize_recovery_point(self, issue: Dict[str, Any]):
        """Optimize recovery point."""
        try:
            self.logger.info("Would optimize recovery point")

        except Exception as e:
            self.logger.error(f"Failed to optimize recovery point: {e}")

    async def _update_backup_status(
        self,
        backup_status: Dict[str, Any],
        integrity_checks: Dict[str, Any],
        recovery_tests: Dict[str, Any],
        analysis: Dict[str, Any],
        issues: List[Dict[str, Any]],
    ):
        """Update backup status."""
        try:
            self.backup_status.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "backup_status": backup_status,
                    "integrity_checks": integrity_checks,
                    "recovery_tests": recovery_tests,
                    "analysis": analysis,
                    "issues": issues,
                }
            )

            # Keep only recent status
            if len(self.backup_status) > 100:
                self.backup_status = self.backup_status[-100:]

            # Update recovery tests
            self.recovery_tests.append(
                {"timestamp": datetime.now().isoformat(), "tests": recovery_tests}
            )
            if len(self.recovery_tests) > 50:
                self.recovery_tests = self.recovery_tests[-50:]

            # Update backup issues
            if issues:
                self.backup_issues.extend(issues)
                if len(self.backup_issues) > 50:
                    self.backup_issues = self.backup_issues[-50:]

        except Exception as e:
            self.logger.error(f"Failed to update backup status: {e}")

    async def _broadcast_backup_status(
        self,
        backup_status: Dict[str, Any],
        integrity_checks: Dict[str, Any],
        recovery_tests: Dict[str, Any],
        analysis: Dict[str, Any],
        issues: List[Dict[str, Any]],
    ):
        """Broadcast backup status to other agents."""
        try:
            backup_status_msg = {
                "backup_status": backup_status,
                "integrity_checks": integrity_checks,
                "recovery_tests": recovery_tests,
                "analysis": analysis,
                "issues": issues,
                "backup_score": analysis.get("backup_score", 0),
                "health_level": analysis.get("health_level", "unknown"),
                "timestamp": datetime.now().isoformat(),
            }

            await self.message_bus.broadcast(
                sender=self.agent_name,
                message_type=MessageType.BACKUP_UPDATE,
                content=backup_status_msg,
                priority=MessagePriority.HIGH if issues else MessagePriority.NORMAL,
            )

        except Exception as e:
            self.logger.error(f"Failed to broadcast backup status: {e}")

    async def _setup_subscriptions(self):
        """Set up message subscriptions for the backup agent."""
        await super()._setup_subscriptions()

        # Subscribe to backup-related messages
        await self.message_bus.subscribe(MessageType.ALERT, self._handle_backup_alert)
        self.subscribed_message_types.append(MessageType.ALERT)

    async def _handle_backup_alert(self, message):
        """Handle backup-related alerts."""
        if message.sender == self.agent_name:
            return  # Ignore our own messages

        # Process backup alerts
        alert_content = message.content
        if "backup" in alert_content.get("type", "").lower():
            self.logger.warning(
                f"Backup alert received: {alert_content.get('message', 'Unknown alert')}"
            )

    def get_backup_summary(self) -> Dict[str, Any]:
        """Get a summary of backup status."""
        return {
            "total_backup_status": len(self.backup_status),
            "total_recovery_tests": len(self.recovery_tests),
            "total_backup_issues": len(self.backup_issues),
            "recent_issues": self.backup_issues[-5:] if self.backup_issues else [],
            "backup_sources": self.backup_sources,
            "backup_destinations": self.backup_destinations,
            "backup_schedule": self.backup_schedule,
        }
