"""
Value Object para AudioId
"""
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioId:
    """Value object que representa un ID único de audio"""
    value: str
    
    def __post_init__(self):
        """Valida el formato del ID"""
        if not self.value:
            raise ValueError("AudioId cannot be empty")
        
        try:
            # Validar que sea un UUID válido
            uuid.UUID(self.value)
        except ValueError:
            raise ValueError(f"Invalid AudioId format: {self.value}")
    
    @classmethod
    def generate(cls) -> "AudioId":
        """Genera un nuevo AudioId"""
        return cls(str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value