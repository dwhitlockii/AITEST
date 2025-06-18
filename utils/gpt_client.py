"""
GPT client for AI-powered decision making in the multi-agent system.
This is where the magic happens - when agents need to think, they come here.
"""

import os
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import openai
from pydantic import BaseModel, Field

from config import config
from .logger import create_agent_logger
from utils.message_bus import message_bus, MessageType, MessagePriority

logger = create_agent_logger("GPTClient")


class GPTDecision(BaseModel):
    """Represents a decision made by GPT with reasoning."""

    decision: str = Field(..., description="The decision or action to take")
    reasoning: str = Field(..., description="Explanation of why this decision was made")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level 0-1")
    risk_level: str = Field(..., description="Risk level: low, medium, high, critical")
    alternatives: List[str] = Field(
        default_factory=list, description="Alternative actions considered"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class LLMQuotaExceeded(Exception):
    """Raised when LLM API quota is exceeded and fallback is required."""

    pass


class GPTClient:
    """
    Enhanced GPT client for intelligent decision making in the multi-agent system.
    Provides structured decision making with safety checks and fallback logic.
    """

    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=config.gpt.api_key)
        self.model = config.gpt.model
        self.max_tokens = config.gpt.max_tokens
        self.temperature = config.gpt.temperature
        self.retry_attempts = config.gpt.retry_attempts
        self.retry_delay = config.gpt.retry_delay
        self.fallback_model = "gpt-3.5-turbo"
        self._model_checked = False

        # Decision history for context
        self.decision_history: List[GPTDecision] = []
        self.max_history = 10

        logger.info("GPT Client initialized with enhanced decision-making capabilities")

    async def _ensure_model(self):
        """Ensure the configured model exists, fallback if not."""
        if self._model_checked:
            return
        try:
            models = await self.client.models.list()
            available_models = [m.id for m in models.data]
            if self.model not in available_models:
                logger.warning(
                    f"Configured model '{self.model}' not available. Falling back to '{self.fallback_model}'"
                )
                self.model = self.fallback_model
        except Exception as e:
            logger.warning(f"Could not verify model availability: {e}")
        self._model_checked = True

    async def analyze_metrics(
        self, metrics: Dict[str, Any], context: str = ""
    ) -> GPTDecision:
        """
        Analyze system metrics and provide intelligent insights.

        Args:
            metrics: System metrics data
            context: Additional context for analysis

        Returns:
            GPTDecision with analysis and recommendations
        """
        prompt = self._build_analysis_prompt(metrics, context)

        try:
            response = await self._make_request(prompt)
            decision = self._parse_analysis_response(response)

            # Add to history
            self.decision_history.append(decision)
            if len(self.decision_history) > self.max_history:
                self.decision_history.pop(0)

            logger.info(
                f"Analysis completed: {decision.decision} (confidence: {decision.confidence})"
            )
            return decision

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return self._create_fallback_decision(
                "Continue monitoring", f"Analysis failed: {e}", 0.5
            )

    async def recommend_remediation(
        self, issue: str, metrics: Dict[str, Any], available_actions: List[str]
    ) -> GPTDecision:
        """
        Recommend remediation actions for detected issues.

        Args:
            issue: Description of the issue
            metrics: Current system metrics
            available_actions: List of available remediation actions

        Returns:
            GPTDecision with recommended action and reasoning
        """
        prompt = self._build_remediation_prompt(issue, metrics, available_actions)

        try:
            response = await self._make_request(prompt)
            decision = self._parse_remediation_response(response)

            # Safety check for high-risk actions
            if decision.risk_level in ["high", "critical"]:
                decision = self._apply_safety_checks(decision, metrics)

            # Add to history
            self.decision_history.append(decision)
            if len(self.decision_history) > self.max_history:
                self.decision_history.pop(0)

            logger.info(
                f"Remediation recommended: {decision.decision} (risk: {decision.risk_level})"
            )
            return decision

        except Exception as e:
            logger.error(f"Remediation recommendation failed: {e}")
            return self._create_fallback_decision(
                "Monitor situation", f"Recommendation failed: {e}", 0.3
            )

    async def detect_anomalies(
        self, metrics: Dict[str, Any], historical_context: List[Dict[str, Any]] = None
    ) -> GPTDecision:
        """
        Detect anomalies in system metrics using GPT intelligence.

        Args:
            metrics: Current system metrics
            historical_context: Historical metrics for trend analysis

        Returns:
            GPTDecision with anomaly detection results
        """
        prompt = self._build_anomaly_prompt(metrics, historical_context)

        try:
            response = await self._make_request(prompt)
            decision = self._parse_anomaly_response(response)

            # Add to history
            self.decision_history.append(decision)
            if len(self.decision_history) > self.max_history:
                self.decision_history.pop(0)

            logger.info(
                f"Anomaly detection: {decision.decision} (confidence: {decision.confidence})"
            )
            return decision

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return self._create_fallback_decision(
                "No anomalies detected", f"Detection failed: {e}", 0.4
            )

    def _build_analysis_prompt(self, metrics: Dict[str, Any], context: str) -> str:
        """Build prompt for metric analysis."""
        return f"""
You are an intelligent system monitoring AI. Analyze the following system metrics and provide insights.

Current Metrics:
{json.dumps(metrics, indent=2)}

Context: {context}

Recent Decisions (for context):
{self._format_decision_history()}

Provide a structured analysis with:
1. Overall system health assessment
2. Key observations and trends
3. Potential issues or concerns
4. Recommended monitoring focus areas

Respond in JSON format:
{{
    "decision": "brief summary of analysis",
    "reasoning": "detailed explanation of findings",
    "confidence": 0.85,
    "risk_level": "low|medium|high|critical",
    "alternatives": ["alternative interpretation 1", "alternative interpretation 2"],
    "metadata": {{
        "health_score": 0.9,
        "trends": ["increasing CPU usage", "stable memory"],
        "concerns": ["high disk usage"]
    }}
}}
"""

    def _build_remediation_prompt(
        self, issue: str, metrics: Dict[str, Any], available_actions: List[str]
    ) -> str:
        """Build prompt for remediation recommendations."""
        return f"""
You are an intelligent system remediation AI. Recommend actions to address the following issue.

Issue: {issue}

Current Metrics:
{json.dumps(metrics, indent=2)}

Available Actions:
{json.dumps(available_actions, indent=2)}

Recent Decisions (for context):
{self._format_decision_history()}

Consider:
1. Safety and potential side effects
2. Effectiveness of each action
3. System impact and recovery time
4. Risk level of each action

Respond in JSON format:
{{
    "decision": "recommended action",
    "reasoning": "why this action is recommended",
    "confidence": 0.8,
    "risk_level": "low|medium|high|critical",
    "alternatives": ["alternative action 1", "alternative action 2"],
    "metadata": {{
        "estimated_impact": "low|medium|high",
        "recovery_time": "immediate|short|medium|long",
        "side_effects": ["potential side effect 1", "potential side effect 2"]
    }}
}}
"""

    def _build_anomaly_prompt(
        self, metrics: Dict[str, Any], historical_context: List[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for anomaly detection."""
        historical_data = ""
        if historical_context:
            historical_data = f"\nHistorical Context (last 5 data points):\n{json.dumps(historical_context[-5:], indent=2)}"

        return f"""
You are an intelligent anomaly detection AI. Analyze the following metrics for anomalies.

Current Metrics:
{json.dumps(metrics, indent=2)}
{historical_data}

Recent Decisions (for context):
{self._format_decision_history()}

Look for:
1. Unusual patterns or spikes
2. Deviations from normal ranges
3. Correlations between different metrics
4. Potential system issues

Respond in JSON format:
{{
    "decision": "anomaly summary",
    "reasoning": "detailed explanation of detected anomalies",
    "confidence": 0.9,
    "risk_level": "low|medium|high|critical",
    "alternatives": ["alternative interpretation 1", "alternative interpretation 2"],
    "metadata": {{
        "anomalies_detected": ["anomaly 1", "anomaly 2"],
        "severity": "low|medium|high|critical",
        "affected_metrics": ["cpu", "memory"]
    }}
}}
"""

    def _format_decision_history(self) -> str:
        """Format recent decision history for context."""
        if not self.decision_history:
            return "No recent decisions"

        history = []
        for decision in self.decision_history[-3:]:  # Last 3 decisions
            history.append(f"- {decision.decision} (confidence: {decision.confidence})")

        return "\n".join(history)

    async def _make_request(self, prompt: str) -> str:
        """Make request to GPT API with retry logic and model fallback."""
        await self._ensure_model()
        for attempt in range(self.retry_attempts):
            try:
                logger.info(
                    f"Making GPT request (attempt {attempt + 1}) with model {self.model}"
                )
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an intelligent system monitoring and remediation AI. Provide accurate, safe, and actionable recommendations.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    response_format={"type": "json_object"},
                )
                return response.choices[0].message.content
            except Exception as e:
                # Check for model_not_found error and fallback
                if hasattr(e, "status_code") and e.status_code == 404:
                    logger.warning(
                        f"Model '{self.model}' not found (404). Falling back to '{self.fallback_model}' and retrying."
                    )
                    self.model = self.fallback_model
                    self._model_checked = True
                    continue
                if "model_not_found" in str(e):
                    logger.warning(
                        f"Model '{self.model}' not found. Falling back to '{self.fallback_model}' and retrying."
                    )
                    self.model = self.fallback_model
                    self._model_checked = True
                    continue
                # Check for quota exceeded (429 insufficient_quota)
                if (
                    hasattr(e, "status_code") and e.status_code == 429
                ) or "insufficient_quota" in str(e):
                    logger.error(f"OpenAI quota exceeded: {e}")
                    # Broadcast a critical alert and activate fallback if not already active
                    if not config.is_llm_fallback_active():
                        config.activate_llm_fallback("OpenAI API quota exceeded.")
                        asyncio.create_task(
                            message_bus.broadcast(
                                sender="GPTClient",
                                message_type=MessageType.ALERT,
                                content={
                                    "type": "llm_quota_exceeded",
                                    "severity": "critical",
                                    "message": "OpenAI API quota exceeded. System is switching to fallback LLM until quota is restored.",
                                    "timestamp": datetime.now().isoformat(),
                                },
                                priority=MessagePriority.CRITICAL,
                            )
                        )
                    raise LLMQuotaExceeded("OpenAI API quota exceeded.")
                logger.warning(f"GPT request failed (attempt {attempt + 1}): {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise e

    def _parse_analysis_response(self, response: str) -> GPTDecision:
        """Parse GPT response for analysis."""
        try:
            data = json.loads(response)
            return GPTDecision(**data)
        except Exception as e:
            logger.error(f"Failed to parse analysis response: {e}")
            return self._create_fallback_decision(
                "Analysis parsing failed", str(e), 0.3
            )

    def _parse_remediation_response(self, response: str) -> GPTDecision:
        """Parse GPT response for remediation."""
        try:
            data = json.loads(response)
            return GPTDecision(**data)
        except Exception as e:
            logger.error(f"Failed to parse remediation response: {e}")
            return self._create_fallback_decision(
                "Remediation parsing failed", str(e), 0.3
            )

    def _parse_anomaly_response(self, response: str) -> GPTDecision:
        """Parse GPT response for anomaly detection."""
        try:
            data = json.loads(response)
            return GPTDecision(**data)
        except Exception as e:
            logger.error(f"Failed to parse anomaly response: {e}")
            return self._create_fallback_decision("Anomaly parsing failed", str(e), 0.3)

    def _apply_safety_checks(
        self, decision: GPTDecision, metrics: Dict[str, Any]
    ) -> GPTDecision:
        """Apply safety checks to high-risk decisions."""
        # Check if system is already under stress
        cpu_high = metrics.get("cpu_percent", 0) > 90
        memory_high = metrics.get("memory_percent", 0) > 90

        if cpu_high or memory_high:
            logger.warning(
                f"System under stress, downgrading risk level from {decision.risk_level}"
            )
            decision.risk_level = "medium"  # Downgrade risk
            decision.confidence *= 0.8  # Reduce confidence
            decision.reasoning += " (Risk downgraded due to system stress)"

        return decision

    def _create_fallback_decision(
        self, decision: str, reasoning: str, confidence: float
    ) -> GPTDecision:
        """Create a fallback decision when GPT fails."""
        return GPTDecision(
            decision=decision,
            reasoning=reasoning,
            confidence=confidence,
            risk_level="low",
            alternatives=["Wait and monitor", "Manual intervention"],
            metadata={"fallback": True, "timestamp": datetime.now().isoformat()},
        )

    def get_decision_history(self) -> List[GPTDecision]:
        """Get recent decision history."""
        return self.decision_history.copy()

    def clear_history(self):
        """Clear decision history."""
        self.decision_history.clear()
        logger.info("Decision history cleared")

    async def health_check(self) -> bool:
        """Check if the OpenAI API is reachable."""
        try:
            # Make a minimal request to the OpenAI API
            response = await self.client.models.list()
            return bool(response.data)
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False


# Global GPT client instance
gpt_client = GPTClient()
