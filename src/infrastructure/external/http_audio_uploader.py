"""
HTTP implementation of AudioUploader
"""
import os
import json
import logging
import asyncio
import time
from typing import Optional, Dict, Any

import aiohttp
import requests

from ...application.interfaces import AudioUploader, AuthService

logger = logging.getLogger(__name__)


class HttpAudioUploader(AudioUploader):
    """HTTP implementation for uploading audio files"""
    
    def __init__(
        self,
        base_url: str,
        speech_upload_url: str,
        word_upload_url: Optional[str] = None,
        token: str = "",
        max_retries: int = 3,
        retry_delay: int = 2,
        timeout: int = 30,
        enabled: bool = True,
        auth_service: Optional[AuthService] = None
    ):
        self.base_url = base_url  # Legacy support
        self.speech_upload_url = speech_upload_url  # New endpoint for speech
        self.word_upload_url = word_upload_url or base_url  # Endpoint for word uploads
        self.token = token  # Legacy token support
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.enabled = enabled
        self.auth_service = auth_service
    
    async def upload(
        self, 
        file_path: str, 
        speech_id: str, 
        audio_type: str = "main",
        metadata: Optional[Dict[str, Any]] = None,
        original_text: Optional[str] = None,
        language: Optional[str] = None,
        original_text_srt: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Upload audio file to server"""
        if not self.enabled:
            logger.info("Upload disabled in configuration")
            return None
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        # Prepare form data for new endpoint
        form_data = {
            'speech_uuid': speech_id,
            'audio_type': audio_type
        }
        
        # Add original_text if provided
        if original_text:
            form_data['original_text'] = original_text
        
        # Add language if provided
        if language:
            form_data['language'] = language
        
        # Add original_text_srt if provided
        if original_text_srt:
            form_data['original_text_srt'] = original_text_srt
        
        logger.info(f"original_text_srt: {original_text_srt}")

        # Add optional sequence_number for non-main types
        if audio_type in ['word', 'question', 'connector', 'sentence']:
            # Let the server auto-assign sequence number
            pass  # No need to add sequence_number
        
        # Add metadata if provided
        if metadata and len(metadata) > 0:
            # For word audio type, include word-specific metadata
            if audio_type == 'word':
                # Include word-specific metadata as separate form fields
                if 'word_index' in metadata:
                    form_data['word_index'] = metadata['word_index']
                if 'word_text' in metadata:
                    form_data['word_text'] = metadata['word_text']
                if 'parent_message_id' in metadata:
                    form_data['parent_message_id'] = metadata['parent_message_id']
                
                # Also include general audio metadata if available
                audio_metadata = {
                    'duration': metadata.get('duration'),
                    'size_bytes': metadata.get('size_bytes'),
                    'format': metadata.get('format', 'mp3'),
                    'sample_rate': metadata.get('sample_rate'),
                    'bitrate': metadata.get('bitrate')
                }
                # Remove None values
                audio_metadata = {k: v for k, v in audio_metadata.items() if v is not None}
                if audio_metadata:
                    form_data['metadata'] = json.dumps(audio_metadata)
            else:
                # For other audio types, only include audio-related metadata
                audio_metadata = {
                    'duration': metadata.get('duration'),
                    'size_bytes': metadata.get('size_bytes'),
                    'format': metadata.get('format', 'wav'),
                    'sample_rate': metadata.get('sample_rate'),
                    'bitrate': metadata.get('bitrate')
                }
                # Remove None values
                audio_metadata = {k: v for k, v in audio_metadata.items() if v is not None}
                if audio_metadata:
                    form_data['metadata'] = json.dumps(audio_metadata)
        
        # Get authentication token
        auth_token = self.token  # Default to legacy token
        if self.auth_service:
            try:
                # Get fresh token from auth service
                auth_token = await self.auth_service.get_access_token()
                logger.info("Using token from AuthService")
            except Exception as e:
                logger.warning(f"Failed to get token from AuthService: {str(e)}, using legacy token")
        
        # Headers
        headers = {
            'Authorization': f"Bearer {auth_token}"
        }
        
        # Try upload with retries
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Uploading file (attempt {attempt + 1}/{self.max_retries})...")
                logger.info(f"File path: {file_path}")
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                logger.info(f"File size: {file_size_mb:.2f} MB")
                
                # Determine MIME type based on file extension
                file_ext = os.path.splitext(file_path)[1].lower()
                mime_type = 'audio/mpeg' if file_ext == '.mp3' else 'audio/wav'
                
                # Use synchronous requests for now (can be converted to async later)
                with open(file_path, 'rb') as f:
                    files = {
                        'file': (os.path.basename(file_path), f, mime_type)
                    }
                    
                    # Use appropriate endpoint based on audio type
                    if audio_type == "main":
                        upload_url = self.speech_upload_url
                    elif audio_type == "word":
                        upload_url = self.word_upload_url
                    else:
                        upload_url = self.base_url
                    logger.info(f"Upload URL: {upload_url}")
                    logger.info(f"Upload type: {audio_type}")
                    logger.info(f"Speech ID: {speech_id}")
                    logger.info(f"Form data: {json.dumps(form_data, indent=2)}")
                    
                    start_time = time.time()
                    response = requests.post(
                        upload_url,
                        headers=headers,
                        data=form_data,
                        files=files,
                        timeout=self.timeout
                    )
                    upload_time = time.time() - start_time
                    logger.info(f"Upload request completed in {upload_time:.2f} seconds")
                
                logger.info(f"Response status code: {response.status_code}")
                
                if response.status_code == 201:
                    result = response.json()
                    logger.info(f"Upload successful!")
                    logger.info(f"Response data: {json.dumps(result, indent=2)}")
                    logger.info(f"File URL: {result.get('file_url', 'N/A')}")
                    logger.info(f"Audio UUID: {result.get('uuid', 'N/A')}")
                    return result
                elif response.status_code == 401:
                    logger.error("Authentication error - invalid or expired token")
                    logger.error(f"Response: {response.text}")
                    return None
                else:
                    logger.error(f"Upload failed: {response.status_code}")
                    logger.error(f"Response headers: {dict(response.headers)}")
                    logger.error(f"Response body: {response.text}")
                    
                    if attempt < self.max_retries - 1:
                        logger.info(f"Retrying in {self.retry_delay} seconds...")
                        await asyncio.sleep(self.retry_delay)
                        
            except Exception as e:
                logger.error(f"Upload error: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
        
        logger.error("Upload failed after all retries")
        return None
    
    def is_enabled(self) -> bool:
        """Check if upload is enabled"""
        return self.enabled
    
    async def validate_connection(self) -> bool:
        """Validate connection to server"""
        try:
            # Simple health check
            response = requests.get(
                self.base_url.replace('/upload', '/health'),
                timeout=5
            )
            return response.status_code == 200
        except:
            return False