"""
Entidad Speech del dominio
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Speech:
    """Entidad que representa un speech en el sistema"""
    id: str
    user_id: str
    name: str
    language: str
    original_text: str
    created_at: datetime
    project_id: Optional[str] = None
    status: str = "pending"
    speed: float = 1.0
    
    def validate(self) -> bool:
        """Valida que el speech tenga datos correctos"""
        if not self.id or not self.original_text:
            return False
        
        if not self.language:
            return False
            
        if self.speed <= 0:
            return False
            
        return True
    
    @property
    def text_length(self) -> int:
        """Retorna la longitud del texto"""
        return len(self.original_text)
    
    def should_chunk(self, max_length: int) -> bool:
        """Determina si el texto debe ser dividido en chunks"""
        return self.text_length > max_length