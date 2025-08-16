"""
Estrategia de post-procesamiento para acciones después del procesamiento principal
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import json

from ..interfaces import MessageProcessingStrategy, StrategyResult, AudioUploader

logger = logging.getLogger(__name__)


class PostProcessingStrategy(MessageProcessingStrategy):
    """
    Estrategia que ejecuta acciones de post-procesamiento después
    de la generación de audio.
    
    Incluye: notificaciones, analytics, limpieza, webhooks, etc.
    """
    
    def __init__(
        self,
        enable_notifications: bool = True,
        enable_analytics: bool = True,
        enable_cleanup: bool = False,
        webhook_url: Optional[str] = None,
        audio_uploader: Optional[AudioUploader] = None
    ):
        """
        Inicializa la estrategia de post-procesamiento.
        
        Args:
            enable_notifications: Habilitar notificaciones
            enable_analytics: Habilitar registro de analytics
            enable_cleanup: Habilitar limpieza de archivos temporales
            webhook_url: URL para enviar webhooks
            audio_uploader: Servicio de upload de audio (opcional)
        """
        self.enable_notifications = enable_notifications
        self.enable_analytics = enable_analytics
        self.enable_cleanup = enable_cleanup
        self.webhook_url = webhook_url
        self.audio_uploader = audio_uploader
        self._stats = {
            "total_processed": 0,
            "total_success": 0,
            "total_failed": 0,
            "total_bytes_processed": 0
        }
    
    @property
    def name(self) -> str:
        return "post_processing"
    
    @property
    def order(self) -> int:
        return 200  # Ejecuta después del procesamiento principal
    
    async def can_handle(self, message: Dict[str, Any]) -> bool:
        """
        Post-procesamiento se ejecuta solo si el audio fue generado.
        """
        # Este método será llamado con el contexto actualizado
        # pero por ahora retornamos True
        return True
    
    async def execute(self, message: Dict[str, Any], context: Dict[str, Any]) -> StrategyResult:
        """
        Ejecuta acciones de post-procesamiento.
        """
        start_time = datetime.now()
        post_processing_results = {}
        
        try:
            # Verificar si el audio fue generado exitosamente
            audio_generated = context.get("audio_generated", False)
            
            if not audio_generated:
                logger.info(
                    f"Skipping post-processing for message {message.get('id')} - "
                    "no audio generated"
                )
                return StrategyResult(
                    success=True,
                    data={"message": "Skipped - no audio generated"},
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    should_continue=True
                )
            
            # Obtener datos del contexto
            audio = context.get("audio")
            speech = context.get("speech")
            basic_srt = context.get("basic_srt", "")
            transcription_srt = context.get("original_text_srt")
            transcription_completed = context.get("transcription_completed", False)
            
            # Log diagnóstico
            logger.info(f"PostProcessing context check:")
            logger.info(f"  - Has audio: {bool(audio)}")
            logger.info(f"  - Has speech: {bool(speech)}")
            logger.info(f"  - Has basic_srt: {bool(basic_srt)}")
            logger.info(f"  - Has transcription_srt: {bool(transcription_srt)}")
            logger.info(f"  - Transcription completed: {transcription_completed}")
            logger.info(f"  - Uploader enabled: {self.audio_uploader.is_enabled() if self.audio_uploader else False}")
            
            # 0. Upload del audio (solo si hay transcripción completada)
            upload_result = None
            if self.audio_uploader and self.audio_uploader.is_enabled() and audio and speech:
                # Solo subir si hay transcripción palabra por palabra completada
                if transcription_completed and transcription_srt:
                    logger.info("📤 Uploading audio to server with word-level SRT...")
                    logger.info(f"   SRT lines: {transcription_srt.count(' --> ')}")
                    
                    upload_result = await self.audio_uploader.upload(
                        file_path=audio.file_path,
                        speech_id=speech.id,
                        audio_type="main",
                        metadata=None,
                        original_text=speech.original_text,
                        language=speech.language,
                        original_text_srt=transcription_srt
                    )
                else:
                    logger.info("⏳ Skipping upload - waiting for word-level transcription")
                    logger.info("   Transcription is required for upload")
                    post_processing_results["upload"] = {
                        "success": False,
                        "reason": "waiting_for_transcription"
                    }
                
                if upload_result:
                    logger.info("✅ Audio uploaded successfully")
                    logger.info(f"   UUID: {upload_result.get('uuid')}")
                    logger.info(f"   URL: {upload_result.get('file_url')}")
                    context['upload_result'] = upload_result
                    post_processing_results["upload"] = {
                        "success": True,
                        "srt_type": "transcription" if (transcription_completed and transcription_srt) else "basic"
                    }
                    
                    # Actualizar metadata con info del upload
                    if hasattr(audio, 'id'):
                        try:
                            from ...infrastructure.storage import LocalFileStorage
                            file_storage = LocalFileStorage(output_dir=audio.file_path.rsplit('/', 1)[0])
                            metadata = await file_storage.get_metadata(audio.id)
                            metadata["upload_result"] = {
                                "uploaded": True,
                                "upload_time": datetime.now().isoformat(),
                                "server_uuid": upload_result.get("uuid"),
                                "server_url": upload_result.get("file_url"),
                                "server_path": upload_result.get("file_path"),
                                "srt_type": "transcription" if (transcription_completed and transcription_srt) else "basic"
                            }
                            await file_storage.save_metadata(audio.id, metadata)
                            logger.info("Metadata updated with upload info")
                        except Exception as e:
                            logger.error(f"Failed to update metadata: {str(e)}")
                else:
                    logger.warning("❌ Audio upload failed")
                    post_processing_results["upload"] = {
                        "success": False,
                        "reason": "upload_failed"
                    }
            
            # 1. Analytics
            if self.enable_analytics:
                analytics_result = await self._record_analytics(
                    message, audio, speech, upload_result
                )
                post_processing_results["analytics"] = analytics_result
            
            # 2. Notificaciones
            if self.enable_notifications:
                notification_result = await self._send_notifications(
                    message, audio, speech, upload_result
                )
                post_processing_results["notifications"] = notification_result
            
            # 3. Webhook
            if self.webhook_url and upload_result:
                webhook_result = await self._send_webhook(
                    message, audio, speech, upload_result
                )
                post_processing_results["webhook"] = webhook_result
            
            # 4. Limpieza (si está habilitada)
            if self.enable_cleanup:
                cleanup_result = await self._cleanup_temp_files(context)
                post_processing_results["cleanup"] = cleanup_result
            
            # 5. Actualizar estadísticas
            self._update_stats(audio, context)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                f"Post-processing completed for message {message.get('id')} "
                f"in {processing_time:.2f}s"
            )
            
            return StrategyResult(
                success=True,
                data={
                    "message": "Post-processing completed",
                    "results": post_processing_results,
                    "stats": self._get_current_stats()
                },
                processing_time=processing_time,
                should_continue=True
            )
            
        except Exception as e:
            logger.error(f"Post-processing error: {str(e)}", exc_info=True)
            return StrategyResult(
                success=False,
                data={"message": "Post-processing error"},
                error=str(e),
                processing_time=(datetime.now() - start_time).total_seconds(),
                should_continue=True  # No detener la cadena por errores de post-procesamiento
            )
    
    async def _record_analytics(
        self, 
        message: Dict[str, Any], 
        audio: Any, 
        speech: Any,
        upload_result: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Registra analytics del procesamiento"""
        try:
            analytics_data = {
                "message_id": message.get("id"),
                "speech_id": speech.id if speech else None,
                "audio_id": audio.id if audio else None,
                "language": speech.language if speech else None,
                "text_length": len(speech.original_text) if speech else 0,
                "file_size": audio.file_size if audio else 0,
                "was_chunked": audio.was_chunked if audio else False,
                "chunks_count": audio.chunks_count if audio else 0,
                "uploaded": bool(upload_result),
                "timestamp": datetime.now().isoformat()
            }
            
            # Aquí normalmente enviarías a un servicio de analytics
            logger.info(f"Analytics recorded: {json.dumps(analytics_data, indent=2)}")
            
            return {
                "success": True,
                "data": analytics_data
            }
            
        except Exception as e:
            logger.error(f"Analytics error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_notifications(
        self,
        message: Dict[str, Any],
        audio: Any,
        speech: Any,
        upload_result: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Envía notificaciones sobre el procesamiento completado"""
        try:
            notification_data = {
                "type": "audio_processing_completed",
                "message_id": message.get("id"),
                "speech_id": speech.id if speech else None,
                "audio_id": audio.id if audio else None,
                "user_id": speech.user_id if speech else None,
                "status": "uploaded" if upload_result else "generated",
                "file_url": upload_result.get("file_url") if upload_result else None,
                "timestamp": datetime.now().isoformat()
            }
            
            # Aquí normalmente enviarías a un servicio de notificaciones
            # Por ejemplo: email, push notifications, etc.
            logger.info(
                f"Notification prepared for user {notification_data['user_id']}: "
                f"Audio {notification_data['audio_id']} is ready"
            )
            
            return {
                "success": True,
                "notification_type": "audio_ready",
                "user_notified": notification_data["user_id"]
            }
            
        except Exception as e:
            logger.error(f"Notification error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_webhook(
        self,
        message: Dict[str, Any],
        audio: Any,
        speech: Any,
        upload_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Envía webhook con los resultados del procesamiento"""
        try:
            webhook_payload = {
                "event": "audio_processing_completed",
                "message_id": message.get("id"),
                "speech_id": speech.id if speech else None,
                "audio_id": audio.id if audio else None,
                "file_url": upload_result.get("file_url"),
                "file_size": audio.file_size if audio else 0,
                "language": speech.language if speech else None,
                "processing_stats": {
                    "was_chunked": audio.was_chunked if audio else False,
                    "chunks_count": audio.chunks_count if audio else 0,
                    "text_length": len(speech.original_text) if speech else 0
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Aquí normalmente harías una llamada HTTP al webhook
            # import aiohttp
            # async with aiohttp.ClientSession() as session:
            #     async with session.post(self.webhook_url, json=webhook_payload) as response:
            #         response_data = await response.json()
            
            logger.info(f"Webhook would be sent to {self.webhook_url}")
            logger.debug(f"Webhook payload: {json.dumps(webhook_payload, indent=2)}")
            
            return {
                "success": True,
                "webhook_url": self.webhook_url,
                "payload_size": len(json.dumps(webhook_payload))
            }
            
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _cleanup_temp_files(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Limpia archivos temporales si está configurado"""
        try:
            cleaned_files = []
            
            # Aquí normalmente limpiarías archivos temporales
            # Por ejemplo, chunks individuales si fueron concatenados
            
            logger.info(f"Cleanup completed: {len(cleaned_files)} files removed")
            
            return {
                "success": True,
                "files_cleaned": len(cleaned_files)
            }
            
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _update_stats(self, audio: Any, context: Dict[str, Any]) -> None:
        """Actualiza estadísticas internas"""
        self._stats["total_processed"] += 1
        
        if context.get("audio_generated"):
            self._stats["total_success"] += 1
            if audio and audio.file_size:
                self._stats["total_bytes_processed"] += audio.file_size
        else:
            self._stats["total_failed"] += 1
    
    def _get_current_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas actuales"""
        return {
            "total_processed": self._stats["total_processed"],
            "total_success": self._stats["total_success"],
            "total_failed": self._stats["total_failed"],
            "success_rate": (
                self._stats["total_success"] / self._stats["total_processed"] * 100
                if self._stats["total_processed"] > 0 else 0
            ),
            "total_mb_processed": self._stats["total_bytes_processed"] / (1024 * 1024)
        }
    
    async def cleanup(self) -> None:
        """Limpieza al finalizar"""
        logger.info(f"PostProcessingStrategy final stats: {self._get_current_stats()}")