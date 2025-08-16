"""
Interface for transcription services
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class TranscriptionService(ABC):
    """Interface for audio transcription services with word-level alignment"""
    
    @abstractmethod
    async def transcribe_with_alignment(
        self,
        audio_path: str,
        language: Optional[str] = None,
        original_text: Optional[str] = None
    ) -> str:
        """
        Transcribe audio and return aligned SRT with word-level timestamps
        
        Args:
            audio_path: Path to the audio file
            language: Language code (e.g., 'en', 'es'). Auto-detect if None
            original_text: Original text for forced alignment (optional)
            
        Returns:
            SRT formatted text with precise word-level timestamps
        """
        pass
    
    @abstractmethod
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Basic transcription without alignment
        
        Args:
            audio_path: Path to the audio file
            language: Language code. Auto-detect if None
            
        Returns:
            Dictionary with transcription results including text and segments
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes
        
        Returns:
            List of language codes
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the transcription service is available and properly configured
        
        Returns:
            True if service is ready to use
        """
        pass