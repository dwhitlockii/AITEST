"""
Ollama client for local LLM communication without API keys.
This provides the same interface as GPT client but uses locally hosted models.
"""

import os
import asyncio
import json
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from config import config
from .logger import create_agent_logger
from utils.message_bus import message_bus, MessageType, MessagePriority

logger = create_agent_logger("OllamaClient")


class OllamaDecision(BaseModel):
    """Represents a decision made by Ollama with reasoning."""

    decision: str = Field(..., description="The decision or action to take")
    reasoning: str = Field(..., description="Explanation of why this decision was made")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level 0-1")
    risk_level: str = Field(..., description="Risk level: low, medium, high, critical")
    alternatives: List[str] = Field(
        default_factory=list, description="Alternative actions considered"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the decision"
    )


class OllamaClient:
    """Client for communicating with locally hosted Ollama models."""

    def __init__(self):
        self.base_url = getattr(config.ollama, "url", "http://localhost:11434")
        self.default_model = getattr(config.ollama, "model", "mistral")
        self.timeout = getattr(config.ollama, "timeout", 30)
        self.retry_attempts = getattr(config.ollama, "retry_attempts", 3)
        self.retry_delay = getattr(config.ollama, "retry_delay", 2)
        
        # Decision history for context
        self.decision_history: List[OllamaDecision] = []
        self.max_history = 50

        # Available models cache
        self.available_models = []
        self.last_model_check = None
        self.model_check_interval = 300  # 5 minutes

        logger.info(f"OllamaClient initialized with model: {self.default_model}")

    async def _ensure_model(self):
        """Ensure the default model is available."""
        if not self.available_models:
            await self._refresh_models()
        
        if self.default_model not in self.available_models:
            logger.warning(f"Default model {self.default_model} not available. Available: {self.available_models}")
            if self.available_models:
                self.default_model = self.available_models[0]
                logger.info(f"Using fallback model: {self.default_model}")

    async def _refresh_models(self):
        """Refresh the list of available models."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=self.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.available_models = [model["name"] for model in data.get("models", [])]
                        self.last_model_check = datetime.now()
                        logger.info(f"Available Ollama models: {self.available_models}")
                    else:
                        logger.error(f"Failed to get models: {response.status}")
        except Exception as e:
            logger.error(f"Error refreshing models: {e}")

    async def analyze_metrics(
        self, metrics: Dict[str, Any], context: str = ""
    ) -> OllamaDecision:
        """Analyze system metrics using Ollama."""
        await self._ensure_model()
        
        prompt = self._build_analysis_prompt(metrics, context)
        
        try:
            response = await self._make_request(prompt)
            return self._parse_analysis_response(response)
        except Exception as e:
            logger.error(f"Ollama analysis failed: {e}")
            return self._create_fallback_decision(
                "Monitor system closely",
                f"Analysis failed: {str(e)}. Recommend monitoring.",
                0.3
            )

    async def recommend_remediation(
        self, issue: str, metrics: Dict[str, Any], available_actions: List[str]
    ) -> OllamaDecision:
        """Get remediation recommendations from Ollama."""
        await self._ensure_model()
        
        prompt = self._build_remediation_prompt(issue, metrics, available_actions)
        
        try:
            response = await self._make_request(prompt)
            return self._parse_remediation_response(response)
        except Exception as e:
            logger.error(f"Ollama remediation recommendation failed: {e}")
            return self._create_fallback_decision(
                "Monitor and investigate",
                f"Remediation analysis failed: {str(e)}. Recommend manual investigation.",
                0.2
            )

    async def detect_anomalies(
        self, metrics: Dict[str, Any], historical_context: List[Dict[str, Any]] = None
    ) -> OllamaDecision:
        """Detect anomalies using Ollama."""
        await self._ensure_model()
        
        prompt = self._build_anomaly_prompt(metrics, historical_context)
        
        try:
            response = await self._make_request(prompt)
            return self._parse_anomaly_response(response)
        except Exception as e:
            logger.error(f"Ollama anomaly detection failed: {e}")
            return self._create_fallback_decision(
                "Continue monitoring",
                f"Anomaly detection failed: {str(e)}. Continue monitoring.",
                0.3
            )

    def _build_analysis_prompt(self, metrics: Dict[str, Any], context: str) -> str:
        """Build prompt for system analysis."""
        prompt = f"""You are an AI system analyst. Analyze the following system metrics and provide insights.

