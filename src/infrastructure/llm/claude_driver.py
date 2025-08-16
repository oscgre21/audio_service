"""
Driver para Claude (Anthropic)
"""
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator
from .base_driver import BaseLLMDriver
import logging

logger = logging.getLogger(__name__)


class ClaudeDriver(BaseLLMDriver):
    """Driver para interactuar con Claude API de Anthropic"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.anthropic.com/v1')
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'claude-3-opus-20240229')
        self.anthropic_version = '2023-06-01'
        
        if not self.api_key:
            raise ValueError("Se requiere CLAUDE_API_KEY para usar Claude")
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Genera una respuesta usando Claude API"""
        
        url = f"{self.base_url}/messages"
        
        # Separar system prompt de los mensajes
        system_prompt = None
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)
        
        payload = {
            "model": self.model,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 1024
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            "content-type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                return {
                    "content": data["content"][0]["text"],
                    "model": data["model"],
                    "usage": {
                        "prompt_tokens": data["usage"]["input_tokens"],
                        "completion_tokens": data["usage"]["output_tokens"],
                        "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
                    },
                    "metadata": {
                        "stop_reason": data.get("stop_reason"),
                        "id": data.get("id")
                    }
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Error al comunicarse con Claude API: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado en Claude driver: {str(e)}")
            raise
            
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Genera una respuesta en streaming usando Claude API"""
        
        url = f"{self.base_url}/messages"
        
        # Separar system prompt
        system_prompt = None
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)
        
        payload = {
            "model": self.model,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 1024,
            "stream": True
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            "content-type": "application/json"
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
                                import json
                                data = json.loads(data_str)
                                
                                if data["type"] == "content_block_delta":
                                    yield data["delta"]["text"]
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"No se pudo decodificar línea: {line}")
                                continue
                                
        except httpx.HTTPError as e:
            logger.error(f"Error al comunicarse con Claude API (streaming): {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado en Claude streaming: {str(e)}")
            raise