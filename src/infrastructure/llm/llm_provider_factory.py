"""
Factory para crear instancias de drivers LLM
"""
from typing import Dict, Any
from enum import Enum
from .base_driver import BaseLLMDriver
from .ollama_driver import OllamaDriver
from .claude_driver import ClaudeDriver
from .openai_driver import OpenAIDriver
import logging

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Proveedores de LLM soportados"""
    OLLAMA = "ollama"
    CLAUDE = "claude"
    OPENAI = "openai"


class LLMProviderFactory:
    """Factory para crear drivers de LLM según el proveedor"""
    
    _drivers = {
        LLMProvider.OLLAMA: OllamaDriver,
        LLMProvider.CLAUDE: ClaudeDriver,
        LLMProvider.OPENAI: OpenAIDriver
    }
    
    @classmethod
    def create_driver(cls, provider: str, config: Dict[str, Any]) -> BaseLLMDriver:
        """
        Crea una instancia del driver LLM correspondiente
        
        Args:
            provider: Nombre del proveedor (ollama, claude, openai)
            config: Configuración específica del proveedor
            
        Returns:
            Instancia del driver LLM
            
        Raises:
            ValueError: Si el proveedor no es soportado
        """
        try:
            provider_enum = LLMProvider(provider.lower())
        except ValueError:
            supported = ", ".join([p.value for p in LLMProvider])
            raise ValueError(
                f"Proveedor '{provider}' no soportado. "
                f"Proveedores disponibles: {supported}"
            )
        
        driver_class = cls._drivers.get(provider_enum)
        if not driver_class:
            raise ValueError(f"No se encontró driver para el proveedor: {provider}")
        
        logger.info(f"Creando driver LLM para proveedor: {provider}")
        return driver_class(config)
    
    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Retorna la lista de proveedores soportados"""
        return [provider.value for provider in LLMProvider]