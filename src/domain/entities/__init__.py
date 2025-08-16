"""
Entidades del dominio
"""
from .speech import Speech
from .audio import Audio
from .message import SpeechMessage
from .base_message import Message

__all__ = ["Speech", "Audio", "SpeechMessage", "Message"]