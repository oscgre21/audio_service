"""
Interface para generadores de audio
"""
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional


class AudioGenerator(ABC):
    """Interface para implementaciones de generadores de audio"""
    
    @abstractmethod
    async def generate(self, text: str, language: str = "en") -> Tuple[str, str]:
        """
        Genera audio a partir de texto
        
        Args:
            text: Texto a convertir en audio
            language: Código de idioma (es, en, pt, etc.)
            
        Returns:
            Tuple[str, str]: (file_path, audio_id)
        """
        pass
    
    @abstractmethod
    async def generate_chunked(
        self, 
        chunks: List[str], 
        language: str = "en", 
        reference_audio_path: Optional[str] = "examples/voice_prompts/belinda.wav"
    ) -> Tuple[str, str]:
        """
        Genera audio a partir de múltiples chunks de texto
        
        Args:
            chunks: Lista de textos a convertir
            language: Código de idioma
            
        Returns:
            Tuple[str, str]: (file_path, audio_id) del audio concatenado
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Retorna lista de idiomas soportados"""
        pass
    
    @abstractmethod
    async def cleanup_temp_files(self) -> None:
        """Limpia archivos temporales generados"""
        pass