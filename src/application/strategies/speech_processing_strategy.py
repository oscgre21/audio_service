"""
Estrategia para procesamiento de mensajes de speech
Refactorización de ProcessSpeechMessageUseCase usando el patrón Strategy
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import uuid
import asyncio

from ..interfaces import (
    MessageProcessingStrategy, StrategyResult,
    AudioGenerator, TextChunker, FileStorage, AudioUploader, VoiceReferenceService
)
from ...domain.entities import Speech, Audio, Message
from ...domain.value_objects.audio_id import AudioId
from ..utils import generate_srt_from_text

logger = logging.getLogger(__name__)


class SpeechProcessingStrategy(MessageProcessingStrategy):
    """
    Estrategia principal para procesar mensajes de speech.
    Convierte el texto en audio usando Higgs Audio Engine.
    """
    
    def __init__(
        self,
        audio_generator: AudioGenerator,
        text_chunker: TextChunker,
        file_storage: FileStorage,
        audio_uploader: Optional[AudioUploader] = None,
        voice_reference_service: Optional[VoiceReferenceService] = None,
        max_chunk_length: int = 566
    ):
        self.audio_generator = audio_generator
        self.text_chunker = text_chunker
        self.file_storage = file_storage
        self.audio_uploader = audio_uploader
        self.voice_reference_service = voice_reference_service
        self.max_chunk_length = max_chunk_length
    
    @property
    def name(self) -> str:
        return "speech_processing"
    
    @property
    def order(self) -> int:
        return 100  # Ejecuta después de validación (si existe)
    
    async def can_handle(self, message: Dict[str, Any]) -> bool:
        """
        Verifica si este mensaje es un mensaje de speech que podemos procesar.
        """
        try:
            # Verificar estructura básica
            if not isinstance(message, dict):
                return False
            
            # Verificar que tenga speechDto
            data = message.get('data', {})
            speech_dto = data.get('speechDto', {})
            
            # Debe tener al menos texto original
            return bool(speech_dto.get('original_text'))
            
        except Exception:
            return False
    
    async def execute(self, message: Dict[str, Any], context: Dict[str, Any]) -> StrategyResult:
        """
        Ejecuta el procesamiento del mensaje de speech.
        """
        start_time = datetime.now()
        
        try:
            # 1. Extraer datos del mensaje
            message_data = message.get('data', {})
            speech_dto = message_data.get('speechDto', {})
            
            # Crear entidad Message para compatibilidad
            message_entity = Message(
                id=message.get('id', str(uuid.uuid4())),
                event_type=message.get('type', 'speech.created'),
                data=message_data,
                timestamp=message.get('timestamp', datetime.now()),
                retry_count=message.get('retryCount', 0)
            )
            
            # Validar estructura del mensaje
            if not speech_dto or not speech_dto.get('original_text'):
                logger.warning(f"Message {message_entity.id} has no text to process")
                return StrategyResult(
                    success=False,
                    data={"message": "No text to process"},
                    error="No text to process"
                )
            
            # 2. Obtener character del DTO
            character = speech_dto.get('character')
            reference_audio_path = None
            
            if self.voice_reference_service and character:
                reference_audio_path = self.voice_reference_service.get_voice_path(character)
                logger.info(f"Using character voice: {character} -> {reference_audio_path}")
            
            # 3. Crear entidad Speech
            speech = Speech(
                id=message_data.get('speechId', ''),
                user_id=speech_dto.get('user_uuid', speech_dto.get('userId', '')),
                name=speech_dto.get('name', ''),
                language=speech_dto.get('language', 'en'),
                original_text=speech_dto.get('original_text', ''),
                created_at=datetime.now()
            )
            
            # Validar speech
            if not speech.id or not speech.original_text:
                return StrategyResult(
                    success=False,
                    data={"message": "Invalid speech data"},
                    error="Invalid speech data"
                )
            
            # Guardar en contexto para otras estrategias
            context['speech'] = speech
            context['message_entity'] = message_entity
            
            logger.info("="*60)
            logger.info(f"Processing speech message: {message_entity.id}")
            logger.info(f"Speech ID: {speech.id}")
            logger.info(f"Language: {speech.language}")
            logger.info(f"Text length: {len(speech.original_text)} characters")
            logger.info(f"Text preview: {speech.original_text[:100]}...")
            
            # 3. Determinar si necesita chunking
            file_path: str
            audio_id: str
            
            if len(speech.original_text) > self.max_chunk_length:
                logger.info(f"Text exceeds {self.max_chunk_length} chars, will be chunked")
                chunks = self.text_chunker.split(speech.original_text, self.max_chunk_length)
                logger.info(f"Starting chunked audio generation with {len(chunks)} chunks")
                try:
                    generation_timeout = 300 * len(chunks)  # 5 minutes per chunk
                    file_path, audio_id = await asyncio.wait_for(
                        self.audio_generator.generate_chunked(
                            chunks=chunks,
                            language=speech.language,
                            reference_audio_path=reference_audio_path
                        ),
                        timeout=generation_timeout
                    )
                    logger.info(f"Chunked audio generation completed: {audio_id}")
                except asyncio.TimeoutError:
                    logger.error(f"Chunked audio generation timed out after {generation_timeout} seconds")
                    return StrategyResult(
                        success=False,
                        data={"message": "Chunked audio generation timed out"},
                        error=f"Chunked audio generation timed out after {generation_timeout} seconds"
                    )
                except Exception as e:
                    logger.error(f"Error in chunked audio generation: {str(e)}", exc_info=True)
                    raise
                was_chunked = True
                chunks_count = len(chunks)
            else:
                logger.info(f"Starting single audio generation ${speech.language}")
                try:
                    # Add timeout to prevent indefinite blocking
                    generation_timeout = 300  # 5 minutes timeout
                    file_path, audio_id = await asyncio.wait_for(
                        self.audio_generator.generate(
                            text=speech.original_text,
                            language=speech.language,
                            reference_audio_path=reference_audio_path
                        ),
                        timeout=generation_timeout
                    )
                    logger.info(f"Single audio generation completed: {audio_id}")
                except asyncio.TimeoutError:
                    logger.error(f"Audio generation timed out after {generation_timeout} seconds")
                    return StrategyResult(
                        success=False,
                        data={"message": "Audio generation timed out"},
                        error=f"Audio generation timed out after {generation_timeout} seconds"
                    )
                except Exception as e:
                    logger.error(f"Error in audio generation: {str(e)}", exc_info=True)
                    raise
                was_chunked = False
                chunks_count = 1
            
            logger.info(f"✅ Audio generated successfully")
            logger.info(f"   ID: {audio_id}")
            logger.info(f"   File: {file_path}")
            
            # 4. Obtener tamaño del archivo
            file_size = 0
            try:
                import os
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    logger.info(f"   Size: {file_size / (1024 * 1024):.2f} MB")
            except:
                pass
            
            # 5. Crear entidad Audio
            audio = Audio(
                id=audio_id,
                speech_id=speech.id,
                file_path=file_path,
                file_size=file_size,
                was_chunked=was_chunked,
                chunks_count=chunks_count,
                created_at=datetime.now()
            )
            
            # Guardar audio en contexto
            context['audio'] = audio
            context['audio_generated'] = True
            
            # 6. Guardar metadata
            metadata = {
                "audio_id": audio.id,
                "speech_id": speech.id,
                "speech_name": speech.name,
                "user_id": speech.user_id,
                "language": speech.language,
                "text_length": len(speech.original_text),
                "was_chunked": was_chunked,
                "chunks_count": chunks_count,
                "file_size": file_size,
                "created_at": audio.created_at.isoformat(),
                "message_id": message_entity.id
            }
            
            await self.file_storage.save_metadata(audio_id, metadata)
            logger.info(f"Metadata saved for audio {audio_id}")
            
            # 7. Generar SRT básico para el contexto
            # El upload se manejará en PostProcessingStrategy para evitar duplicados
            original_text_srt = generate_srt_from_text(speech.original_text)
            logger.info(f"Generated basic SRT with {len(original_text_srt.splitlines())} lines")
            context['basic_srt'] = original_text_srt
            
            # NO subir aquí - dejar que PostProcessingStrategy maneje el upload
            logger.info("📤 Upload will be handled by PostProcessingStrategy")
            context['uploaded'] = False
            
            # 8. Calcular tiempo de procesamiento
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info("="*60)
            logger.info(f"✅ Processing completed in {processing_time:.2f} seconds")
            
            # Preparar resultado
            result_data = {
                "audio_id": audio_id,
                "file_path": file_path,
                "file_size": file_size,
                "was_chunked": was_chunked,
                "chunks_count": chunks_count,
                "upload_url": None,  # Upload se maneja en PostProcessingStrategy
                "processing_time": processing_time
            }
            
            return StrategyResult(
                success=True,
                data=result_data,
                processing_time=processing_time,
                should_continue=True  # Permite que otras estrategias procesen
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error in speech processing strategy: {str(e)}", exc_info=True)
            
            # Guardar error en contexto
            context['error'] = str(e)
            context['audio_generated'] = False
            
            return StrategyResult(
                success=False,
                data={"message": "Processing failed"},
                error=str(e),
                processing_time=processing_time,
                should_continue=False  # Detener procesamiento en caso de error
            )