Context: {context}

System Metrics:
{json.dumps(metrics, indent=2)}

Recent Decision History:
{self._format_decision_history()}

Please analyze the system health and provide:
1. A clear decision about the current state
2. Detailed reasoning for your assessment
3. Confidence level (0.0-1.0)
4. Risk level (low/medium/high/critical)
5. Alternative actions to consider
6. Any additional insights

Respond in JSON format:
{{
    "decision": "your decision here",
    "reasoning": "detailed reasoning",
    "confidence": 0.85,
    "risk_level": "medium",
    "alternatives": ["action1", "action2"],
    "metadata": {{"insights": "additional info"}}
}}"""

        return prompt

    def _build_remediation_prompt(
        self, issue: str, metrics: Dict[str, Any], available_actions: List[str]
    ) -> str:
        """Build prompt for remediation recommendations."""
        prompt = f"""You are an AI system remediation expert. A system issue has been detected and you need to recommend safe actions.

Issue: {issue}

Current System Metrics:
{json.dumps(metrics, indent=2)}

Available Safe Actions:
{', '.join(available_actions)}

Recent Decision History:
{self._format_decision_history()}

Please recommend the best remediation action:
1. Choose the most appropriate action from the available list
2. Provide clear reasoning for your choice
3. Assess confidence level (0.0-1.0)
4. Evaluate risk level (low/medium/high/critical)
5. Suggest alternative approaches
6. Include any safety considerations

