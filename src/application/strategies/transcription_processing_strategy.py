"""
Estrategia para procesar transcripciones con alineación palabra por palabra
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from ..interfaces import (
    MessageProcessingStrategy, 
    StrategyResult,
    TranscriptionService
)

logger = logging.getLogger(__name__)


class TranscriptionProcessingStrategy(MessageProcessingStrategy):
    """
    Estrategia que genera transcripciones SRT precisas con alineación palabra por palabra.
    Se ejecuta después de SpeechProcessingStrategy y antes de PostProcessingStrategy.
    """
    
    def __init__(
        self,
        transcription_service: TranscriptionService,
        enabled: bool = True
    ):
        """
        Initialize transcription processing strategy
        
        Args:
            transcription_service: Service for audio transcription
            enabled: Whether this strategy is enabled
        """
        self.transcription_service = transcription_service
        self.enabled = enabled
    
    @property
    def name(self) -> str:
        return "transcription_processing"
    
    @property
    def order(self) -> int:
        return 150  # Ejecuta después de speech (100) y antes de post-processing (200)
    
    async def can_handle(self, message: Dict[str, Any]) -> bool:
        """
        Verifica si puede procesar el mensaje.
        Solo procesa si:
        - La estrategia está habilitada
        - El servicio de transcripción está disponible
        - Hay un audio generado en el contexto
        """
        logger.info(f"TranscriptionStrategy.can_handle called - enabled: {self.enabled}")
        
        if not self.enabled:
            logger.info("TranscriptionStrategy is disabled")
            return False
            
        if not self.transcription_service.is_available():
            logger.warning("Transcription service is not available")
            return False
            
        # Check if it's a speech message
        event_type = message.get('type', '')
        can_handle = event_type in ['speech.created', 'tts.requested', 'audio.generate']
        logger.info(f"TranscriptionStrategy can handle message type '{event_type}': {can_handle}")
        return can_handle
    
    async def execute(self, message: Dict[str, Any], context: Dict[str, Any]) -> StrategyResult:
        """
        Ejecuta la transcripción del audio generado.
        """
        start_time = datetime.now()
        
        try:
            # Verificar que hay audio generado
            audio = context.get('audio')
            if not audio:
                logger.info("No audio found in context, skipping transcription")
                return StrategyResult(
                    success=True,
                    data={
                        "message": "No audio to transcribe",
                        "skipped": True
                    },
                    should_continue=True
                )
            
            audio_path = audio.file_path
            if not audio_path:
                logger.error("Audio path not found")
                return StrategyResult(
                    success=True,  # No fail the pipeline
                    data={
                        "message": "Audio path not found",
                        "skipped": True
                    },
                    should_continue=True
                )
            
            # Obtener información del speech
            speech = context.get('speech')
            language = speech.language if speech else 'en'
            original_text = speech.original_text if speech else None
            
            logger.info("="*60)
            logger.info(f"🎙️ Starting transcription processing")
            logger.info(f"Audio path: {audio_path}")
            logger.info(f"Language: {language}")
            logger.info(f"Has original text: {'Yes' if original_text else 'No'}")
            
            # Realizar transcripción con alineación
            logger.info("Performing transcription with word-level alignment...")
            
            srt_content = await self.transcription_service.transcribe_with_alignment(
                audio_path=audio_path,
                language=language,
                original_text=original_text
            )
            
            if not srt_content:
                logger.warning("Transcription returned empty content")
                return StrategyResult(
                    success=True,
                    data={
                        "message": "Transcription returned empty content",
                        "skipped": True
                    },
                    should_continue=True
                )
            
            # Estadísticas del SRT generado
            srt_lines = srt_content.strip().split('\n')
            subtitle_count = srt_content.count(' --> ')
            
            logger.info(f"✅ Transcription completed successfully")
            logger.info(f"   Generated {subtitle_count} subtitles")
            logger.info(f"   Total lines: {len(srt_lines)}")
            logger.info(f"   Total srt_content: {srt_content}")
            
            # Guardar el SRT en el contexto para PostProcessingStrategy
            context['original_text_srt'] = srt_content
            context['transcription_completed'] = True
            
            # Log sample of SRT
            if len(srt_lines) > 4:
                logger.info("   SRT sample:")
                for line in srt_lines[:4]:
                    logger.info(f"   {line}")
                logger.info("   ...")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return StrategyResult(
                success=True,
                data={
                    "message": "Transcription completed successfully",
                    "subtitle_count": subtitle_count,
                    "srt_lines": len(srt_lines),
                    "processing_time": processing_time,
                    "language": language,
                    "has_original_text": bool(original_text)
                },
                processing_time=processing_time,
                should_continue=True
            )
            
        except Exception as e:
            logger.error(f"Error in transcription processing: {str(e)}", exc_info=True)
            # No fallar el pipeline, continuar sin transcripción
            return StrategyResult(
                success=True,
                data={
                    "message": f"Transcription error: {str(e)}",
                    "error": True
                },
                error=str(e),
                should_continue=True
            )
    
    async def initialize(self) -> None:
        """Initialize the strategy"""
        if self.enabled:
            logger.info("TranscriptionProcessingStrategy initialized")
            logger.info(f"Transcription service available: {self.transcription_service.is_available()}")
            if self.transcription_service.is_available():
                languages = self.transcription_service.get_supported_languages()
                logger.info(f"Supported languages: {', '.join(languages[:10])}...")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        pass