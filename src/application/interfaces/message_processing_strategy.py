"""
Interfaz para estrategias de procesamiento de mensajes
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class StrategyResult:
    """Resultado de ejecutar una estrategia de procesamiento"""
    success: bool
    data: Dict[str, Any]
    next_strategy: Optional[str] = None  # Permite control de flujo dinámico
    should_continue: bool = True         # Permite detener la cadena de procesamiento
    error: Optional[str] = None
    processing_time: Optional[float] = None


class MessageProcessingStrategy(ABC):
    """
    Interfaz base para todas las estrategias de procesamiento de mensajes.
    
    Implementa el patrón Strategy para permitir diferentes algoritmos
    de procesamiento que pueden ser intercambiados dinámicamente.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Nombre único de la estrategia.
        Usado para logging y control de flujo.
        """
        pass
    
    @property
    @abstractmethod
    def order(self) -> int:
        """
        Orden de ejecución de la estrategia.
        Menor número = mayor prioridad (ejecuta primero).
        Ejemplo: Validación=10, Procesamiento=100, PostProcesamiento=200
        """
        pass
    
    @abstractmethod
    async def can_handle(self, message: Dict[str, Any]) -> bool:
        """
        Determina si esta estrategia puede procesar el mensaje dado.
        
        Args:
            message: Mensaje a evaluar
            
        Returns:
            True si la estrategia puede procesar el mensaje
        """
        pass
    
    @abstractmethod
    async def execute(self, message: Dict[str, Any], context: Dict[str, Any]) -> StrategyResult:
        """
        Ejecuta la lógica de procesamiento de la estrategia.
        
        Args:
            message: Mensaje a procesar
            context: Contexto compartido entre estrategias para pasar datos
            
        Returns:
            StrategyResult con el resultado del procesamiento
        """
        pass
    
    async def initialize(self) -> None:
        """
        Hook opcional para inicialización asíncrona.
        Útil para cargar recursos, conectar a servicios, etc.
        """
        pass
    
    async def cleanup(self) -> None:
        """
        Hook opcional para limpieza de recursos.
        Se llama cuando la estrategia ya no se necesita.
        """
        pass
    
    def __str__(self) -> str:
        """Representación string de la estrategia"""
        return f"{self.__class__.__name__}(name={self.name}, order={self.order})"