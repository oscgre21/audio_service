"""
Interface para sistemas de mensajería
"""
from abc import ABC, abstractmethod
from typing import Callable, Any, Dict

from ...domain.entities import Message


class MessageQueue(ABC):
    """Interface para interactuar con sistemas de colas de mensajes"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establece conexión con el sistema de mensajería"""
        pass
    
    @abstractmethod
    async def consume(self, handler: Callable[[Message], None]) -> None:
        """
        Consume mensajes de la cola
        
        Args:
            handler: Función a ejecutar por cada mensaje recibido
        """
        pass
    
    @abstractmethod
    async def acknowledge(self, message_id: str) -> None:
        """Confirma que un mensaje fue procesado correctamente"""
        pass
    
    @abstractmethod
    async def reject(self, message_id: str, requeue: bool = False) -> None:
        """Rechaza un mensaje"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Cierra la conexión"""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Verifica si está conectado"""
        pass