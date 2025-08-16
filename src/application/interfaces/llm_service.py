"""
Interfaz para el servicio de LLM (Language Model)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class LLMResponse:
    """Respuesta del servicio LLM"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMService(ABC):
    """Interfaz para servicios de Language Model"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Genera una respuesta usando el LLM
        
        Args:
            prompt: El prompt del usuario
            system_prompt: El prompt del sistema (opcional)
            temperature: Control de creatividad (0.0 - 1.0)
            max_tokens: Máximo de tokens a generar
            **kwargs: Parámetros adicionales específicos del proveedor
            
        Returns:
            LLMResponse con el contenido generado
        """
        pass
    
    @abstractmethod
    async def generate_with_template(
        self,
        template_name: str,
        variables: Dict[str, Any],
        **kwargs
    ) -> LLMResponse:
        """
        Genera una respuesta usando una plantilla de prompt
        
        Args:
            template_name: Nombre de la plantilla a usar
            variables: Variables para renderizar la plantilla
            **kwargs: Parámetros adicionales para la generación
            
        Returns:
            LLMResponse con el contenido generado
        """
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Genera una respuesta en streaming
        
        Args:
            prompt: El prompt del usuario
            system_prompt: El prompt del sistema (opcional)
            temperature: Control de creatividad (0.0 - 1.0)
            max_tokens: Máximo de tokens a generar
            **kwargs: Parámetros adicionales específicos del proveedor
            
        Yields:
            Chunks de texto generados
        """
        pass