"""
Interface para subida de archivos de audio
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class AudioUploader(ABC):
    """Interface para implementaciones de upload de audio"""
    
    @abstractmethod
    async def upload(
        self, 
        file_path: str, 
        speech_id: str, 
        audio_type: str = "main",
        metadata: Optional[Dict[str, Any]] = None,
        original_text: Optional[str] = None,
        language: Optional[str] = None,
        original_text_srt: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Sube un archivo de audio
        
        Args:
            file_path: Ruta del archivo a subir
            speech_id: ID del speech asociado
            audio_type: Tipo de audio (main, word, question, etc.)
            metadata: Metadata adicional opcional
            original_text: Texto original opcional
            language: Código de idioma (es, en, etc.)
            original_text_srt: Texto en formato SRT con timestamps
            
        Returns:
            Optional[Dict[str, Any]]: Respuesta del servidor o None si falla
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Verifica si el upload está habilitado"""
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """Valida que se puede conectar al servidor"""
        pass