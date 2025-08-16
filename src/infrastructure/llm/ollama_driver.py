"""
Driver para Ollama
"""
import httpx
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from .base_driver import BaseLLMDriver
import logging

logger = logging.getLogger(__name__)


class OllamaDriver(BaseLLMDriver):
    """Driver para interactuar con Ollama API"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://llm.oscgre.com')
        self.model = config.get('model', 'llama3.1')
        
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Genera una respuesta usando Ollama"""
        
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
            
        # Agregar opciones adicionales de Ollama si se proporcionan
        for key, value in kwargs.items():
            if key in ["top_k", "top_p", "repeat_penalty", "seed"]:
                payload["options"][key] = value
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                return {
                    "content": data["message"]["content"],
                    "model": data["model"],
                    "usage": {
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                        "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                    },
                    "metadata": {
                        "eval_duration": data.get("eval_duration"),
                        "total_duration": data.get("total_duration")
                    }
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Error al comunicarse con Ollama: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado en Ollama driver: {str(e)}")
            raise
            
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Genera una respuesta en streaming usando Ollama"""
        
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
            
        # Agregar opciones adicionales
        for key, value in kwargs.items():
            if key in ["top_k", "top_p", "repeat_penalty", "seed"]:
                payload["options"][key] = value
        
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    yield data["message"]["content"]
                            except json.JSONDecodeError:
                                logger.warning(f"No se pudo decodificar línea: {line}")
                                continue
                                
        except httpx.HTTPError as e:
            logger.error(f"Error al comunicarse con Ollama (streaming): {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado en Ollama streaming: {str(e)}")
            raise