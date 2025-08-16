"""
Interface for voice reference service
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict


class VoiceReferenceService(ABC):
    """Service to manage voice references for audio generation"""
    
    @abstractmethod
    def get_voice_path(self, character: str) -> Optional[str]:
        """
        Get the audio reference path for a character
        
        Args:
            character: Character name (e.g., "belinda", "narrator")
            
        Returns:
            Path to the audio reference file, or None if not found
        """
        pass
    
    @abstractmethod
    def get_default_character(self) -> str:
        """
        Get the default character name
        
        Returns:
            Default character name
        """
        pass
    
    @abstractmethod
    def list_available_characters(self) -> List[str]:
        """
        List all available character names
        
        Returns:
            List of available character names
        """
        pass
    
    @abstractmethod
    def get_character_info(self, character: str) -> Optional[Dict[str, str]]:
        """
        Get detailed information about a character
        
        Args:
            character: Character name
            
        Returns:
            Dictionary with character information or None if not found
        """
        pass