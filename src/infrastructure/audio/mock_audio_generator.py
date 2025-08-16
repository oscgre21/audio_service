"""
Mock implementation of AudioGenerator for testing
"""
import os
import uuid
import asyncio
from typing import Tuple, List
import logging

from ...application.interfaces import AudioGenerator, TextChunker

logger = logging.getLogger(__name__)


class MockAudioGenerator(AudioGenerator):
    """Mock implementation for testing without actual audio generation"""
    
    def __init__(
        self, 
        model_path: str,
        tokenizer_path: str,
        output_dir: str,
        device: str = None,
        torch_seed: int = 42,
        text_chunker: TextChunker = None,
        generation_config: dict = None
    ):
        self.output_dir = output_dir
        self.text_chunker = text_chunker
        logger.info("MockAudioGenerator initialized (using mock implementation)")
        logger.warning("This is a mock implementation - no actual audio will be generated")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    async def generate(self, text: str, language: str = "en") -> Tuple[str, str]:
        """Mock audio generation"""
        logger.info(f"Mock generating audio for text of {len(text)} chars in {language}")
        
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        # Generate fake audio file
        audio_id = str(uuid.uuid4())
        file_path = os.path.join(self.output_dir, f"{audio_id}.wav")
        
        # Create a dummy file
        with open(file_path, 'wb') as f:
            f.write(b'MOCK_AUDIO_DATA')
        
        logger.info(f"Mock audio 'generated': {file_path}")
        return file_path, audio_id
    
    async def generate_chunked(self, chunks: List[str], language: str = "en") -> Tuple[str, str]:
        """Mock chunked audio generation"""
        logger.info(f"Mock generating audio for {len(chunks)} chunks in {language}")
        
        # Simulate longer processing time for chunks
        await asyncio.sleep(len(chunks) * 0.3)
        
        # Generate fake audio file
        audio_id = str(uuid.uuid4())
        file_path = os.path.join(self.output_dir, f"{audio_id}.wav")
        
        # Create a dummy file
        with open(file_path, 'wb') as f:
            f.write(b'MOCK_CHUNKED_AUDIO_DATA')
        
        logger.info(f"Mock chunked audio 'generated': {file_path}")
        return file_path, audio_id
    
    def get_supported_languages(self) -> List[str]:
        """Return supported languages"""
        return ["es", "en", "pt"]
    
    async def cleanup_temp_files(self) -> None:
        """Clean up temporary files"""
        logger.info("Mock cleanup completed")