"""
Estrategias de procesamiento de mensajes
"""
from .speech_processing_strategy import SpeechProcessingStrategy
from .validation_strategy import ValidationStrategy
from .post_processing_strategy import PostProcessingStrategy
from .transcription_processing_strategy import TranscriptionProcessingStrategy
from .word_processing_strategy import WordProcessingStrategy

__all__ = [
    'SpeechProcessingStrategy',
    'ValidationStrategy',
    'PostProcessingStrategy',
    'TranscriptionProcessingStrategy',
    'WordProcessingStrategy'
]