"""
Local implementation of voice reference service
"""
import logging
from typing import Optional, List, Dict
from pathlib import Path

from ...application.interfaces import VoiceReferenceService

logger = logging.getLogger(__name__)


class LocalVoiceReferenceService(VoiceReferenceService):
    """Local implementation that manages voice references from filesystem"""
    
    def __init__(self, default_character: str = "belinda"):
        """
        Initialize the voice reference service
        
        Args:
            default_character: Default character to use when none specified
        """
        self.default_character = default_character
        
        # Define character voice mappings
        self._character_voices: Dict[str, Dict[str, str]] = {
            "belinda": {
                "path": "examples/voice_prompts/belinda.wav",
                "description": "Professional female voice with clear and neutral accent",
                "language": "multi"
            },
            "shrek_donkey": {
                "path": "examples/voice_prompts/shrek_donkey_es.wav",
                "description": "Energetic male salesperson voice",
                "language": "es"
            },
            "narrator": {
                "path": "examples/voice_prompts/narrator.wav",
                "description": "Deep, storytelling voice perfect for audiobooks",
                "language": "en"
            },
            "child": {
                "path": "examples/voice_prompts/child.wav",
                "description": "Young, enthusiastic voice",
                "language": "en"
            },
            "elder": {
                "path": "examples/voice_prompts/elder.wav",
                "description": "Wise, aged voice with warmth",
                "language": "en"
            }
        }
        
        logger.info(f"Voice reference service initialized with {len(self._character_voices)} characters")
        logger.info(f"Default character: {self.default_character}")
    
    def get_voice_path(self, character: str) -> Optional[str]:
        """Get the audio reference path for a character"""
        if not character:
            character = self.default_character
            
        character_lower = character.lower()
        
        if character_lower in self._character_voices:
            path = self._character_voices[character_lower]["path"]
            # Verify the file exists
            if Path(path).exists():
                logger.debug(f"Found voice path for character '{character}': {path}")
                return path
            else:
                logger.warning(f"Voice file not found for character '{character}': {path}")
                # Fall back to default if file doesn't exist
                if character_lower != self.default_character.lower():
                    logger.info(f"Falling back to default character: {self.default_character}")
                    return self.get_voice_path(self.default_character)
        
        logger.warning(f"Unknown character: {character}")
        # Try to use default character
        if character_lower != self.default_character.lower():
            logger.info(f"Using default character: {self.default_character}")
            return self.get_voice_path(self.default_character)
        
        return None
    
    def get_default_character(self) -> str:
        """Get the default character name"""
        return self.default_character
    
    def list_available_characters(self) -> List[str]:
        """List all available character names"""
        return list(self._character_voices.keys())
    
    def get_character_info(self, character: str) -> Optional[Dict[str, str]]:
        """Get detailed information about a character"""
        character_lower = character.lower()
        if character_lower in self._character_voices:
            info = self._character_voices[character_lower].copy()
            info["name"] = character
            return info
        return None
    
    def add_character(self, name: str, path: str, description: str = "", language: str = "en") -> bool:
        """
        Add a new character voice (for future extensibility)
        
        Args:
            name: Character name
            path: Path to audio file
            description: Character voice description
            language: Language code
            
        Returns:
            True if added successfully
        """
        if not Path(path).exists():
            logger.error(f"Cannot add character '{name}': audio file not found at {path}")
            return False
            
        self._character_voices[name.lower()] = {
            "path": path,
            "description": description,
            "language": language
        }
        logger.info(f"Added new character: {name}")
        return True