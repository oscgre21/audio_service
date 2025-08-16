"""
Orquestador para coordinar la ejecución de estrategias de procesamiento
"""
from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

from ..interfaces import MessageProcessingStrategy, StrategyResult

logger = logging.getLogger(__name__)


class StrategyOrchestrator:
    """
    Coordina la ejecución de múltiples estrategias de procesamiento.
    
    Las estrategias se ejecutan en orden según su prioridad (order),
    compartiendo un contexto común para pasar datos entre ellas.
    """
    
    def __init__(self, strategies: List[MessageProcessingStrategy]):
        """
        Inicializa el orquestador con las estrategias disponibles.
        
        Args:
            strategies: Lista de estrategias a coordinar
        """
        # Ordenar estrategias por prioridad (menor order = mayor prioridad)
        self.strategies = sorted(strategies, key=lambda s: s.order)
        self._strategy_map = {s.name: s for s in strategies}
        
        logger.info(f"StrategyOrchestrator initialized with {len(strategies)} strategies:")
        for strategy in self.strategies:
            logger.info(f"  - {strategy.name} (order: {strategy.order})")
    
    async def initialize_all(self) -> None:
        """Inicializa todas las estrategias"""
        logger.info("Initializing all strategies...")
        
        init_tasks = []
        for strategy in self.strategies:
            init_tasks.append(strategy.initialize())
        
        await asyncio.gather(*init_tasks)
        logger.info("All strategies initialized")
    
    async def cleanup_all(self) -> None:
        """Limpia recursos de todas las estrategias"""
        logger.info("Cleaning up all strategies...")
        
        cleanup_tasks = []
        for strategy in self.strategies:
            cleanup_tasks.append(strategy.cleanup())
        
        await asyncio.gather(*cleanup_tasks)
        logger.info("All strategies cleaned up")
    
    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un mensaje a través de la cadena de estrategias.
        
        Args:
            message: Mensaje a procesar
            
        Returns:
            Dict con los resultados del procesamiento
        """
        start_time = datetime.now()
        context = {}  # Contexto compartido entre estrategias
        results = []
        
        message_id = message.get('id', 'unknown')
        logger.info(f"Starting orchestrated processing for message: {message_id}")
        
        current_strategy_index = 0
        
        while current_strategy_index < len(self.strategies):
            strategy = self.strategies[current_strategy_index]
            
            try:
                # Verificar si la estrategia puede manejar el mensaje
                if not await strategy.can_handle(message):
                    logger.debug(f"Strategy {strategy.name} cannot handle message, skipping")
                    current_strategy_index += 1
                    continue
                
                logger.info(f"Executing strategy: {strategy.name}")
                strategy_start = datetime.now()
                
                # Ejecutar la estrategia
                result = await strategy.execute(message, context)
                
                # Calcular tiempo si no está en el resultado
                if result.processing_time is None:
                    result.processing_time = (datetime.now() - strategy_start).total_seconds()
                
                # Guardar resultado
                results.append({
                    "strategy": strategy.name,
                    "order": strategy.order,
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "processing_time": result.processing_time
                })
                
                logger.info(
                    f"Strategy {strategy.name} completed: "
                    f"success={result.success}, time={result.processing_time:.2f}s"
                )
                
                # Verificar si debe continuar
                if not result.should_continue:
                    logger.info(f"Strategy {strategy.name} requested to stop processing chain")
                    break
                
                # Verificar si debe saltar a otra estrategia
                if result.next_strategy:
                    next_strategy = self._strategy_map.get(result.next_strategy)
                    if next_strategy:
                        # Encontrar índice de la siguiente estrategia
                        next_index = next(
                            (i for i, s in enumerate(self.strategies) if s.name == result.next_strategy),
                            None
                        )
                        if next_index is not None:
                            logger.info(f"Jumping to strategy: {result.next_strategy}")
                            current_strategy_index = next_index
                            continue
                        else:
                            logger.warning(f"Strategy {result.next_strategy} not found in chain")
                    else:
                        logger.warning(f"Unknown strategy requested: {result.next_strategy}")
                
            except Exception as e:
                logger.error(f"Error in strategy {strategy.name}: {str(e)}", exc_info=True)
                
                # Guardar error en resultados
                results.append({
                    "strategy": strategy.name,
                    "order": strategy.order,
                    "success": False,
                    "data": {},
                    "error": str(e),
                    "processing_time": (datetime.now() - strategy_start).total_seconds()
                })
                
                # Por defecto, continuar con la siguiente estrategia en caso de error
                # (a menos que sea una estrategia crítica)
            
            current_strategy_index += 1
        
        # Calcular tiempo total
        total_time = (datetime.now() - start_time).total_seconds()
        
        # Determinar éxito general (al menos una estrategia exitosa)
        overall_success = any(r["success"] for r in results)
        
        # Preparar respuesta final
        orchestration_result = {
            "message_id": message_id,
            "timestamp": datetime.now().isoformat(),
            "total_processing_time": total_time,
            "overall_success": overall_success,
            "strategies_executed": len(results),
            "results": results,
            "context": context  # Incluir contexto final para debugging
        }
        
        logger.info(
            f"Orchestration completed for message {message_id}: "
            f"success={overall_success}, "
            f"strategies={len(results)}, "
            f"time={total_time:.2f}s"
        )
        
        return orchestration_result
    
    def get_strategy(self, name: str) -> Optional[MessageProcessingStrategy]:
        """
        Obtiene una estrategia por nombre.
        
        Args:
            name: Nombre de la estrategia
            
        Returns:
            La estrategia si existe, None si no
        """
        return self._strategy_map.get(name)
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """
        Lista todas las estrategias registradas.
        
        Returns:
            Lista con información de cada estrategia
        """
        return [
            {
                "name": strategy.name,
                "order": strategy.order,
                "class": strategy.__class__.__name__
            }
            for strategy in self.strategies
        ]