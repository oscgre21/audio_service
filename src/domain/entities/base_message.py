"""
Base Message entity
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


@dataclass
class Message:
    """Base message entity for all message types"""
    id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)