"""
WhisperX implementation of TranscriptionService with Silero VAD
"""
import logging
import os
import gc
from typing import Optional, Dict, Any, List
import asyncio
from pathlib import Path

try:
    import whisperx
    import torch
    WHISPERX_AVAILABLE = True
except ImportError:
    WHISPERX_AVAILABLE = False
    
from ...application.interfaces import TranscriptionService

logger = logging.getLogger(__name__)


class WhisperXTranscriptionService(TranscriptionService):
    """WhisperX implementation with word-level alignment using Silero VAD"""
    
    def __init__(
        self,
        model_name: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        batch_size: int = 16,
        language: Optional[str] = None,
        words_per_subtitle: int = 1  # 1 for word-by-word, higher for grouped
    ):
        """
        Initialize WhisperX transcription service
        
        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            device: Device to use (cuda, cpu)
            compute_type: Compute type (float16, int8)
            batch_size: Batch size for transcription
            language: Default language (None for auto-detection)
            words_per_subtitle: Number of words per subtitle (1 for word-by-word)
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.batch_size = batch_size
        self.default_language = language
        self.words_per_subtitle = words_per_subtitle
        self.model = None
        self.align_model = None
        self.diarize_model = None
        
        if not WHISPERX_AVAILABLE:
            logger.error("WhisperX is not installed. Please install it with: pip install git+https://github.com/m-bain/whisperX.git")
            return
            
        # Initialize model on first use to avoid memory issues
        logger.info(f"WhisperX service configured: model={model_name}, device={device}, words_per_subtitle={words_per_subtitle}")
        logger.info(f"WhisperX available: {WHISPERX_AVAILABLE}")
    
    def _load_model(self):
        """Lazy load the model"""
        if self.model is None and WHISPERX_AVAILABLE:
            logger.info(f"Loading WhisperX model: {self.model_name}")
            self.model = whisperx.load_model(
                self.model_name,
                self.device,
                compute_type=self.compute_type
            )
            logger.info("WhisperX model loaded successfully")
    
    def _load_align_model(self, language: str):
        """Load alignment model for specific language"""
        if self.align_model is None and WHISPERX_AVAILABLE:
            logger.info(f"Loading alignment model for language: {language}")
            self.align_model, self.align_metadata = whisperx.load_align_model(
                language_code=language,
                device=self.device
            )
            logger.info("Alignment model loaded successfully")
    
    async def transcribe_with_alignment(
        self,
        audio_path: str,
        language: Optional[str] = None,
        original_text: Optional[str] = None
    ) -> str:
        """
        Transcribe audio and return aligned SRT with word-level timestamps
        """
        if not WHISPERX_AVAILABLE:
            logger.error("WhisperX not available, returning empty SRT")
            return ""
            
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return ""
        
        try:
            # Run transcription in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            srt_content = await loop.run_in_executor(
                None,
                self._transcribe_sync,
                audio_path,
                language,
                original_text
            )
            return srt_content
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}", exc_info=True)
            return ""
    
    def _transcribe_sync(
        self,
        audio_path: str,
        language: Optional[str] = None,
        original_text: Optional[str] = None
    ) -> str:
        """Synchronous transcription with alignment"""
        try:
            # Load model if needed
            self._load_model()
            
            # Load audio
            logger.info(f"Loading audio from: {audio_path}")
            audio = whisperx.load_audio(audio_path)
            
            # Transcribe with VAD
            logger.info("Starting transcription with VAD...")
            result = self.model.transcribe(
                audio,
                batch_size=self.batch_size,
                language=language or self.default_language
            )
            
            detected_language = result.get("language", language or "en")
            logger.info(f"Detected language: {detected_language}")
            
            # Align whisper output with wav2vec2 for word-level timestamps
            self._load_align_model(detected_language)
            logger.info("Starting word-level alignment with wav2vec2...")
            
            result = whisperx.align(
                result["segments"],
                self.align_model,
                self.align_metadata,
                audio,
                self.device,
                return_char_alignments=False  # We want word-level, not character-level
            )
            
            # Log alignment results
            word_count = sum(len(seg.get("words", [])) for seg in result["segments"])
            logger.info(f"Alignment completed: {word_count} words aligned")
            
            # Convert to SRT format
            srt_content = self._convert_to_srt(result["segments"])
            logger.info(f"Generated SRT with {len(result['segments'])} segments")
            
            # Clean up memory
            del audio
            gc.collect()
            
            return srt_content
            
        except Exception as e:
            logger.error(f"Error in synchronous transcription: {str(e)}", exc_info=True)
            return ""
    
    def _convert_to_srt(self, segments: List[Dict[str, Any]]) -> str:
        """Convert WhisperX segments to SRT format with word-level timestamps"""
        srt_lines = []
        srt_index = 1
        
        for segment in segments:
            # Check if we have word-level timestamps
            if "words" in segment and segment["words"]:
                if self.words_per_subtitle == 1:
                    # Generate word-by-word subtitles
                    for word_data in segment["words"]:
                        if "start" in word_data and "end" in word_data:
                            word = word_data.get("word", "").strip()
                            if word:  # Skip empty words
                                start_time = self._format_timestamp(word_data["start"])
                                end_time = self._format_timestamp(word_data["end"])
                                
                                # Create SRT entry for each word
                                srt_lines.append(f"{srt_index}")
                                srt_lines.append(f"{start_time} --> {end_time}")
                                srt_lines.append(word)
                                srt_lines.append("")  # Empty line between entries
                                srt_index += 1
                else:
                    # Group words together
                    words = segment["words"]
                    for i in range(0, len(words), self.words_per_subtitle):
                        group = words[i:i + self.words_per_subtitle]
                        if group and all("start" in w and "end" in w for w in group):
                            start_time = self._format_timestamp(group[0]["start"])
                            end_time = self._format_timestamp(group[-1]["end"])
                            text = " ".join(w.get("word", "").strip() for w in group)
                            
                            if text:
                                srt_lines.append(f"{srt_index}")
                                srt_lines.append(f"{start_time} --> {end_time}")
                                srt_lines.append(text)
                                srt_lines.append("")
                                srt_index += 1
            else:
                # Fallback to segment-level if no word timestamps
                start_time = self._format_timestamp(segment["start"])
                end_time = self._format_timestamp(segment["end"])
                text = segment["text"].strip()
                
                if text:
                    srt_lines.append(f"{srt_index}")
                    srt_lines.append(f"{start_time} --> {end_time}")
                    srt_lines.append(text)
                    srt_lines.append("")
                    srt_index += 1
        
        return "\n".join(srt_lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to SRT timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Basic transcription without alignment"""
        if not WHISPERX_AVAILABLE:
            return {"text": "", "segments": []}
            
        try:
            self._load_model()
            audio = whisperx.load_audio(audio_path)
            
            result = self.model.transcribe(
                audio,
                batch_size=self.batch_size,
                language=language or self.default_language
            )
            
            del audio
            gc.collect()
            
            return result
            
        except Exception as e:
            logger.error(f"Error in basic transcription: {str(e)}", exc_info=True)
            return {"text": "", "segments": []}
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes"""
        return [
            "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko",
            "ar", "hi", "tr", "pl", "nl", "sv", "fi", "da", "no", "cs"
        ]
    
    def is_available(self) -> bool:
        """Check if the transcription service is available"""
        return WHISPERX_AVAILABLE
    
    def __del__(self):
        """Clean up models on deletion"""
        if self.model is not None:
            del self.model
        if self.align_model is not None:
            del self.align_model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()