Respond in JSON format:
{{
    "decision": "recommended action",
    "reasoning": "why this action is best",
    "confidence": 0.8,
    "risk_level": "low",
    "alternatives": ["alternative1", "alternative2"],
    "metadata": {{"safety_notes": "safety considerations"}}
}}"""

        return prompt

    def _build_anomaly_prompt(
        self, metrics: Dict[str, Any], historical_context: List[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for anomaly detection."""
        historical_data = ""
        if historical_context:
            historical_data = f"\nHistorical Context (last {len(historical_context)} data points):\n{json.dumps(historical_context[-5:], indent=2)}"

        prompt = f"""You are an AI anomaly detection specialist. Analyze the current metrics for anomalies.

Current Metrics:
{json.dumps(metrics, indent=2)}{historical_data}

Recent Decision History:
{self._format_decision_history()}

Please detect any anomalies:
1. Identify unusual patterns or values
2. Assess the severity of any anomalies
3. Provide confidence in your detection (0.0-1.0)
4. Determine risk level (low/medium/high/critical)
5. Suggest monitoring or action recommendations
6. Note any affected metrics or systems

Respond in JSON format:
{{
    "decision": "anomaly assessment",
    "reasoning": "what anomalies were detected and why",
    "confidence": 0.75,
    "risk_level": "medium",
    "alternatives": ["monitor closely", "investigate further"],
    "metadata": {{
        "anomalies_detected": ["anomaly1", "anomaly2"],
        "severity": "medium",
        "affected_metrics": ["cpu", "memory"]
    }}
}}"""

        return prompt

    def _format_decision_history(self) -> str:
        """Format recent decision history for context."""
        if not self.decision_history:
            return "No recent decisions."
        
        recent = self.decision_history[-3:]  # Last 3 decisions
        formatted = []
        for decision in recent:
            formatted.append(f"- {decision.decision} (confidence: {decision.confidence}, risk: {decision.risk_level})")
        
        return "\n".join(formatted)

    async def _make_request(self, prompt: str) -> str:
        """Make request to Ollama API."""
        await self._ensure_model()
        
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Making Ollama request (attempt {attempt + 1}) with model {self.default_model}")
                
                payload = {
                    "model": self.default_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 1000
                    }
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get("response", "")
                        else:
                            logger.warning(f"Ollama request failed (attempt {attempt + 1}): {response.status}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"Ollama request timeout (attempt {attempt + 1})")
            except Exception as e:
                logger.warning(f"Ollama request failed (attempt {attempt + 1}): {e}")
            
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(self.retry_delay)
        
        raise Exception("All Ollama request attempts failed")

    def _parse_analysis_response(self, response: str) -> OllamaDecision:
        """Parse analysis response from Ollama."""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
            else:
                # Fallback parsing
                data = self._parse_fallback_response(response)
            
            decision = OllamaDecision(
                decision=data.get("decision", "Monitor system"),
                reasoning=data.get("reasoning", "No reasoning provided"),
                confidence=float(data.get("confidence", 0.5)),
                risk_level=data.get("risk_level", "medium"),
                alternatives=data.get("alternatives", []),
                metadata=data.get("metadata", {})
            )
            
            self._add_to_history(decision)
            return decision
            
        except Exception as e:
            logger.error(f"Failed to parse analysis response: {e}")
            return self._create_fallback_decision(
                "Continue monitoring",
                f"Failed to parse response: {str(e)}",
                0.3
            )

    def _parse_remediation_response(self, response: str) -> OllamaDecision:
        """Parse remediation response from Ollama."""
        return self._parse_analysis_response(response)  # Same parsing logic

    def _parse_anomaly_response(self, response: str) -> OllamaDecision:
        """Parse anomaly detection response from Ollama."""
        return self._parse_analysis_response(response)  # Same parsing logic

    def _parse_fallback_response(self, response: str) -> Dict[str, Any]:
        """Parse response when JSON extraction fails."""
        # Simple keyword-based parsing
        response_lower = response.lower()
        
        decision = "Monitor system"
        if "critical" in response_lower or "emergency" in response_lower:
            decision = "Immediate attention required"
        elif "warning" in response_lower:
            decision = "Investigate warning"
        elif "normal" in response_lower or "healthy" in response_lower:
            decision = "System appears normal"
        
        reasoning = response[:200] + "..." if len(response) > 200 else response
        
        confidence = 0.5
        if "high confidence" in response_lower or "certain" in response_lower:
            confidence = 0.8
        elif "low confidence" in response_lower or "uncertain" in response_lower:
            confidence = 0.3
        
        risk_level = "medium"
        if "critical" in response_lower:
            risk_level = "critical"
        elif "high" in response_lower:
            risk_level = "high"
        elif "low" in response_lower:
            risk_level = "low"
        
        return {
            "decision": decision,
            "reasoning": reasoning,
            "confidence": confidence,
            "risk_level": risk_level,
            "alternatives": ["Monitor closely", "Check logs"],
            "metadata": {"parsing_method": "fallback"}
        }

    def _create_fallback_decision(
        self, decision: str, reasoning: str, confidence: float
    ) -> OllamaDecision:
        """Create a fallback decision when Ollama is unavailable."""
        fallback = OllamaDecision(
            decision=decision,
            reasoning=reasoning,
            confidence=confidence,
            risk_level="medium",
            alternatives=["Monitor system", "Check logs"],
            metadata={"source": "fallback", "ollama_available": False}
        )
        
        self._add_to_history(fallback)
        return fallback

    def _add_to_history(self, decision: OllamaDecision):
        """Add decision to history."""
        self.decision_history.append(decision)
        if len(self.decision_history) > self.max_history:
            self.decision_history.pop(0)

    def get_decision_history(self) -> List[OllamaDecision]:
        """Get decision history."""
        return self.decision_history.copy()

    def clear_history(self):
        """Clear decision history."""
        self.decision_history.clear()

    async def health_check(self) -> bool:
        """Check if Ollama is available and healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=5) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """List available models."""
        await self._refresh_models()
        return self.available_models.copy()


# Global instance
ollama_client = OllamaClient()
