"""
Higgs Audio Engine implementation of AudioGenerator
"""
import os
import uuid
import asyncio
import logging
import time
from typing import Tuple, List, Optional
from pathlib import Path

import torch
import torchaudio
from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine, HiggsAudioResponse
from boson_multimodal.data_types import ChatMLSample, Message, AudioContent
from pydub import AudioSegment
import base64

from ...application.interfaces import AudioGenerator, TextChunker

logger = logging.getLogger(__name__)


class HiggsAudioGenerator(AudioGenerator):
    """Higgs Audio Engine implementation for audio generation"""
    
    def __init__(
        self, 
        model_path: str,
        tokenizer_path: str,
        output_dir: str,
        device: Optional[str] = None,
        torch_seed: int = 42,
        text_chunker: Optional[TextChunker] = None,
        generation_config: Optional[dict] = None,
        output_format: str = "mp3",  # "wav" or "mp3"
        mp3_bitrate: str = "128k",  # Audio bitrate for MP3
        default_reference_audio_path: Optional[str] = "examples/voice_prompts/belinda.wav"
    ):
        self.model_path = model_path
        self.tokenizer_path = tokenizer_path
        self.output_dir = Path(output_dir)
        self.text_chunker = text_chunker
        self.output_format = output_format.lower()
        self.mp3_bitrate = mp3_bitrate
        self.default_reference_audio_path = default_reference_audio_path
        
        # Set device
        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device
            
        # Set torch seed for reproducibility
        torch.manual_seed(torch_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(torch_seed)
        
        # Default generation config
        self.generation_config = generation_config or {
            "max_new_tokens": 1024,
            "temperature": 0.1,
            "top_p": 0.95,
            "top_k": 50
        }
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the engine
        logger.info(f"Initializing Higgs Audio Engine on device: {self.device}")
        self.engine = HiggsAudioServeEngine(
            self.model_path,
            self.tokenizer_path,
            device=self.device
        )
        logger.info("Higgs Audio Engine initialized successfully")
    
    def _load_reference_audio_base64(self, audio_path: str) -> Optional[str]:
        """Load audio file and convert to base64"""
        try:
            if audio_path and Path(audio_path).exists():
                with open(audio_path, "rb") as audio_file:
                    logger.warning(f"Reference audio found: {audio_path}")
                    return base64.b64encode(audio_file.read()).decode("utf-8")
            else:
                logger.warning(f"Reference audio path not found: {audio_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading reference audio: {str(e)}")
            return None
    
    def _create_system_prompt(self, language: str) -> str:
        """Create system prompt based on language"""
        # Language-specific voices for consistency
        voice_settings = {
            "es": "The audio is recorded with a professional Spanish voice, clear and neutral accent.",
            "en": "The audio is recorded with a professional English voice, clear and neutral accent.",
            "pt": "The audio is recorded with a professional Portuguese voice, clear and neutral accent."
        }
        
        voice_desc = voice_settings.get(language, voice_settings["en"])
        
        return f"Generate audio following instruction.\n\n<|scene_desc_start|>\n{voice_desc}\n<|scene_desc_end|>"
    
    async def generate(self, text: str, language: str = "en", reference_audio_path: Optional[str] = "examples/voice_prompts/belinda.wav") -> Tuple[str, str]:
        """Generate audio from text with optional reference audio"""
        try:
            logger.info(f"Starting audio generation for text of {len(text)} chars in {language}")
            logger.info(f"Using device: {self.device}")
            
            # Use default reference audio if not provided
            if reference_audio_path is None:
                reference_audio_path = self.default_reference_audio_path
            
            # Create messages
            logger.info("Creating system and user prompts")
            messages = [
                Message(
                    role="system",
                    content=self._create_system_prompt(language)
                )
            ]
            
            # Add reference audio message if available
            if reference_audio_path:
                reference_audio_base64 = self._load_reference_audio_base64(reference_audio_path)
                if reference_audio_base64:
                    logger.info(f"Adding reference audio from: {reference_audio_path}")
                    messages.append(
                        Message(
                            role="assistant",
                            content=AudioContent(raw_audio=reference_audio_base64, audio_url="placeholder")
                        )
                    )
            
            # Add user message
            messages.append(
                Message(
                    role="user",
                    content=text
                )
            )
            
            # Generate in thread pool to avoid blocking
            logger.info("Submitting generation task to thread pool executor")
            loop = asyncio.get_event_loop()
            start_time = asyncio.get_event_loop().time()
            
            output = await loop.run_in_executor(
                None,
                self._generate_sync,
                messages
            )
            
            generation_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"Audio generation completed in {generation_time:.2f} seconds")
            
            # Save audio
            audio_id = str(uuid.uuid4())
            
            if self.output_format == "mp3":
                # First save as WAV temporarily
                temp_wav_path = self.output_dir / f"{audio_id}_temp.wav"
                final_path = self.output_dir / f"{audio_id}.mp3"
                
                logger.info(f"Saving temporary WAV to: {temp_wav_path}")
                logger.info(f"Audio shape: {output.audio.shape}, Sample rate: {output.sampling_rate}")
                
                # Save temporary WAV
                torchaudio.save(
                    str(temp_wav_path),
                    torch.from_numpy(output.audio)[None, :],
                    output.sampling_rate
                )
                
                # Get WAV size before conversion
                wav_size_mb = temp_wav_path.stat().st_size / (1024 * 1024)
                
                # Convert to MP3
                logger.info(f"Converting to MP3 with bitrate: {self.mp3_bitrate}")
                audio = AudioSegment.from_wav(str(temp_wav_path))
                audio.export(
                    str(final_path),
                    format="mp3",
                    bitrate=self.mp3_bitrate
                )
                
                # Get MP3 size
                mp3_size_mb = final_path.stat().st_size / (1024 * 1024)
                compression_ratio = (1 - mp3_size_mb/wav_size_mb) * 100
                
                logger.info(f"MP3 file saved: {final_path} ({mp3_size_mb:.2f} MB)")
                logger.info(f"Original WAV size: {wav_size_mb:.2f} MB")
                logger.info(f"Compression ratio: {compression_ratio:.1f}% reduction")
                
                # Remove temporary WAV
                temp_wav_path.unlink()
                
                file_path = final_path
            else:
                # Save as WAV
                file_path = self.output_dir / f"{audio_id}.wav"
                
                logger.info(f"Saving audio to: {file_path}")
                logger.info(f"Audio shape: {output.audio.shape}, Sample rate: {output.sampling_rate}")
                
                # Save the audio file
                torchaudio.save(
                    str(file_path),
                    torch.from_numpy(output.audio)[None, :],
                    output.sampling_rate
                )
                
                # Get file size
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                logger.info(f"WAV file saved successfully: {file_path} ({file_size_mb:.2f} MB)")
            
            return str(file_path), audio_id
            
        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            raise
    
    def _generate_sync(self, messages: List[Message]) -> HiggsAudioResponse:
        """Synchronous generation method"""
        logger.info("Starting synchronous audio generation")
        logger.info(f"Generation config: max_tokens={self.generation_config['max_new_tokens']}, "
                   f"temp={self.generation_config['temperature']}, "
                   f"top_p={self.generation_config['top_p']}, "
                   f"top_k={self.generation_config['top_k']}")
        
        start_time = time.time()
        
        try:
            response = self.engine.generate(
                chat_ml_sample=ChatMLSample(messages=messages),
                max_new_tokens=self.generation_config["max_new_tokens"],
                temperature=self.generation_config["temperature"],
                top_p=self.generation_config["top_p"],
                top_k=self.generation_config["top_k"],
                stop_strings=["<|end_of_text|>", "<|eot_id|>"],
                seed=12345,  # Seed fijo para consistencia
            )
            
            sync_time = time.time() - start_time
            logger.info(f"Synchronous generation completed in {sync_time:.2f} seconds")
            
            return response
        except Exception as e:
            logger.error(f"Error in synchronous generation: {str(e)}", exc_info=True)
            raise
    
    async def generate_chunked(self, chunks: List[str], language: str = "en", reference_audio_path: Optional[str] = "examples/voice_prompts/belinda.wav") -> Tuple[str, str]:
        """Generate audio from multiple text chunks and concatenate"""
        try:
            logger.info(f"Generating audio for {len(chunks)} chunks in {language}")
            
            # Create temporary directory for chunks
            temp_dir = self.output_dir / "temp_chunks"
            temp_dir.mkdir(exist_ok=True)
            
            # Generate audio for each chunk
            chunk_files = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}: {len(chunk)} chars")
                
                # Add context markers for consistent voice
                contextualized_chunk = chunk
                if i > 0:  # Not first chunk
                    contextualized_chunk = f"{chunk}"
                print(f"Contextualized chunk {i+1}: {contextualized_chunk[:10]}...")  # Print first 50 chars for debugging
                print(f"Reference audio path: {reference_audio_path}")
                # Generate audio for chunk with reference audio
                chunk_path, _ = await self.generate(contextualized_chunk, language, reference_audio_path)
                chunk_files.append(chunk_path)
            
            # Concatenate audio files
            audio_id = str(uuid.uuid4())
            output_path = self.output_dir / f"{audio_id}.wav"
            
            await self._concatenate_audio_files(chunk_files, str(output_path))
            
            # Clean up temporary files
            for chunk_file in chunk_files:
                try:
                    os.remove(chunk_file)
                except:
                    pass
            
            logger.info(f"Chunked audio generated and concatenated: {output_path}")
            return str(output_path), audio_id
            
        except Exception as e:
            logger.error(f"Error generating chunked audio: {str(e)}")
            raise
    
    async def _concatenate_audio_files(self, file_paths: List[str], output_path: str) -> None:
        """Concatenate multiple audio files"""
        try:
            # Load all audio files
            waveforms = []
            sample_rate = None
            
            for file_path in file_paths:
                waveform, sr = torchaudio.load(file_path)
                if sample_rate is None:
                    sample_rate = sr
                elif sample_rate != sr:
                    # Resample if necessary
                    resampler = torchaudio.transforms.Resample(sr, sample_rate)
                    waveform = resampler(waveform)
                waveforms.append(waveform)
            
            # Concatenate all waveforms
            concatenated = torch.cat(waveforms, dim=1)
            
            # Save concatenated audio
            torchaudio.save(output_path, concatenated, sample_rate)
            
            logger.info(f"Concatenated {len(file_paths)} audio files")
            
        except Exception as e:
            logger.error(f"Error concatenating audio files: {str(e)}")
            raise
    
    def get_supported_languages(self) -> List[str]:
        """Return supported languages"""
        return ["es", "en", "pt"]
    
    async def cleanup_temp_files(self) -> None:
        """Clean up temporary files"""
        try:
            temp_dir = self.output_dir / "temp_chunks"
            if temp_dir.exists():
                for file in temp_dir.glob("*.wav"):
                    try:
                        file.unlink()
                    except:
                        pass
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {str(e)}")