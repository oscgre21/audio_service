"""
Entidad Audio del dominio
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Audio:
    """Entidad que representa un archivo de audio generado"""
    id: str
    speech_id: str
    file_path: str
    file_size: int
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    was_chunked: bool = False
    chunks_count: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    upload_status: str = "pending"  # pending, uploaded, failed
    upload_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def mark_as_uploaded(self, url: str) -> None:
        """Marca el audio como subido exitosamente"""
        self.upload_status = "uploaded"
        self.upload_url = url
    
    def mark_upload_failed(self) -> None:
        """Marca el upload como fallido"""
        self.upload_status = "failed"
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Agrega metadata al audio"""
        self.metadata[key] = value
    
    @property
    def is_uploaded(self) -> bool:
        """Verifica si el audio fue subido exitosamente"""
        return self.upload_status == "uploaded"