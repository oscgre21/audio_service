"""
Interfaz para cola de procesamiento de mensajes
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MessagePriority(Enum):
    """Prioridades de mensaje para procesamiento"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class QueuedMessage:
    """Mensaje en cola con metadata adicional"""
    id: str
    message: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    enqueued_at: datetime = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.enqueued_at is None:
            self.enqueued_at = datetime.now()
    
    def increment_retry(self) -> bool:
        """
        Incrementa el contador de reintentos.
        Returns: True si puede reintentar, False si excedió el límite
        """
        self.retry_count += 1
        return self.retry_count <= self.max_retries


class ProcessingQueue(ABC):
    """
    Interfaz para cola de procesamiento FIFO con soporte de prioridades.
    
    Permite encolar mensajes para procesamiento ordenado,
    desacoplando la recepción del procesamiento.
    """
    
    @abstractmethod
    async def enqueue(self, message: Dict[str, Any], priority: MessagePriority = MessagePriority.NORMAL) -> bool:
        """
        Agrega un mensaje a la cola.
        
        Args:
            message: Mensaje a encolar
            priority: Prioridad del mensaje
            
        Returns:
            True si se encoló exitosamente, False si la cola está llena
        """
        pass
    
    @abstractmethod
    async def dequeue(self) -> Optional[QueuedMessage]:
        """
        Obtiene y remueve el siguiente mensaje de la cola.
        Respeta prioridades: mensajes con mayor prioridad salen primero.
        
        Returns:
            QueuedMessage si hay mensajes, None si la cola está vacía
        """
        pass
    
    @abstractmethod
    async def peek(self) -> Optional[QueuedMessage]:
        """
        Mira el siguiente mensaje sin removerlo de la cola.
        
        Returns:
            QueuedMessage si hay mensajes, None si la cola está vacía
        """
        pass
    
    @abstractmethod
    async def requeue(self, message: QueuedMessage) -> bool:
        """
        Re-encola un mensaje (útil para reintentos).
        
        Args:
            message: Mensaje a re-encolar
            
        Returns:
            True si se re-encoló exitosamente
        """
        pass
    
    @abstractmethod
    def size(self) -> int:
        """
        Obtiene la cantidad de mensajes en cola.
        
        Returns:
            Número de mensajes en la cola
        """
        pass
    
    @abstractmethod
    def is_empty(self) -> bool:
        """
        Verifica si la cola está vacía.
        
        Returns:
            True si no hay mensajes en la cola
        """
        pass
    
    @abstractmethod
    def is_full(self) -> bool:
        """
        Verifica si la cola está llena.
        
        Returns:
            True si la cola alcanzó su capacidad máxima
        """
        pass
    
    @abstractmethod
    async def clear(self) -> int:
        """
        Limpia todos los mensajes de la cola.
        
        Returns:
            Número de mensajes que fueron removidos
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la cola.
        
        Returns:
            Dict con estadísticas (tamaño, mensajes por prioridad, etc.)
        """
        pass
    
    @abstractmethod
    async def get_messages_by_priority(self, priority: MessagePriority) -> List[QueuedMessage]:
        """
        Obtiene todos los mensajes de una prioridad específica sin removerlos.
        
        Args:
            priority: Prioridad a filtrar
            
        Returns:
            Lista de mensajes con la prioridad especificada
        """
        pass