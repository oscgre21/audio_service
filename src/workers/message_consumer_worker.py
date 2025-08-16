"""
Worker mejorado para consumir mensajes con cola de procesamiento y estrategias
"""
import asyncio
import logging
import signal
from typing import Optional, Dict, Any
from datetime import datetime

from ..application.interfaces import MessageQueue, ProcessingQueue, MessagePriority
from ..application.orchestrator import StrategyOrchestrator
from ..domain.entities import Message

logger = logging.getLogger(__name__)


class MessageConsumerWorker:
    """
    Worker mejorado que consume mensajes de RabbitMQ y los procesa
    usando una cola interna y el patrón Strategy.
    """
    
    def __init__(
        self,
        message_queue: MessageQueue,
        processing_queue: ProcessingQueue,
        orchestrator: StrategyOrchestrator,
        concurrent_processors: int = 3
    ):
        """
        Inicializa el worker con las dependencias necesarias.
        
        Args:
            message_queue: Cola de mensajes externa (RabbitMQ)
            processing_queue: Cola de procesamiento interna
            orchestrator: Orquestador de estrategias
            concurrent_processors: Número de procesadores concurrentes
        """
        self.message_queue = message_queue
        self.processing_queue = processing_queue
        self.orchestrator = orchestrator
        self.concurrent_processors = concurrent_processors
        
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
        self._processor_tasks: list[asyncio.Task] = []
        self._stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "start_time": None
        }
    
    async def start(self) -> None:
        """Inicia el worker y todos sus componentes"""
        logger.info("Starting enhanced message consumer worker...")
        logger.info(f"Concurrent processors: {self.concurrent_processors}")
        
        self._stats["start_time"] = datetime.now()
        
        # Conectar a la cola de mensajes
        await self.message_queue.connect()
        
        # Inicializar estrategias
        await self.orchestrator.initialize_all()
        
        # Configurar manejadores de señales
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        self._running = True
        
        # Iniciar consumidor de RabbitMQ
        self._consumer_task = asyncio.create_task(
            self._consume_messages(),
            name="rabbitmq_consumer"
        )
        
        # Iniciar procesadores de cola interna
        for i in range(self.concurrent_processors):
            processor_task = asyncio.create_task(
                self._process_queue(),
                name=f"queue_processor_{i}"
            )
            self._processor_tasks.append(processor_task)
        
        logger.info("Worker started successfully")
        
        # Iniciar tarea de monitoreo
        monitor_task = asyncio.create_task(self._monitor_stats())
        
        try:
            # Esperar hasta que se detenga el worker
            await asyncio.gather(
                self._consumer_task,
                *self._processor_tasks,
                monitor_task
            )
        except asyncio.CancelledError:
            logger.info("Worker tasks cancelled")
        except Exception as e:
            logger.error(f"Worker error: {str(e)}", exc_info=True)
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Detiene el worker gracefully"""
        logger.info("Stopping message consumer worker...")
        self._running = False
        
        # Cancelar tareas de consumo
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        
        # Esperar a que se procesen los mensajes pendientes
        queue_size = self.processing_queue.size()
        if queue_size > 0:
            logger.info(f"Waiting for {queue_size} messages in queue to be processed...")
            
            # Dar tiempo para procesar mensajes pendientes
            timeout = 30  # segundos
            start_time = asyncio.get_event_loop().time()
            
            while self.processing_queue.size() > 0 and \
                  asyncio.get_event_loop().time() - start_time < timeout:
                await asyncio.sleep(0.5)
            
            final_size = self.processing_queue.size()
            if final_size > 0:
                logger.warning(f"Timeout: {final_size} messages still in queue")
        
        # Cancelar procesadores
        for task in self._processor_tasks:
            if not task.done():
                task.cancel()
        
        # Esperar a que terminen
        if self._processor_tasks:
            await asyncio.gather(*self._processor_tasks, return_exceptions=True)
        
        # Limpiar estrategias
        await self.orchestrator.cleanup_all()
        
        # Desconectar de RabbitMQ
        await self.message_queue.disconnect()
        
        # Mostrar estadísticas finales
        await self._print_final_stats()
        
        logger.info("Worker stopped")
    
    def _handle_signal(self, signum, frame):
        """Maneja señales del sistema"""
        logger.info(f"Received signal {signum}")
        self._running = False
    
    async def _consume_messages(self) -> None:
        """Consume mensajes de RabbitMQ y los encola para procesamiento"""
        logger.info("Starting RabbitMQ consumer...")
        
        try:
            await self.message_queue.consume(self._on_message)
        except Exception as e:
            logger.error(f"Consumer error: {str(e)}", exc_info=True)
            self._running = False
    
    async def _on_message(self, message: Message) -> None:
        """
        Callback para mensajes recibidos de RabbitMQ.
        Encola el mensaje sin bloquear RabbitMQ.
        """
        if not self._running:
            return
        
        self._stats["messages_received"] += 1
        
        # Determinar prioridad basada en el tipo de evento o contenido
        priority = self._determine_priority(message)
        
        # Convertir Message entity a dict para la cola
        message_dict = {
            "id": message.id,
            "type": message.event_type,
            "data": message.data,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "retryCount": message.retry_count
        }
        
        # Encolar mensaje
        success = await self.processing_queue.enqueue(message_dict, priority)
        
        if success:
            logger.debug(
                f"Message {message.id} enqueued with priority {priority.name}, "
                f"queue size: {self.processing_queue.size()}"
            )
        else:
            logger.error(f"Failed to enqueue message {message.id} - queue might be full")
            self._stats["messages_failed"] += 1
    
    def _determine_priority(self, message: Message) -> MessagePriority:
        """
        Determina la prioridad de un mensaje basándose en su contenido.
        """
        # Mensajes con reintentos tienen menor prioridad
        if message.retry_count > 0:
            return MessagePriority.LOW
        
        # Mensajes críticos (ejemplo: usuarios premium)
        data = message.data or {}
        speech_dto = data.get("speechDto", {})
        
        # Ejemplo: dar prioridad alta a ciertos usuarios o tipos
        user_id = speech_dto.get("user_uuid", "")
        if user_id and "premium" in user_id.lower():
            return MessagePriority.HIGH
        
        # Por defecto, prioridad normal
        return MessagePriority.NORMAL
    
    async def _process_queue(self) -> None:
        """
        Procesa mensajes de la cola interna en orden FIFO por prioridad.
        Este método es ejecutado por múltiples tareas concurrentes.
        """
        processor_name = asyncio.current_task().get_name()
        logger.info(f"{processor_name} started")
        
        while self._running:
            try:
                # Obtener siguiente mensaje
                queued_message = await self.processing_queue.dequeue()
                
                if not queued_message:
                    # No hay mensajes, esperar un poco
                    await asyncio.sleep(0.1)
                    continue
                
                # Procesar mensaje
                logger.info(
                    f"{processor_name} processing message {queued_message.id} "
                    f"(priority: {queued_message.priority.name}, "
                    f"retry: {queued_message.retry_count})"
                )
                
                start_time = datetime.now()
                
                try:
                    # Ejecutar estrategias a través del orquestador
                    result = await self.orchestrator.process(queued_message.message)
                    
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    if result["overall_success"]:
                        self._stats["messages_processed"] += 1
                        logger.info(
                            f"Message {queued_message.id} processed successfully "
                            f"in {processing_time:.2f}s"
                        )
                    else:
                        # Verificar si debe reintentarse
                        if await self._should_retry(queued_message, result):
                            await self.processing_queue.requeue(queued_message)
                            logger.warning(
                                f"Message {queued_message.id} failed, requeued for retry"
                            )
                        else:
                            self._stats["messages_failed"] += 1
                            logger.error(
                                f"Message {queued_message.id} failed permanently"
                            )
                    
                except Exception as e:
                    logger.error(
                        f"Error processing message {queued_message.id}: {str(e)}",
                        exc_info=True
                    )
                    
                    # Reintentar si es posible
                    if queued_message.retry_count < queued_message.max_retries:
                        await self.processing_queue.requeue(queued_message)
                    else:
                        self._stats["messages_failed"] += 1
                
            except Exception as e:
                logger.error(f"{processor_name} error: {str(e)}", exc_info=True)
                await asyncio.sleep(1)  # Evitar busy loop en caso de error
        
        logger.info(f"{processor_name} stopped")
    
    async def _should_retry(self, message: Any, result: Dict[str, Any]) -> bool:
        """
        Determina si un mensaje debe reintentarse basándose en el resultado.
        """
        # No reintentar si ya excedió los límites
        if message.retry_count >= message.max_retries:
            return False
        
        # Analizar los resultados de las estrategias
        for strategy_result in result.get("results", []):
            error = strategy_result.get("error", "")
            
            # No reintentar errores de validación
            if "validation" in error.lower() or "invalid" in error.lower():
                return False
            
            # Reintentar errores temporales
            if any(temp_error in error.lower() for temp_error in 
                   ["timeout", "connection", "temporary", "unavailable"]):
                return True
        
        # Por defecto, no reintentar
        return False
    
    async def _monitor_stats(self) -> None:
        """Monitorea y reporta estadísticas periódicamente"""
        while self._running:
            await asyncio.sleep(30)  # Reportar cada 30 segundos
            
            if self._running:
                await self._print_stats()
    
    async def _print_stats(self) -> None:
        """Imprime estadísticas actuales"""
        queue_stats = await self.processing_queue.get_stats()
        uptime = (datetime.now() - self._stats["start_time"]).total_seconds()
        
        # logger.info("=== Worker Statistics ===")
        # logger.info(f"Uptime: {uptime:.0f}s")
        # logger.info(f"Messages received: {self._stats['messages_received']}")
        # logger.info(f"Messages processed: {self._stats['messages_processed']}")
        # logger.info(f"Messages failed: {self._stats['messages_failed']}")
        # logger.info(f"Queue size: {queue_stats['current_size']}")
        # logger.info(f"Queue stats: {queue_stats}")
        # logger.info("========================")
    
    async def _print_final_stats(self) -> None:
        """Imprime estadísticas finales al detener"""
        # logger.info("=== Final Worker Statistics ===")
        if self._stats["start_time"]:
            uptime = (datetime.now() - self._stats["start_time"]).total_seconds()
        #     logger.info(f"Total uptime: {uptime:.0f}s")
        # logger.info(f"Total messages received: {self._stats['messages_received']}")
        # logger.info(f"Total messages processed: {self._stats['messages_processed']}")
        # logger.info(f"Total messages failed: {self._stats['messages_failed']}")
        
        success_rate = 0
        if self._stats['messages_received'] > 0:
            success_rate = (self._stats['messages_processed'] / 
                          self._stats['messages_received']) * 100
        # logger.info(f"Success rate: {success_rate:.1f}%")
        # logger.info("===============================")