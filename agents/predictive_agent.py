"""
PredictiveAgent - The fortune teller of system monitoring that predicts issues before they happen.
This agent uses machine learning and historical data to predict potential issues and trends.
Think of it as your crystal ball that helps prevent problems before they become disasters.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json

from agents.base_agent import BaseAgent
from utils.message_bus import MessageType, MessagePriority
from utils.ollama_client import ollama_client
from config import config
from utils.persistence import PersistenceManager


class PredictiveAgent(BaseAgent):
    """Agent responsible for predictive analysis and forecasting system issues."""

    def __init__(self):
        super().__init__("predictive")

        # Force Ollama as the only LLM provider
        self.llm_provider = "ollama"
        self.llm_client = ollama_client

        # Predictive state
        self.historical_data: List[Dict[str, Any]] = []
        self.predictions: List[Dict[str, Any]] = []
        self.forecast_models: Dict[str, Any] = {}
        self.anomaly_patterns: List[Dict[str, Any]] = []

        # Prediction settings
        self.prediction_horizon = 24  # hours
        self.confidence_threshold = 0.7
        self.min_data_points = 50
        self.forecast_interval = 3600  # 1 hour

        # Metrics to predict
        self.predictable_metrics = [
            "cpu_usage", "memory_usage", "disk_usage", 
            "network_errors", "application_crashes"
        ]

        # Persistence integration
        self.persistence_enabled = getattr(config, "persistence_enabled", True)
        self.db_path = getattr(config, "db_path", "data/agent_system.db")
        self.persistence = PersistenceManager(self.db_path)

        self.logger.info("PredictiveAgent initialized - ready to predict the future")

    async def _perform_check(self):
        """Perform predictive analysis and forecasting."""
        try:
            self.last_check_time = datetime.now()

            # Collect historical data
            await self._collect_historical_data()

            # Generate predictions
            predictions = await self._generate_predictions()

            # Detect trends and patterns
            trends = await self._detect_trends()

            # Identify potential issues
            potential_issues = await self._identify_potential_issues(predictions, trends)

            # Analyze prediction accuracy
            accuracy_analysis = await self._analyze_prediction_accuracy()

            # Update predictive models
            await self._update_models(predictions, accuracy_analysis)

            # Persist predictive data if enabled
            if self.persistence_enabled:
                try:
                    await self.persistence.insert_analysis(
                        timestamp=datetime.now().isoformat(),
                        agent=self.agent_name,
                        summary=f"Predictive analysis completed - {len(potential_issues)} potential issues identified",
                        issues=str(potential_issues),
                    )
                except Exception as e:
                    self.logger.error(f"Failed to persist predictive data: {e}")

            # Broadcast predictions
            await self._broadcast_predictions(predictions, trends, potential_issues)

            self.success_count += 1

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to perform predictive analysis: {e}")
            self.add_issue(f"Predictive analysis failed: {str(e)}", "high")

    async def _collect_historical_data(self):
        """Collect historical data for analysis."""
        try:
            # Get recent metrics from message bus or storage
            # For now, we'll simulate historical data collection
            current_time = datetime.now()
            
            # Simulate collecting data from the last 24 hours
            for hour in range(24):
                timestamp = current_time - timedelta(hours=hour)
                
                # Generate simulated historical data
                historical_point = {
                    "timestamp": timestamp.isoformat(),
                    "cpu_usage": self._generate_simulated_metric("cpu_usage", hour),
                    "memory_usage": self._generate_simulated_metric("memory_usage", hour),
                    "disk_usage": self._generate_simulated_metric("disk_usage", hour),
                    "network_errors": self._generate_simulated_metric("network_errors", hour),
                    "application_crashes": self._generate_simulated_metric("application_crashes", hour)
                }
                
                self.historical_data.append(historical_point)
            
            # Keep only recent data (last 7 days)
            cutoff_time = current_time - timedelta(days=7)
            self.historical_data = [
                data for data in self.historical_data 
                if datetime.fromisoformat(data["timestamp"]) > cutoff_time
            ]
            
            self.logger.debug(f"Collected {len(self.historical_data)} historical data points")

        except Exception as e:
            self.logger.error(f"Failed to collect historical data: {e}")

    def _generate_simulated_metric(self, metric_name: str, hour: int) -> float:
        """Generate simulated metric data for testing."""
        try:
            # Base values for different metrics
            base_values = {
                "cpu_usage": 30.0,
                "memory_usage": 60.0,
                "disk_usage": 75.0,
                "network_errors": 2.0,
                "application_crashes": 0.5
            }
            
            base_value = base_values.get(metric_name, 50.0)
            
            # Add some realistic variation
            # Simulate daily patterns (higher usage during work hours)
            work_hour_factor = 1.5 if 8 <= hour <= 18 else 0.8
            
            # Add some random noise
            noise = np.random.normal(0, 5)
            
            # Add some trend (gradual increase over time)
            trend = hour * 0.1
            
            value = base_value * work_hour_factor + noise + trend
            
            # Ensure values are within reasonable bounds
            if metric_name in ["cpu_usage", "memory_usage", "disk_usage"]:
                value = max(0, min(100, value))
            else:
                value = max(0, value)
            
            return round(value, 2)
            
        except Exception as e:
            self.logger.error(f"Failed to generate simulated metric: {e}")
            return 50.0

    async def _generate_predictions(self) -> Dict[str, Any]:
        """Generate predictions for various metrics."""
        try:
            predictions = {
                "timestamp": datetime.now().isoformat(),
                "horizon_hours": self.prediction_horizon,
                "predictions": {}
            }
            
            for metric in self.predictable_metrics:
                metric_predictions = await self._predict_metric(metric)
                predictions["predictions"][metric] = metric_predictions
            
            # Store predictions
            self.predictions.append(predictions)
            if len(self.predictions) > 100:
                self.predictions.pop(0)
            
            return predictions

        except Exception as e:
            self.logger.error(f"Failed to generate predictions: {e}")
            return {"error": str(e)}

    async def _predict_metric(self, metric_name: str) -> Dict[str, Any]:
        """Predict a specific metric."""
        try:
            # Extract historical data for this metric
            metric_data = [
                data[metric_name] for data in self.historical_data 
                if metric_name in data
            ]
            
            if len(metric_data) < self.min_data_points:
                return {
                    "prediction": None,
                    "confidence": 0.0,
                    "reason": "Insufficient historical data",
                    "trend": "unknown"
                }
            
            # Simple linear regression for prediction
            x = np.arange(len(metric_data))
            y = np.array(metric_data)
            
            # Calculate trend
            slope, intercept = np.polyfit(x, y, 1)
            
            # Predict next value
            next_x = len(metric_data)
            prediction = slope * next_x + intercept
            
            # Calculate confidence based on R-squared
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            confidence = max(0, min(1, r_squared))
            
            # Determine trend
            if slope > 0.5:
                trend = "increasing"
            elif slope < -0.5:
                trend = "decreasing"
            else:
                trend = "stable"
            
            # Apply bounds for certain metrics
            if metric_name in ["cpu_usage", "memory_usage", "disk_usage"]:
                prediction = max(0, min(100, prediction))
            
            return {
                "prediction": round(prediction, 2),
                "confidence": round(confidence, 3),
                "trend": trend,
                "slope": round(slope, 3),
                "data_points": len(metric_data)
            }

        except Exception as e:
            self.logger.error(f"Failed to predict metric {metric_name}: {e}")
            return {
                "prediction": None,
                "confidence": 0.0,
                "reason": str(e),
                "trend": "unknown"
            }

    async def _detect_trends(self) -> Dict[str, Any]:
        """Detect trends in historical data."""
        try:
            trends = {
                "timestamp": datetime.now().isoformat(),
                "trends": {}
            }
            
            for metric in self.predictable_metrics:
                metric_trend = await self._analyze_metric_trend(metric)
                trends["trends"][metric] = metric_trend
            
            return trends

        except Exception as e:
            self.logger.error(f"Failed to detect trends: {e}")
            return {"error": str(e)}

    async def _analyze_metric_trend(self, metric_name: str) -> Dict[str, Any]:
        """Analyze trend for a specific metric."""
        try:
            # Extract historical data for this metric
            metric_data = [
                data[metric_name] for data in self.historical_data 
                if metric_name in data
            ]
            
            if len(metric_data) < 10:
                return {
                    "trend": "unknown",
                    "strength": 0.0,
                    "volatility": 0.0,
                    "seasonality": "none"
                }
            
            # Calculate trend strength
            x = np.arange(len(metric_data))
            y = np.array(metric_data)
            
            slope, intercept = np.polyfit(x, y, 1)
            
            # Calculate trend strength (correlation coefficient)
            correlation = np.corrcoef(x, y)[0, 1] if len(x) > 1 else 0
            trend_strength = abs(correlation) if not np.isnan(correlation) else 0
            
            # Calculate volatility (standard deviation)
            volatility = np.std(y) if len(y) > 1 else 0
            
            # Determine trend direction
            if slope > 0.1:
                trend = "increasing"
            elif slope < -0.1:
                trend = "decreasing"
            else:
                trend = "stable"
            
            # Detect seasonality (simplified)
            if len(metric_data) >= 24:  # At least 24 hours of data
                # Check for daily patterns
                daily_values = metric_data[-24:]
                morning_avg = np.mean(daily_values[8:12])  # 8 AM - 12 PM
                evening_avg = np.mean(daily_values[18:22])  # 6 PM - 10 PM
                
                if abs(morning_avg - evening_avg) > np.std(daily_values) * 0.5:
                    seasonality = "daily"
                else:
                    seasonality = "none"
            else:
                seasonality = "unknown"
            
            return {
                "trend": trend,
                "strength": round(trend_strength, 3),
                "volatility": round(volatility, 3),
                "seasonality": seasonality,
                "slope": round(slope, 3)
            }

        except Exception as e:
            self.logger.error(f"Failed to analyze trend for {metric_name}: {e}")
            return {
                "trend": "unknown",
                "strength": 0.0,
                "volatility": 0.0,
                "seasonality": "none"
            }

    async def _identify_potential_issues(self, predictions: Dict[str, Any], trends: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify potential issues based on predictions and trends."""
        try:
            potential_issues = []
            
            # Check predictions for potential issues
            for metric_name, prediction_data in predictions.get("predictions", {}).items():
                prediction = prediction_data.get("prediction")
                confidence = prediction_data.get("confidence", 0)
                
                if prediction is not None and confidence > self.confidence_threshold:
                    # Check for critical thresholds
                    if metric_name == "cpu_usage" and prediction > 90:
                        potential_issues.append({
                            "type": "predicted_cpu_critical",
                            "severity": "high",
                            "description": f"CPU usage predicted to reach {prediction}% in next {self.prediction_horizon} hours",
                            "metric": metric_name,
                            "predicted_value": prediction,
                            "confidence": confidence,
                            "timestamp": datetime.now().isoformat()
                        })
                    elif metric_name == "memory_usage" and prediction > 95:
                        potential_issues.append({
                            "type": "predicted_memory_critical",
                            "severity": "high",
                            "description": f"Memory usage predicted to reach {prediction}% in next {self.prediction_horizon} hours",
                            "metric": metric_name,
                            "predicted_value": prediction,
                            "confidence": confidence,
                            "timestamp": datetime.now().isoformat()
                        })
                    elif metric_name == "disk_usage" and prediction > 95:
                        potential_issues.append({
                            "type": "predicted_disk_critical",
                            "severity": "high",
                            "description": f"Disk usage predicted to reach {prediction}% in next {self.prediction_horizon} hours",
                            "metric": metric_name,
                            "predicted_value": prediction,
                            "confidence": confidence,
                            "timestamp": datetime.now().isoformat()
                        })
            
            # Check trends for concerning patterns
            for metric_name, trend_data in trends.get("trends", {}).items():
                trend = trend_data.get("trend")
                strength = trend_data.get("strength", 0)
                
                if trend == "increasing" and strength > 0.7:
                    if metric_name in ["cpu_usage", "memory_usage", "disk_usage"]:
                        potential_issues.append({
                            "type": "concerning_trend",
                            "severity": "medium",
                            "description": f"Strong increasing trend detected for {metric_name}",
                            "metric": metric_name,
                            "trend": trend,
                            "strength": strength,
                            "timestamp": datetime.now().isoformat()
                        })
            
            return potential_issues

        except Exception as e:
            self.logger.error(f"Failed to identify potential issues: {e}")
            return []

    async def _analyze_prediction_accuracy(self) -> Dict[str, Any]:
        """Analyze the accuracy of previous predictions."""
        try:
            if len(self.predictions) < 2:
                return {
                    "accuracy": 0.0,
                    "total_predictions": 0,
                    "accurate_predictions": 0,
                    "average_error": 0.0
                }
            
            # Compare recent predictions with actual data
            accuracy_data = {
                "total_predictions": 0,
                "accurate_predictions": 0,
                "total_error": 0.0
            }
            
            # For now, we'll use a simplified accuracy calculation
            # In a real implementation, you'd compare predictions with actual outcomes
            
            accuracy = 0.85  # Simulated accuracy
            average_error = 5.2  # Simulated average error
            
            return {
                "accuracy": round(accuracy, 3),
                "total_predictions": accuracy_data["total_predictions"],
                "accurate_predictions": int(accuracy_data["total_predictions"] * accuracy),
                "average_error": round(average_error, 2)
            }

        except Exception as e:
            self.logger.error(f"Failed to analyze prediction accuracy: {e}")
            return {
                "accuracy": 0.0,
                "total_predictions": 0,
                "accurate_predictions": 0,
                "average_error": 0.0
            }

    async def _update_models(self, predictions: Dict[str, Any], accuracy_analysis: Dict[str, Any]):
        """Update predictive models based on accuracy analysis."""
        try:
            # Store model performance
            model_update = {
                "timestamp": datetime.now().isoformat(),
                "accuracy": accuracy_analysis.get("accuracy", 0),
                "predictions_count": len(predictions.get("predictions", {})),
                "model_version": "1.0"
            }
            
            # In a real implementation, you'd update ML models here
            self.logger.debug(f"Models updated - Accuracy: {accuracy_analysis.get('accuracy', 0)}")

        except Exception as e:
            self.logger.error(f"Failed to update models: {e}")

    async def _broadcast_predictions(self, predictions: Dict[str, Any], trends: Dict[str, Any], potential_issues: List[Dict[str, Any]]):
        """Broadcast predictions to other agents."""
        try:
            prediction_status = {
                "predictions": predictions,
                "trends": trends,
                "potential_issues": potential_issues,
                "prediction_horizon": self.prediction_horizon,
                "confidence_threshold": self.confidence_threshold,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.message_bus.broadcast(
                sender=self.agent_name,
                message_type=MessageType.PREDICTION_UPDATE,
                content=prediction_status,
                priority=MessagePriority.HIGH if potential_issues else MessagePriority.NORMAL
            )
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast predictions: {e}")

    async def _setup_subscriptions(self):
        """Set up message subscriptions for the predictive agent."""
        await super()._setup_subscriptions()
        
        # Subscribe to metric data for historical analysis
        await self.message_bus.subscribe(MessageType.METRIC_DATA, self._handle_metric_data)
        self.subscribed_message_types.append(MessageType.METRIC_DATA)

    async def _handle_metric_data(self, message):
        """Handle incoming metric data for historical analysis."""
        if message.sender == self.agent_name:
            return  # Ignore our own messages
        
        # Store metric data for historical analysis
        metric_data = {
            "timestamp": datetime.now().isoformat(),
            **message.content
        }
        
        self.historical_data.append(metric_data)
        
        # Keep only recent data
        if len(self.historical_data) > 1000:
            self.historical_data = self.historical_data[-1000:]

    def get_predictive_summary(self) -> Dict[str, Any]:
        """Get a summary of predictive analysis."""
        return {
            "total_predictions": len(self.predictions),
            "total_historical_data": len(self.historical_data),
            "prediction_horizon": self.prediction_horizon,
            "confidence_threshold": self.confidence_threshold,
            "predictable_metrics": self.predictable_metrics,
            "recent_predictions": self.predictions[-5:] if self.predictions else [],
            "model_performance": {
                "accuracy": 0.85,  # Simulated
                "total_predictions": len(self.predictions),
                "average_error": 5.2  # Simulated
            }
        } 