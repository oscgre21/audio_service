"""
Entidad Message del dominio
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class SpeechMessage:
    """Representa un mensaje de RabbitMQ para procesar speech"""
    id: str
    type: str
    timestamp: datetime
    retry_count: int
    data: Dict[str, Any]
    
    @property
    def speech_id(self) -> Optional[str]:
        """Obtiene el ID del speech del mensaje"""
        return self.data.get("speechId")
    
    @property
    def user_id(self) -> Optional[str]:
        """Obtiene el ID del usuario del mensaje"""
        return self.data.get("userId")
    
    @property
    def speech_dto(self) -> Dict[str, Any]:
        """Obtiene el DTO del speech"""
        return self.data.get("speechDto", {})
    
    def is_valid(self) -> bool:
        """Valida que el mensaje tenga la estructura correcta"""
        if self.type != "speech.created":
            return False
            
        if not self.speech_id:
            return False
            
        if not self.speech_dto:
            return False
            
        return True