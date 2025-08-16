"""
Driver para OpenAI
"""
import httpx
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from .base_driver import BaseLLMDriver
import logging

logger = logging.getLogger(__name__)


class OpenAIDriver(BaseLLMDriver):
    """Driver para interactuar con OpenAI API"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.openai.com/v1')
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'gpt-4-turbo-preview')
        
        if not self.api_key:
            raise ValueError("Se requiere OPENAI_API_KEY para usar OpenAI")
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Genera una respuesta usando OpenAI API"""
        
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        # Agregar parámetros adicionales de OpenAI
        for key, value in kwargs.items():
            if key in ["top_p", "frequency_penalty", "presence_penalty", "seed", "stop"]:
                payload[key] = value
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": data["model"],
                    "usage": {
                        "prompt_tokens": data["usage"]["prompt_tokens"],
                        "completion_tokens": data["usage"]["completion_tokens"],
                        "total_tokens": data["usage"]["total_tokens"]
                    },
                    "metadata": {
                        "finish_reason": data["choices"][0]["finish_reason"],
                        "id": data["id"]
                    }
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Error al comunicarse con OpenAI API: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado en OpenAI driver: {str(e)}")
            raise
            
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Genera una respuesta en streaming usando OpenAI API"""
        
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        # Agregar parámetros adicionales
        for key, value in kwargs.items():
            if key in ["top_p", "frequency_penalty", "presence_penalty", "seed", "stop"]:
                payload[key] = value
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                                
                            try:
                                data = json.loads(data_str)
                                
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"No se pudo decodificar línea: {line}")
                                continue
                                
        except httpx.HTTPError as e:
            logger.error(f"Error al comunicarse con OpenAI API (streaming): {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado en OpenAI streaming: {str(e)}")
            raise