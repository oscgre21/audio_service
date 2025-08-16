"""
Implementación del servicio LLM
"""
from typing import Dict, Any, Optional
from src.application.interfaces.llm_service import LLMService, LLMResponse
from src.application.interfaces.prompt_service import PromptService
from .llm_provider_factory import LLMProviderFactory
from .base_driver import BaseLLMDriver
import logging

logger = logging.getLogger(__name__)


class LLMServiceImpl(LLMService):
    """Implementación del servicio LLM con soporte multi-proveedor"""
    
    def __init__(
        self, 
        provider: str,
        config: Dict[str, Any],
        prompt_service: PromptService
    ):
        self.provider = provider
        self.config = config
        self.prompt_service = prompt_service
        self.driver: BaseLLMDriver = LLMProviderFactory.create_driver(provider, config)
        
        logger.info(f"Servicio LLM inicializado con proveedor: {provider}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Genera una respuesta usando el LLM"""
        
        # Preparar mensajes
        messages = self.driver._prepare_messages(prompt, system_prompt)
        
        try:
            # Llamar al driver
            response = await self.driver.generate(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Convertir a LLMResponse
            return LLMResponse(
                content=response["content"],
                model=response["model"],
                usage=response.get("usage"),
                metadata=response.get("metadata")
            )
            
        except Exception as e:
            logger.error(f"Error generando respuesta con {self.provider}: {str(e)}")
            raise
    
    async def generate_with_template(
        self,
        template_name: str,
        variables: Dict[str, Any],
        **kwargs
    ) -> LLMResponse:
        """Genera una respuesta usando una plantilla de prompt"""
        
        try:
            # Renderizar la plantilla
            system_prompt, user_prompt = self.prompt_service.render_template(
                template_name, 
                variables
            )
            
            # Obtener la plantilla para acceder a preferencias del modelo
            template = self.prompt_service.get_template(template_name)
            
            # Mezclar kwargs con preferencias del modelo si existen
            if template.model_preferences:
                generation_kwargs = {**template.model_preferences, **kwargs}
            else:
                generation_kwargs = kwargs
            
            # Generar respuesta
            return await self.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                **generation_kwargs
            )
            
        except Exception as e:
            logger.error(
                f"Error generando con plantilla '{template_name}': {str(e)}"
            )
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """Genera una respuesta en streaming"""
        
        # Preparar mensajes
        messages = self.driver._prepare_messages(prompt, system_prompt)
        
        try:
            # Stream desde el driver
            async for chunk in self.driver.generate_stream(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error en streaming con {self.provider}: {str(e)}")
            raise