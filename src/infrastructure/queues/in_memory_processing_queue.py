"""
Implementación en memoria de la cola de procesamiento
"""
import asyncio
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from collections import defaultdict
import heapq

from ...application.interfaces import ProcessingQueue, QueuedMessage, MessagePriority

logger = logging.getLogger(__name__)


class InMemoryProcessingQueue(ProcessingQueue):
    """
    Implementación en memoria de la cola de procesamiento.
    
    Utiliza asyncio.Queue internamente con soporte para prioridades
    usando heapq para mantener el orden FIFO dentro de cada prioridad.
    """
    
    def __init__(self, max_size: Optional[int] = None):
        """
        Inicializa la cola con un tamaño máximo opcional.
        
        Args:
            max_size: Tamaño máximo de la cola (None = ilimitado)
        """
        self.max_size = max_size or 0
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=self.max_size)
        self._priority_queues: Dict[MessagePriority, List[QueuedMessage]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._total_processed = 0
        self._total_enqueued = 0
        self._total_failed = 0
        
        logger.info(f"InMemoryProcessingQueue initialized with max_size={max_size}")
    
    async def enqueue(self, message: Dict[str, Any], priority: MessagePriority = MessagePriority.NORMAL) -> bool:
        """
        Agrega un mensaje a la cola con la prioridad especificada.
        """
        try:
            # Crear mensaje encolado
            queued_message = QueuedMessage(
                id=message.get('id', str(uuid.uuid4())),
                message=message,
                priority=priority,
                enqueued_at=datetime.now()
            )
            
            async with self._lock:
                # Verificar si la cola está llena
                if self.is_full():
                    logger.warning(f"Queue is full, cannot enqueue message {queued_message.id}")
                    return False
                
                # Agregar a la cola de prioridad correspondiente
                heapq.heappush(
                    self._priority_queues[priority],
                    (queued_message.enqueued_at.timestamp(), queued_message)
                )
                
                # Notificar que hay un mensaje disponible
                await self._queue.put(None)  # Usamos None como señal
                
                self._total_enqueued += 1
                
                logger.debug(
                    f"Message {queued_message.id} enqueued with priority {priority.name}, "
                    f"queue size: {self.size()}"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error enqueuing message: {str(e)}")
            return False
    
    async def dequeue(self) -> Optional[QueuedMessage]:
        """
        Obtiene el siguiente mensaje respetando prioridades.
        """
        try:
            # Esperar señal de que hay mensajes
            await self._queue.get()
            
            async with self._lock:
                # Buscar en orden de prioridad
                for priority in sorted(MessagePriority, key=lambda p: p.value):
                    if self._priority_queues[priority]:
                        # Obtener el mensaje más antiguo de esta prioridad
                        _, message = heapq.heappop(self._priority_queues[priority])
                        self._total_processed += 1
                        
                        logger.debug(
                            f"Dequeued message {message.id} with priority {priority.name}, "
                            f"queue size: {self.size() - 1}"
                        )
                        
                        return message
                
                return None
                
        except asyncio.QueueEmpty:
            return None
        except Exception as e:
            logger.error(f"Error dequeuing message: {str(e)}")
            return None
    
    async def peek(self) -> Optional[QueuedMessage]:
        """
        Mira el siguiente mensaje sin removerlo.
        """
        async with self._lock:
            # Buscar en orden de prioridad
            for priority in sorted(MessagePriority, key=lambda p: p.value):
                if self._priority_queues[priority]:
                    # Ver el primer elemento sin removerlo
                    _, message = self._priority_queues[priority][0]
                    return message
            
            return None
    
    async def requeue(self, message: QueuedMessage) -> bool:
        """
        Re-encola un mensaje, útil para reintentos.
        """
        try:
            if not message.increment_retry():
                logger.warning(
                    f"Message {message.id} exceeded max retries ({message.max_retries}), "
                    "not requeueing"
                )
                self._total_failed += 1
                return False
            
            # Actualizar timestamp para mantener orden FIFO en reintentos
            message.enqueued_at = datetime.now()
            
            async with self._lock:
                if self.is_full():
                    logger.warning(f"Queue is full, cannot requeue message {message.id}")
                    return False
                
                # Re-encolar con menor prioridad si es un reintento
                new_priority = MessagePriority.LOW if message.retry_count > 1 else message.priority
                
                heapq.heappush(
                    self._priority_queues[new_priority],
                    (message.enqueued_at.timestamp(), message)
                )
                
                await self._queue.put(None)  # Señal
                
                logger.info(
                    f"Message {message.id} requeued with priority {new_priority.name}, "
                    f"retry count: {message.retry_count}"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error requeueing message: {str(e)}")
            return False
    
    def size(self) -> int:
        """
        Obtiene el tamaño actual de la cola.
        """
        total = 0
        for queue in self._priority_queues.values():
            total += len(queue)
        return total
    
    def is_empty(self) -> bool:
        """
        Verifica si la cola está vacía.
        """
        return self.size() == 0
    
    def is_full(self) -> bool:
        """
        Verifica si la cola está llena.
        """
        if self.max_size == 0:  # Sin límite
            return False
        return self.size() >= self.max_size
    
    async def clear(self) -> int:
        """
        Limpia todos los mensajes de la cola.
        """
        async with self._lock:
            count = self.size()
            
            # Limpiar todas las colas de prioridad
            for priority_queue in self._priority_queues.values():
                priority_queue.clear()
            
            # Limpiar la cola de señales
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            logger.info(f"Cleared {count} messages from queue")
            return count
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la cola.
        """
        async with self._lock:
            stats = {
                "current_size": self.size(),
                "max_size": self.max_size if self.max_size > 0 else "unlimited",
                "is_empty": self.is_empty(),
                "is_full": self.is_full(),
                "total_enqueued": self._total_enqueued,
                "total_processed": self._total_processed,
                "total_failed": self._total_failed,
                "messages_by_priority": {}
            }
            
            # Contar mensajes por prioridad
            for priority in MessagePriority:
                count = len(self._priority_queues[priority])
                if count > 0:
                    stats["messages_by_priority"][priority.name] = count
            
            # Calcular tiempo de espera promedio si hay mensajes
            if not self.is_empty():
                now = datetime.now()
                total_wait_time = 0
                message_count = 0
                
                for priority_queue in self._priority_queues.values():
                    for timestamp, message in priority_queue:
                        wait_time = (now - message.enqueued_at).total_seconds()
                        total_wait_time += wait_time
                        message_count += 1
                
                if message_count > 0:
                    stats["avg_wait_time_seconds"] = total_wait_time / message_count
            
            return stats
    
    async def get_messages_by_priority(self, priority: MessagePriority) -> List[QueuedMessage]:
        """
        Obtiene todos los mensajes de una prioridad específica sin removerlos.
        """
        async with self._lock:
            # Crear copia de los mensajes para no afectar la cola
            messages = []
            for timestamp, message in self._priority_queues[priority]:
                messages.append(message)
            
            # Ordenar por timestamp (más antiguos primero)
            messages.sort(key=lambda m: m.enqueued_at)
            
            return messages