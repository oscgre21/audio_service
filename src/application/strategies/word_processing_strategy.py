"""
Estrategia de procesamiento palabra por palabra
"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import os
import re
import asyncio
import shutil
import uuid
from pathlib import Path

from ..interfaces import MessageProcessingStrategy, StrategyResult, AudioUploader, AudioGenerator, FileStorage

logger = logging.getLogger(__name__)


class WordProcessingStrategy(MessageProcessingStrategy):
    """
    Estrategia que procesa el texto original palabra por palabra,
    generando un audio individual para cada palabra y subiéndolo.
    
    Se ejecuta después de PostProcessingStrategy.
    """
    
    def __init__(
        self,
        audio_generator: AudioGenerator,
        audio_uploader: AudioUploader,
        file_storage: FileStorage,
        max_concurrent_words: int = 5,
        word_timeout: float = 30.0,
        enable_word_processing: bool = True
    ):
        """
        Inicializa la estrategia de procesamiento por palabras.
        
        Args:
            audio_generator: Generador de audio
            audio_uploader: Servicio de upload
            file_storage: Almacenamiento de archivos
            max_concurrent_words: (Obsoleto - procesamiento es secuencial ahora)
            word_timeout: Timeout en segundos por palabra
            enable_word_processing: Habilitar/deshabilitar el procesamiento
        """
        self.audio_generator = audio_generator
        self.audio_uploader = audio_uploader
        self.file_storage = file_storage
        self.max_concurrent_words = max_concurrent_words
        self.word_timeout = word_timeout
        self.enable_word_processing = enable_word_processing
        self._stats = {
            "total_words_processed": 0,
            "total_words_uploaded": 0,
            "total_words_failed": 0
        }
        logger.info(f"WordProcessingStrategy initialized with enable_word_processing={enable_word_processing}, word_timeout={word_timeout}s, max_concurrent={max_concurrent_words}")
    
    def __str__(self) -> str:
        return f"WordProcessingStrategy(enabled={self.enable_word_processing}, order={self.order})"
    
    @property
    def name(self) -> str:
        return "word_processing"
    
    @property
    def order(self) -> int:
        return 250  # Ejecuta después de PostProcessingStrategy (200)
    
    async def can_handle(self, message: Dict[str, Any]) -> bool:
        """
        Procesa solo si el audio principal fue generado exitosamente.
        """
        logger.info(f"WordProcessingStrategy.can_handle called. enable_word_processing = {self.enable_word_processing}")
        return self.enable_word_processing
    
    async def execute(self, message: Dict[str, Any], context: Dict[str, Any]) -> StrategyResult:
        """
        Ejecuta el procesamiento palabra por palabra.
        """
        logger.info("=" * 60)
        logger.info("WordProcessingStrategy: STARTING")
        logger.info(f"Enable word processing: {self.enable_word_processing}")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        word_processing_results = {
            "words_processed": 0,
            "words_uploaded": 0,
            "words_failed": 0,
            "words": []
        }
        
        try:
            # Verificar si el audio principal fue generado
            audio_generated = context.get("audio_generated", False)
            logger.info(f"Audio generated check: {audio_generated}")
            logger.info(f"Context keys: {list(context.keys())}")
            
            if not audio_generated:
                logger.info(
                    f"Skipping word processing for message {message.get('id')} - "
                    "no main audio generated"
                )
                return StrategyResult(
                    success=True,
                    data={"message": "Skipped - no main audio generated"},
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    should_continue=True
                )
            
            # Verificar si el uploader está habilitado
            uploader_enabled = self.audio_uploader and self.audio_uploader.is_enabled()
            logger.info(f"Uploader enabled check: {uploader_enabled}")
            
            if not uploader_enabled:
                logger.info("Word processing skipped - uploader not enabled")
                return StrategyResult(
                    success=True,
                    data={"message": "Skipped - uploader not enabled"},
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    should_continue=True
                )
            
            # Obtener datos del contexto
            speech = context.get("speech")
            audio = context.get("audio")
            
            logger.info(f"Speech data: {speech}")
            logger.info(f"Audio data: {audio}")
            
            if not speech:
                logger.warning("No speech data found in context")
                return StrategyResult(
                    success=True,
                    data={"message": "Skipped - no speech data"},
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    should_continue=True
                )
                
            if not hasattr(speech, 'original_text') or not speech.original_text:
                logger.warning(f"No original_text in speech. Speech attributes: {dir(speech)}")
                return StrategyResult(
                    success=True,
                    data={"message": "Skipped - no original_text"},
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    should_continue=True
                )
            
            # Obtener voice reference del contexto
            voice_reference_path = context.get("voice_reference_path")
            
            # Si no está en el contexto, intentar obtener del mensaje
            if not voice_reference_path and hasattr(speech, 'character'):
                # Usar el character del speech para obtener la voz
                character = getattr(speech, 'character', 'belinda')
                if character:
                    # El path de voz ya se resolvió en SpeechProcessingStrategy
                    logger.info(f"Using character voice: {character}")
                    voice_reference_path = f"examples/voice_prompts/{character}.wav"
            
            logger.info(
                f"Starting word processing for message {message.get('id')}"
                f" - Text length: {len(speech.original_text)} chars"
            )
            
            # Dividir el texto en palabras
            words = self._split_text_into_words(speech.original_text)
            logger.info(f"Text split into {len(words)} words")
            logger.info(f"First 10 words: {words[:10] if words else 'None'}")
            
            if not words:
                logger.warning("No words found to process")
                return StrategyResult(
                    success=True,
                    data={"message": "No words to process"},
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    should_continue=True
                )
            
            # Procesar palabras de forma secuencial
            word_results = await self._process_words_sequentially(
                words, 
                speech,
                voice_reference_path,
                message.get("id")
            )
            
            # Compilar resultados
            for word_result in word_results:
                word_processing_results["words"].append(word_result)
                if word_result["success"]:
                    word_processing_results["words_processed"] += 1
                    if word_result.get("uploaded"):
                        word_processing_results["words_uploaded"] += 1
                else:
                    word_processing_results["words_failed"] += 1
            
            # Actualizar estadísticas
            self._stats["total_words_processed"] += word_processing_results["words_processed"]
            self._stats["total_words_uploaded"] += word_processing_results["words_uploaded"]
            self._stats["total_words_failed"] += word_processing_results["words_failed"]
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                f"Word processing completed for message {message.get('id')} "
                f"in {processing_time:.2f}s - "
                f"Processed: {word_processing_results['words_processed']}, "
                f"Uploaded: {word_processing_results['words_uploaded']}, "
                f"Failed: {word_processing_results['words_failed']}"
            )
            
            # Agregar resultados al contexto
            context["word_processing_results"] = word_processing_results
            
            return StrategyResult(
                success=True,
                data={
                    "message": "Word processing completed",
                    "results": word_processing_results,
                    "stats": self._get_current_stats()
                },
                processing_time=processing_time,
                should_continue=True
            )
            
        except Exception as e:
            logger.error(f"Word processing error: {str(e)}", exc_info=True)
            return StrategyResult(
                success=False,
                data={"message": "Word processing error"},
                error=str(e),
                processing_time=(datetime.now() - start_time).total_seconds(),
                should_continue=True  # No detener la cadena por errores
            )
    
    def _split_text_into_words(self, text: str) -> List[str]:
        """
        Divide el texto en palabras individuales.
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de palabras
        """
        # Remover múltiples espacios y normalizar
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Dividir por espacios pero mantener puntuación con la palabra
        # Esto preserva "Hola," como una unidad
        words = text.split(' ')
        
        # Filtrar palabras vacías
        words = [word for word in words if word.strip()]
        
        return words
    
    async def _process_words_sequentially(
        self,
        words: List[str],
        speech: Any,
        voice_reference_path: Optional[str],
        message_id: str
    ) -> List[Dict[str, Any]]:
        """
        Procesa las palabras de forma secuencial (una por una).
        
        Args:
            words: Lista de palabras a procesar
            speech: Entidad Speech
            voice_reference_path: Ruta al audio de referencia
            message_id: ID del mensaje
            
        Returns:
            Lista de resultados por palabra
        """
        results = []
        
        # Procesar palabras de forma secuencial
        for index, word in enumerate(words):
            try:
                logger.info(f"Processing word {index + 1}/{len(words)}: '{word}'")
                result = await self._process_single_word(
                    word, index, speech, voice_reference_path, message_id
                )
                results.append(result)
                
                # Log progress
                if result["success"]:
                    logger.info(f"Word {index + 1}/{len(words)} completed successfully")
                else:
                    logger.warning(f"Word {index + 1}/{len(words)} failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Error processing word {index}: {str(e)}")
                results.append({
                    "word": word,
                    "index": index,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def _process_single_word(
        self,
        word: str,
        index: int,
        speech: Any,
        voice_reference_path: Optional[str],
        message_id: str
    ) -> Dict[str, Any]:
        """
        Procesa una palabra individual: genera audio y lo sube.
        
        Args:
            word: Palabra a procesar
            index: Índice de la palabra en el texto
            speech: Entidad Speech
            voice_reference_path: Ruta al audio de referencia
            message_id: ID del mensaje
            
        Returns:
            Diccionario con el resultado del procesamiento
        """
        word_result = {
            "word": word,
            "index": index,
            "success": False,
            "uploaded": False,
            "audio_id": None,
            "file_path": None,
            "upload_result": None,
            "error": None
        }
        
        try:
            # Generar GUID único para el audio de la palabra
            word_audio_id = str(uuid.uuid4())
            
            logger.info(f"Processing word {index}: '{word}' (ID: {word_audio_id})")
            
            # Generar audio para la palabra
            try:
                # generate() retorna una tupla (file_path, audio_id)
                generated_path, _ = await asyncio.wait_for(
                    self.audio_generator.generate(
                        text=f"""  The word is: "{word}" """,
                        language=speech.language,
                        reference_audio_path=voice_reference_path
                    ),
                    timeout=self.word_timeout
                )
                
                # Renombrar el archivo generado con el GUID
                target_dir = os.path.dirname(generated_path)
                audio_file_path = os.path.join(target_dir, f"{word_audio_id}.mp3")
                shutil.move(generated_path, audio_file_path)
                
                word_result["file_path"] = audio_file_path
                word_result["audio_id"] = word_audio_id
                
                # Obtener tamaño del archivo
                file_size = os.path.getsize(audio_file_path) if os.path.exists(audio_file_path) else 0
                
                logger.debug(f"Audio generated for word {index}: {audio_file_path} ({file_size} bytes)")
                
            except asyncio.TimeoutError:
                logger.error(f"Timeout generating audio for word {index}: '{word}'")
                word_result["error"] = "Generation timeout"
                return word_result
            except Exception as e:
                logger.error(f"Error generating audio for word {index}: {str(e)}")
                word_result["error"] = f"Generation error: {str(e)}"
                return word_result
            
            # Subir el audio de la palabra
            try:
                upload_result = await self.audio_uploader.upload(
                    file_path=audio_file_path,
                    speech_id=speech.id,
                    audio_type="word",
                    metadata={
                        "word_index": index,
                        "word_text": word,
                        "parent_message_id": message_id
                    },
                    original_text=word,
                    language=speech.language,
                    original_text_srt=None  # Las palabras individuales no necesitan SRT
                )
                
                if upload_result:
                    word_result["uploaded"] = True
                    word_result["upload_result"] = upload_result
                    word_result["success"] = True
                    
                    logger.debug(
                        f"Word {index} uploaded successfully: "
                        f"UUID={upload_result.get('uuid')}"
                    )
                else:
                    word_result["error"] = "Upload failed"
                    
            except Exception as e:
                logger.error(f"Error uploading word {index}: {str(e)}")
                word_result["error"] = f"Upload error: {str(e)}"
            
            # Guardar metadata de la palabra
            try:
                await self.file_storage.save_metadata(word_audio_id, {
                    "word_index": index,
                    "word_text": word,
                    "parent_speech_id": speech.id,
                    "parent_message_id": message_id,
                    "file_path": audio_file_path,
                    "file_size": file_size,
                    "uploaded": word_result["uploaded"],
                    "upload_result": word_result.get("upload_result"),
                    "created_at": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error saving word metadata: {str(e)}")
            
            return word_result
            
        except Exception as e:
            logger.error(f"Unexpected error processing word {index}: {str(e)}")
            word_result["error"] = f"Unexpected error: {str(e)}"
            return word_result
    
    def _get_current_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas actuales"""
        total = self._stats["total_words_processed"] + self._stats["total_words_failed"]
        return {
            "total_words_processed": self._stats["total_words_processed"],
            "total_words_uploaded": self._stats["total_words_uploaded"],
            "total_words_failed": self._stats["total_words_failed"],
            "success_rate": (
                self._stats["total_words_processed"] / total * 100
                if total > 0 else 0
            )
        }
    
    async def cleanup(self) -> None:
        """Limpieza al finalizar"""
        logger.info(f"WordProcessingStrategy final stats: {self._get_current_stats()}")