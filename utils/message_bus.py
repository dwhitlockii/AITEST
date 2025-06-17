"""
Message bus for inter-agent communication in the multi-agent monitoring system.
Think of this as the nervous system - messages flow between agents like electrical impulses.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Coroutine
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from .logger import create_agent_logger

logger = create_agent_logger("MessageBus")

class MessageType(Enum):
    """Types of messages that can be sent between agents."""
    METRIC_DATA = "metric_data"
    ALERT = "alert"
    REMEDIATION_REQUEST = "remediation_request"
    REMEDIATION_RESULT = "remediation_result"
    STATUS_UPDATE = "status_update"
    HEALTH_CHECK = "health_check"
    TREND_ANALYSIS = "trend_analysis"
    SYSTEM_COMMAND = "system_command"
    COORDINATION = "coordination"

class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

@dataclass
class Message:
    """Structured message for inter-agent communication."""
    id: str
    type: MessageType
    priority: MessagePriority
    sender: str
    recipients: List[str]
    content: Dict[str, Any]
    timestamp: datetime
    ttl: Optional[int] = None  # Time to live in seconds
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        data = asdict(self)
        data['type'] = self.type.value
        data['priority'] = self.priority.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        data['type'] = MessageType(data['type'])
        data['priority'] = MessagePriority(data['priority'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if message has expired based on TTL."""
        if self.ttl is None:
            return False
        return datetime.now() - self.timestamp > timedelta(seconds=self.ttl)

class MessageBus:
    """Central message bus for coordinating all agent communication."""
    
    def __init__(self, max_queue_size: int = 1000, retention_time: int = 300):
        self.max_queue_size = max_queue_size
        self.retention_time = retention_time
        
        # Message queues by priority
        self.queues: Dict[MessagePriority, asyncio.Queue] = {
            priority: asyncio.Queue(maxsize=max_queue_size // 5)  # Divide by priority levels
            for priority in MessagePriority
        }
        
        # Subscribers by message type
        self.subscribers: Dict[MessageType, List[Callable]] = {
            msg_type: [] for msg_type in MessageType
        }
        
        # Message history for debugging
        self.message_history: List[Message] = []
        self.max_history_size = 1000
        
        # Running state
        self.running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("Message bus initialized")
    
    async def start(self):
        """Start the message bus."""
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Message bus started")
    
    async def stop(self):
        """Stop the message bus."""
        self.running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Message bus stopped")
    
    async def publish(self, message: Message) -> bool:
        """Publish a message to the bus."""
        try:
            # Add to appropriate priority queue
            await self.queues[message.priority].put(message)
            
            # Add to history
            self.message_history.append(message)
            if len(self.message_history) > self.max_history_size:
                self.message_history.pop(0)
            
            # Notify subscribers
            await self._notify_subscribers(message)
            
            logger.debug(f"Message published: {message.type.value} from {message.sender}")
            return True
            
        except asyncio.QueueFull:
            logger.warning(f"Message queue full, dropping message: {message.type.value}")
            return False
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    async def subscribe(self, message_type: MessageType, callback: Callable[[Message], Coroutine[None, None, None]]):
        """Subscribe to messages of a specific type."""
        self.subscribers[message_type].append(callback)
        logger.debug(f"Subscriber added for {message_type.value}")
    
    async def unsubscribe(self, message_type: MessageType, callback: Callable):
        """Unsubscribe from messages of a specific type."""
        if callback in self.subscribers[message_type]:
            self.subscribers[message_type].remove(callback)
            logger.debug(f"Subscriber removed for {message_type.value}")
    
    async def get_message(self, priority: MessagePriority = MessagePriority.NORMAL, 
                         timeout: float = 1.0) -> Optional[Message]:
        """Get a message from the bus with priority handling."""
        try:
            # Try high priority queues first
            for p in sorted(MessagePriority, key=lambda x: x.value, reverse=True):
                if p.value >= priority.value:
                    try:
                        return await asyncio.wait_for(self.queues[p].get(), timeout=timeout)
                    except asyncio.TimeoutError:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get message: {e}")
            return None
    
    async def send_direct(self, sender: str, recipient: str, message_type, 
                         content: Dict[str, Any], priority = MessagePriority.NORMAL) -> bool:
        """Send a direct message to a specific recipient."""
        # Ensure enums
        if isinstance(message_type, str):
            message_type = MessageType(message_type)
        if isinstance(priority, str):
            priority = MessagePriority[priority.upper()] if priority.isalpha() else MessagePriority(int(priority))
        message = Message(
            id=str(uuid.uuid4()),
            type=message_type,
            priority=priority,
            sender=sender,
            recipients=[recipient],
            content=content,
            timestamp=datetime.now()
        )
        return await self.publish(message)
    
    async def broadcast(self, sender: str, message_type, 
                       content: Dict[str, Any], priority = MessagePriority.NORMAL) -> bool:
        """Broadcast a message to all agents."""
        # Ensure enums
        if isinstance(message_type, str):
            message_type = MessageType(message_type)
        if isinstance(priority, str):
            priority = MessagePriority[priority.upper()] if priority.isalpha() else MessagePriority(int(priority))
        message = Message(
            id=str(uuid.uuid4()),
            type=message_type,
            priority=priority,
            sender=sender,
            recipients=[],  # Empty means broadcast
            content=content,
            timestamp=datetime.now()
        )
        return await self.publish(message)
    
    async def _notify_subscribers(self, message: Message):
        """Notify all subscribers for a message type."""
        subscribers = self.subscribers.get(message.type, [])
        
        if not subscribers:
            return
        
        # Create tasks for all subscribers
        tasks = []
        for callback in subscribers:
            try:
                task = asyncio.create_task(callback(message))
                tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to create subscriber task: {e}")
        
        # Wait for all subscribers to process the message
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error in subscriber processing: {e}")
    
    async def _cleanup_loop(self):
        """Background task to clean up expired messages."""
        while self.running:
            try:
                # Clean up expired messages from history
                current_time = datetime.now()
                self.message_history = [
                    msg for msg in self.message_history
                    if not msg.is_expired()
                ]
                
                # Clean up expired messages from queues
                for priority, queue in self.queues.items():
                    # Note: This is a simplified cleanup. In production, you might want
                    # a more sophisticated approach for queue cleanup
                    pass
                
                await asyncio.sleep(60)  # Clean up every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        return {
            "queue_sizes": {
                priority.name: queue.qsize() 
                for priority, queue in self.queues.items()
            },
            "subscriber_counts": {
                msg_type.value: len(subscribers)
                for msg_type, subscribers in self.subscribers.items()
            },
            "history_size": len(self.message_history),
            "running": self.running
        }
    
    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages for debugging."""
        recent = self.message_history[-limit:] if self.message_history else []
        return [msg.to_dict() for msg in recent]

# Global message bus instance
message_bus = MessageBus() 