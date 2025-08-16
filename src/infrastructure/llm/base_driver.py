"""
Driver base para proveedores de LLM
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class BaseLLMDriver(ABC):
    """Clase base para drivers de LLM"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('base_url')
        self.api_key = config.get('api_key')
        self.model = config.get('model')
        self.timeout = config.get('timeout', 30)
        
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Genera una respuesta del LLM
        
        Args:
            messages: Lista de mensajes en formato [{"role": "system/user/assistant", "content": "..."}]
            temperature: Control de creatividad
            max_tokens: Máximo de tokens a generar
            **kwargs: Parámetros adicionales específicos del proveedor
            
        Returns:
            Diccionario con la respuesta del proveedor
        """
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Genera una respuesta en streaming
        
        Args:
            messages: Lista de mensajes
            temperature: Control de creatividad
            max_tokens: Máximo de tokens a generar
            **kwargs: Parámetros adicionales
            
        Yields:
            Chunks de texto generados
        """
        pass
    
    def _prepare_messages(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Prepara los mensajes en el formato estándar
        
        Args:
            prompt: Prompt del usuario
            system_prompt: Prompt del sistema (opcional)
            
        Returns:
            Lista de mensajes formateados
        """
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
            
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return messages