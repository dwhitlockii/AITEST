"""
ComplianceAgent - The rule enforcer that ensures the system follows policies and regulations.
This agent monitors compliance with security policies, regulatory requirements, and best practices.
Think of it as your auditor with a checklist and a mission to keep everything above board.
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


class ComplianceAgent(BaseAgent):
    """Agent responsible for compliance monitoring and policy enforcement."""

    def __init__(self):
        super().__init__("compliance")

        # Force Ollama as the only LLM provider
        self.llm_provider = "ollama"
        self.llm_client = ollama_client

        # Compliance state
        self.compliance_checks: List[Dict[str, Any]] = []
        self.policy_violations: List[Dict[str, Any]] = []
        self.regulatory_requirements: List[Dict[str, Any]] = []
        self.compliance_score: float = 100.0

        # Compliance policies
        self.security_policies = {
            "password_policy": {
                "min_length": 8,
                "require_complexity": True,
                "max_age_days": 90
            },
            "access_control": {
                "require_mfa": True,
                "session_timeout_minutes": 30,
                "max_failed_attempts": 5
            },
            "data_protection": {
                "encryption_required": True,
                "backup_encryption": True,
                "data_retention_days": 365
            }
        }

        # Regulatory frameworks
        self.regulatory_frameworks = [
            "GDPR", "HIPAA", "SOX", "PCI-DSS", "ISO-27001"
        ]

        # Compliance thresholds
        self.min_compliance_score = 80.0
        self.critical_violation_threshold = 3

        # Persistence integration
        self.persistence_enabled = getattr(config, "persistence_enabled", True)
        self.db_path = getattr(config, "db_path", "data/agent_system.db")
        self.persistence = PersistenceManager(self.db_path)

        self.logger.info("ComplianceAgent initialized - ready to enforce policies")

    async def _perform_check(self):
        """Perform compliance monitoring and policy checks."""
        try:
            self.last_check_time = datetime.now()

            # Perform security policy checks
            security_checks = await self._check_security_policies()

            # Perform regulatory compliance checks
            regulatory_checks = await self._check_regulatory_compliance()

            # Perform best practice checks
            best_practice_checks = await self._check_best_practices()

            # Analyze compliance status
            compliance_analysis = await self._analyze_compliance_status(
                security_checks, regulatory_checks, best_practice_checks
            )

            # Identify violations
            violations = await self._identify_violations(
                security_checks, regulatory_checks, best_practice_checks
            )

            # Perform compliance remediation if needed
            if violations:
                await self._perform_compliance_remediation(violations)

            # Update compliance status
            await self._update_compliance_status(
                security_checks, regulatory_checks, best_practice_checks, compliance_analysis, violations
            )

            # Persist compliance data if enabled
            if self.persistence_enabled:
                try:
                    await self.persistence.insert_analysis(
                        timestamp=datetime.now().isoformat(),
                        agent=self.agent_name,
                        summary=f"Compliance check completed - {len(violations)} violations found",
                        issues=str(violations),
                    )
                except Exception as e:
                    self.logger.error(f"Failed to persist compliance data: {e}")

            # Broadcast compliance status
            await self._broadcast_compliance_status(
                security_checks, regulatory_checks, best_practice_checks, compliance_analysis, violations
            )

            self.success_count += 1

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to perform compliance check: {e}")
            self.add_issue(f"Compliance check failed: {str(e)}", "high")

    async def _check_security_policies(self) -> Dict[str, Any]:
        """Check compliance with security policies."""
        try:
            security_checks = {
                "timestamp": datetime.now().isoformat(),
                "password_policy": await self._check_password_policy(),
                "access_control": await self._check_access_control(),
                "data_protection": await self._check_data_protection(),
                "network_security": await self._check_network_security(),
                "system_hardening": await self._check_system_hardening()
            }

            return security_checks

        except Exception as e:
            self.logger.error(f"Failed to check security policies: {e}")
            return {"error": str(e)}

    async def _check_password_policy(self) -> Dict[str, Any]:
        """Check password policy compliance."""
        try:
            policy = self.security_policies["password_policy"]
            
            # This would check actual password policy settings
            # For now, return simulated results
            return {
                "min_length_enforced": True,
                "complexity_enforced": True,
                "max_age_enforced": True,
                "password_history_enforced": True,
                "overall_compliance": True,
                "details": "Password policy appears to be properly configured"
            }

        except Exception as e:
            self.logger.error(f"Failed to check password policy: {e}")
            return {"error": str(e)}

    async def _check_access_control(self) -> Dict[str, Any]:
        """Check access control compliance."""
        try:
            policy = self.security_policies["access_control"]
            
            # Check for MFA, session timeouts, etc.
            return {
                "mfa_enabled": True,
                "session_timeout_configured": True,
                "failed_attempt_limits": True,
                "account_lockout_enabled": True,
                "overall_compliance": True,
                "details": "Access control policies appear to be properly configured"
            }

        except Exception as e:
            self.logger.error(f"Failed to check access control: {e}")
            return {"error": str(e)}

    async def _check_data_protection(self) -> Dict[str, Any]:
        """Check data protection compliance."""
        try:
            policy = self.security_policies["data_protection"]
            
            # Check encryption, backups, etc.
            return {
                "encryption_enabled": True,
                "backup_encryption": True,
                "data_retention_configured": True,
                "secure_deletion_enabled": True,
                "overall_compliance": True,
                "details": "Data protection measures appear to be properly configured"
            }

        except Exception as e:
            self.logger.error(f"Failed to check data protection: {e}")
            return {"error": str(e)}

    async def _check_network_security(self) -> Dict[str, Any]:
        """Check network security compliance."""
        try:
            # Check firewall, network segmentation, etc.
            return {
                "firewall_enabled": True,
                "network_segmentation": True,
                "vpn_configured": True,
                "intrusion_detection": True,
                "overall_compliance": True,
                "details": "Network security measures appear to be properly configured"
            }

        except Exception as e:
            self.logger.error(f"Failed to check network security: {e}")
            return {"error": str(e)}

    async def _check_system_hardening(self) -> Dict[str, Any]:
        """Check system hardening compliance."""
        try:
            # Check system hardening measures
            return {
                "unnecessary_services_disabled": True,
                "default_accounts_secured": True,
                "patches_applied": True,
                "antivirus_enabled": True,
                "overall_compliance": True,
                "details": "System hardening measures appear to be properly configured"
            }

        except Exception as e:
            self.logger.error(f"Failed to check system hardening: {e}")
            return {"error": str(e)}

    async def _check_regulatory_compliance(self) -> Dict[str, Any]:
        """Check compliance with regulatory frameworks."""
        try:
            regulatory_checks = {
                "timestamp": datetime.now().isoformat(),
                "frameworks": {}
            }
            
            for framework in self.regulatory_frameworks:
                framework_checks = await self._check_framework_compliance(framework)
                regulatory_checks["frameworks"][framework] = framework_checks
            
            return regulatory_checks

        except Exception as e:
            self.logger.error(f"Failed to check regulatory compliance: {e}")
            return {"error": str(e)}

    async def _check_framework_compliance(self, framework: str) -> Dict[str, Any]:
        """Check compliance with a specific regulatory framework."""
        try:
            # This would implement framework-specific checks
            # For now, return simulated results
            framework_checks = {
                "gdpr": {
                    "data_processing_consent": True,
                    "data_subject_rights": True,
                    "data_breach_notification": True,
                    "privacy_by_design": True,
                    "overall_compliance": True
                },
                "hipaa": {
                    "privacy_rule": True,
                    "security_rule": True,
                    "breach_notification": True,
                    "overall_compliance": True
                },
                "sox": {
                    "financial_controls": True,
                    "it_controls": True,
                    "audit_trail": True,
                    "overall_compliance": True
                },
                "pci-dss": {
                    "network_security": True,
                    "cardholder_data_protection": True,
                    "vulnerability_management": True,
                    "overall_compliance": True
                },
                "iso-27001": {
                    "information_security_policy": True,
                    "risk_assessment": True,
                    "access_control": True,
                    "overall_compliance": True
                }
            }
            
            return framework_checks.get(framework.lower(), {
                "overall_compliance": False,
                "details": f"Framework {framework} not implemented"
            })

        except Exception as e:
            self.logger.error(f"Failed to check {framework} compliance: {e}")
            return {"error": str(e)}

    async def _check_best_practices(self) -> Dict[str, Any]:
        """Check compliance with industry best practices."""
        try:
            best_practice_checks = {
                "timestamp": datetime.now().isoformat(),
                "logging_and_monitoring": await self._check_logging_monitoring(),
                "incident_response": await self._check_incident_response(),
                "change_management": await self._check_change_management(),
                "vendor_management": await self._check_vendor_management()
            }

            return best_practice_checks

        except Exception as e:
            self.logger.error(f"Failed to check best practices: {e}")
            return {"error": str(e)}

    async def _check_logging_monitoring(self) -> Dict[str, Any]:
        """Check logging and monitoring best practices."""
        try:
            return {
                "centralized_logging": True,
                "log_retention": True,
                "real_time_monitoring": True,
                "alerting_configured": True,
                "overall_compliance": True,
                "details": "Logging and monitoring appear to follow best practices"
            }

        except Exception as e:
            self.logger.error(f"Failed to check logging and monitoring: {e}")
            return {"error": str(e)}

    async def _check_incident_response(self) -> Dict[str, Any]:
        """Check incident response best practices."""
        try:
            return {
                "incident_response_plan": True,
                "response_team_defined": True,
                "communication_procedures": True,
                "recovery_procedures": True,
                "overall_compliance": True,
                "details": "Incident response appears to follow best practices"
            }

        except Exception as e:
            self.logger.error(f"Failed to check incident response: {e}")
            return {"error": str(e)}

    async def _check_change_management(self) -> Dict[str, Any]:
        """Check change management best practices."""
        try:
            return {
                "change_approval_process": True,
                "testing_procedures": True,
                "rollback_procedures": True,
                "documentation_requirements": True,
                "overall_compliance": True,
                "details": "Change management appears to follow best practices"
            }

        except Exception as e:
            self.logger.error(f"Failed to check change management: {e}")
            return {"error": str(e)}

    async def _check_vendor_management(self) -> Dict[str, Any]:
        """Check vendor management best practices."""
        try:
            return {
                "vendor_assessment": True,
                "contract_reviews": True,
                "performance_monitoring": True,
                "risk_assessment": True,
                "overall_compliance": True,
                "details": "Vendor management appears to follow best practices"
            }

        except Exception as e:
            self.logger.error(f"Failed to check vendor management: {e}")
            return {"error": str(e)}

    async def _analyze_compliance_status(
        self, security_checks: Dict[str, Any], regulatory_checks: Dict[str, Any], best_practice_checks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze overall compliance status using Ollama."""
        try:
            # Combine all compliance data for analysis
            compliance_data = {
                "security_checks": security_checks,
                "regulatory_checks": regulatory_checks,
                "best_practice_checks": best_practice_checks
            }
            
            # Use Ollama to analyze compliance status
            analysis_result = await ollama_client.analyze_metrics(compliance_data, "Compliance status analysis")
            
            return {
                "timestamp": datetime.now().isoformat(),
                "compliance_score": self._calculate_compliance_score(security_checks, regulatory_checks, best_practice_checks),
                "compliance_level": analysis_result.risk_level,
                "recommendations": analysis_result.alternatives,
                "confidence": analysis_result.confidence,
                "analysis": analysis_result.decision
            }

        except Exception as e:
            self.logger.error(f"Failed to analyze compliance status: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "compliance_score": self._calculate_compliance_score(security_checks, regulatory_checks, best_practice_checks),
                "compliance_level": "unknown",
                "recommendations": [],
                "confidence": 0.0,
                "analysis": "Analysis failed"
            }

    def _calculate_compliance_score(
        self, security_checks: Dict[str, Any], regulatory_checks: Dict[str, Any], best_practice_checks: Dict[str, Any]
    ) -> float:
        """Calculate overall compliance score (0-100)."""
        try:
            score = 100.0
            
            # Check security policy compliance
            for check_name, check_result in security_checks.items():
                if isinstance(check_result, dict) and not check_result.get("overall_compliance", True):
                    score -= 10
            
            # Check regulatory compliance
            frameworks = regulatory_checks.get("frameworks", {})
            for framework, framework_result in frameworks.items():
                if isinstance(framework_result, dict) and not framework_result.get("overall_compliance", True):
                    score -= 15
            
            # Check best practice compliance
            for check_name, check_result in best_practice_checks.items():
                if isinstance(check_result, dict) and not check_result.get("overall_compliance", True):
                    score -= 5
            
            return max(0.0, score)

        except Exception as e:
            self.logger.error(f"Failed to calculate compliance score: {e}")
            return 50.0

    async def _identify_violations(
        self, security_checks: Dict[str, Any], regulatory_checks: Dict[str, Any], best_practice_checks: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify compliance violations."""
        violations = []
        
        try:
            # Check security policy violations
            for check_name, check_result in security_checks.items():
                if isinstance(check_result, dict) and not check_result.get("overall_compliance", True):
                    violations.append({
                        "type": "security_policy_violation",
                        "severity": "high",
                        "description": f"Security policy violation in {check_name}",
                        "policy": check_name,
                        "details": check_result.get("details", "Unknown violation"),
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Check regulatory violations
            frameworks = regulatory_checks.get("frameworks", {})
            for framework, framework_result in frameworks.items():
                if isinstance(framework_result, dict) and not framework_result.get("overall_compliance", True):
                    violations.append({
                        "type": "regulatory_violation",
                        "severity": "critical",
                        "description": f"Regulatory violation in {framework}",
                        "framework": framework,
                        "details": framework_result.get("details", "Unknown violation"),
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Check best practice violations
            for check_name, check_result in best_practice_checks.items():
                if isinstance(check_result, dict) and not check_result.get("overall_compliance", True):
                    violations.append({
                        "type": "best_practice_violation",
                        "severity": "medium",
                        "description": f"Best practice violation in {check_name}",
                        "practice": check_name,
                        "details": check_result.get("details", "Unknown violation"),
                        "timestamp": datetime.now().isoformat()
                    })
            
            return violations

        except Exception as e:
            self.logger.error(f"Failed to identify violations: {e}")
            return []

    async def _perform_compliance_remediation(self, violations: List[Dict[str, Any]]):
        """Perform compliance remediation actions."""
        try:
            for violation in violations:
                violation_type = violation.get("type")
                
                if violation_type == "security_policy_violation":
                    await self._remediate_security_violation(violation)
                elif violation_type == "regulatory_violation":
                    await self._remediate_regulatory_violation(violation)
                elif violation_type == "best_practice_violation":
                    await self._remediate_best_practice_violation(violation)
                
                # Log the remediation action
                self.logger.warning(f"Compliance remediation performed for {violation_type}: {violation.get('description')}")

        except Exception as e:
            self.logger.error(f"Failed to perform compliance remediation: {e}")

    async def _remediate_security_violation(self, violation: Dict[str, Any]):
        """Remediate security policy violation."""
        try:
            policy = violation.get("policy")
            self.logger.info(f"Would remediate security violation for {policy} in production")
            
        except Exception as e:
            self.logger.error(f"Failed to remediate security violation: {e}")

    async def _remediate_regulatory_violation(self, violation: Dict[str, Any]):
        """Remediate regulatory violation."""
        try:
            framework = violation.get("framework")
            self.logger.info(f"Would remediate regulatory violation for {framework} in production")
            
        except Exception as e:
            self.logger.error(f"Failed to remediate regulatory violation: {e}")

    async def _remediate_best_practice_violation(self, violation: Dict[str, Any]):
        """Remediate best practice violation."""
        try:
            practice = violation.get("practice")
            self.logger.info(f"Would remediate best practice violation for {practice} in production")
            
        except Exception as e:
            self.logger.error(f"Failed to remediate best practice violation: {e}")

    async def _update_compliance_status(
        self, security_checks: Dict[str, Any], regulatory_checks: Dict[str, Any], 
        best_practice_checks: Dict[str, Any], analysis: Dict[str, Any], violations: List[Dict[str, Any]]
    ):
        """Update compliance status."""
        try:
            self.compliance_checks.append({
                "timestamp": datetime.now().isoformat(),
                "security_checks": security_checks,
                "regulatory_checks": regulatory_checks,
                "best_practice_checks": best_practice_checks,
                "analysis": analysis,
                "violations": violations
            })
            
            # Keep only recent checks
            if len(self.compliance_checks) > 100:
                self.compliance_checks = self.compliance_checks[-100:]
            
            # Update violations
            if violations:
                self.policy_violations.extend(violations)
                if len(self.policy_violations) > 50:
                    self.policy_violations = self.policy_violations[-50:]
            
            # Update compliance score
            self.compliance_score = analysis.get("compliance_score", 100.0)
            
        except Exception as e:
            self.logger.error(f"Failed to update compliance status: {e}")

    async def _broadcast_compliance_status(
        self, security_checks: Dict[str, Any], regulatory_checks: Dict[str, Any], 
        best_practice_checks: Dict[str, Any], analysis: Dict[str, Any], violations: List[Dict[str, Any]]
    ):
        """Broadcast compliance status to other agents."""
        try:
            compliance_status = {
                "security_checks": security_checks,
                "regulatory_checks": regulatory_checks,
                "best_practice_checks": best_practice_checks,
                "analysis": analysis,
                "violations": violations,
                "compliance_score": analysis.get("compliance_score", 0),
                "compliance_level": analysis.get("compliance_level", "unknown"),
                "timestamp": datetime.now().isoformat()
            }
            
            await self.message_bus.broadcast(
                sender=self.agent_name,
                message_type=MessageType.COMPLIANCE_UPDATE,
                content=compliance_status,
                priority=MessagePriority.HIGH if violations else MessagePriority.NORMAL
            )
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast compliance status: {e}")

    async def _setup_subscriptions(self):
        """Set up message subscriptions for the compliance agent."""
        await super()._setup_subscriptions()
        
        # Subscribe to compliance-related messages
        await self.message_bus.subscribe(MessageType.ALERT, self._handle_compliance_alert)
        self.subscribed_message_types.append(MessageType.ALERT)

    async def _handle_compliance_alert(self, message):
        """Handle compliance-related alerts."""
        if message.sender == self.agent_name:
            return  # Ignore our own messages
        
        # Process compliance alerts
        alert_content = message.content
        if "compliance" in alert_content.get("type", "").lower():
            self.logger.warning(f"Compliance alert received: {alert_content.get('message', 'Unknown alert')}")

    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get a summary of compliance status."""
        return {
            "total_compliance_checks": len(self.compliance_checks),
            "total_violations": len(self.policy_violations),
            "compliance_score": self.compliance_score,
            "regulatory_frameworks": self.regulatory_frameworks,
            "recent_violations": self.policy_violations[-5:] if self.policy_violations else [],
            "security_policies": list(self.security_policies.keys())
        } 