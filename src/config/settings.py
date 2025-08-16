"""
Configuración central de la aplicación usando Pydantic
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class RabbitMQSettings(BaseSettings):
    """Configuración para RabbitMQ"""
    host: str = Field(default="rabbit.oscgre.com", env="RABBITMQ_HOST")
    port: int = Field(default=5672, env="RABBITMQ_PORT")
    username: str = Field(default="admin", env="RABBITMQ_USERNAME")
    password: str = Field(default="", env="RABBITMQ_PASSWORD")  # Empty default for testing
    virtual_host: str = Field(default="/", env="RABBITMQ_VHOST")
    exchange_name: str = Field(default="aloud_exchange", env="RABBITMQ_EXCHANGE")
    queue_prefix: str = Field(default="aloud_", env="RABBITMQ_QUEUE_PREFIX")
    
    class Config:
        env_prefix = "RABBITMQ_"


class AudioSettings(BaseSettings):
    """Configuración para generación de audio"""
    model_path: str = Field(
        default="bosonai/higgs-audio-v2-generation-3B-base",
        env="AUDIO_MODEL_PATH"
    )
    tokenizer_path: str = Field(
        default="bosonai/higgs-audio-v2-tokenizer",
        env="AUDIO_TOKENIZER_PATH"
    )
    output_dir: str = Field(default="generated_audio", env="AUDIO_OUTPUT_DIR")
    temp_dir: str = Field(default="generated_audio/temp_chunks", env="AUDIO_TEMP_DIR")
    max_chunk_length: int = Field(default=566, env="AUDIO_MAX_CHUNK_LENGTH")
    torch_seed: int = Field(default=42, env="AUDIO_TORCH_SEED")
    device: Optional[str] = Field(default=None, env="AUDIO_DEVICE")
    
    # Configuración de generación
    max_new_tokens: int = Field(default=1024, env="AUDIO_MAX_NEW_TOKENS")
    temperature: float = Field(default=0.3, env="AUDIO_TEMPERATURE")
    top_p: float = Field(default=0.95, env="AUDIO_TOP_P")
    top_k: int = Field(default=50, env="AUDIO_TOP_K")
    
    # Output format configuration
    output_format: str = Field(default="mp3", env="AUDIO_OUTPUT_FORMAT")
    mp3_bitrate: str = Field(default="128k", env="AUDIO_MP3_BITRATE")
    
    class Config:
        env_prefix = "AUDIO_"


class UploadSettings(BaseSettings):
    """Configuración para upload de archivos"""
    # URLs para diferentes tipos de upload
    speech_upload_url: str = Field(
        default="http://localhost:3000/audio/speech/upload", 
        env="SPEECH_UPLOAD_URL"
    )
    word_upload_url: str = Field(
        default="http://localhost:3000/audio/speech/upload", 
        env="WORD_UPLOAD_URL"
    )
    sentence_upload_url: str = Field(
        default="http://localhost:3000/audio/sentence/upload", 
        env="SENTENCE_UPLOAD_URL"
    )
    custom_upload_url: str = Field(
        default="http://localhost:3000/audio/custom/upload", 
        env="CUSTOM_UPLOAD_URL"
    )
    
    # URL legacy para compatibilidad
    url: str = Field(default="http://localhost:3000/audio/upload", env="UPLOAD_URL")
    
    # Configuración común
    token: str = Field(default="", env="UPLOAD_TOKEN")  # Empty default for testing
    max_retries: int = Field(default=3, env="UPLOAD_MAX_RETRIES")
    retry_delay: int = Field(default=2, env="UPLOAD_RETRY_DELAY")
    enabled: bool = Field(default=False, env="UPLOAD_ENABLED")  # Disabled by default
    timeout: int = Field(default=30, env="UPLOAD_TIMEOUT")
    
    class Config:
        env_prefix = "UPLOAD_"


class ProcessingQueueSettings(BaseSettings):
    """Configuración para la cola de procesamiento"""
    max_size: int = Field(default=1000, env="QUEUE_MAX_SIZE")
    concurrent_processors: int = Field(default=3, env="CONCURRENT_PROCESSORS")
    
    class Config:
        env_prefix = "QUEUE_"


class ValidationSettings(BaseSettings):
    """Configuración para la estrategia de validación"""
    min_text_length: int = Field(default=1, env="VALIDATION_MIN_TEXT_LENGTH")
    max_text_length: int = Field(default=10000, env="VALIDATION_MAX_TEXT_LENGTH")
    
    class Config:
        env_prefix = "VALIDATION_"


class PostProcessingSettings(BaseSettings):
    """Configuración para la estrategia de post-procesamiento"""
    enable_notifications: bool = Field(default=True, env="ENABLE_NOTIFICATIONS")
    enable_analytics: bool = Field(default=True, env="ENABLE_ANALYTICS")
    enable_cleanup: bool = Field(default=False, env="ENABLE_CLEANUP")
    webhook_url: Optional[str] = Field(default=None, env="WEBHOOK_URL")
    
    class Config:
        env_prefix = ""


class TranscriptionSettings(BaseSettings):
    """Configuración para el servicio de transcripción"""
    enabled: bool = Field(default=True, env="TRANSCRIPTION_ENABLED")
    model: str = Field(default="base", env="TRANSCRIPTION_MODEL")
    device: str = Field(default="cpu", env="TRANSCRIPTION_DEVICE")
    compute_type: str = Field(default="int8", env="TRANSCRIPTION_COMPUTE_TYPE")
    batch_size: int = Field(default=16, env="TRANSCRIPTION_BATCH_SIZE")
    
    class Config:
        env_prefix = "TRANSCRIPTION_"


class AuthSettings(BaseSettings):
    """Configuración para el servicio de autenticación"""
    url: str = Field(default="http://localhost:3000/auth/login", env="AUTH_URL")
    email: str = Field(default="admin@test.com", env="AUTH_EMAIL")
    password: str = Field(default="password123", env="AUTH_PASSWORD")
    token_refresh_margin: int = Field(default=300, env="AUTH_TOKEN_REFRESH_MARGIN")
    
    class Config:
        env_prefix = "AUTH_"


class LLMSettings(BaseSettings):
    """Configuración para el servicio de LLM"""
    provider: str = Field(default="ollama", env="LLM_PROVIDER")
    base_url: str = Field(default="https://llm.oscgre.com", env="LLM_BASE_URL")
    api_key: Optional[str] = Field(default=None, env="LLM_API_KEY")
    model: str = Field(default="llama3.1", env="LLM_MODEL")
    temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    max_tokens: int = Field(default=2000, env="LLM_MAX_TOKENS")
    timeout: int = Field(default=30, env="LLM_TIMEOUT")
    
    # Configuración específica por proveedor
    ollama_model: str = Field(default="llama3.1", env="OLLAMA_MODEL")
    claude_api_key: Optional[str] = Field(default=None, env="CLAUDE_API_KEY")
    claude_model: str = Field(default="claude-3-opus-20240229", env="CLAUDE_MODEL")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    
    class Config:
        env_prefix = "LLM_"


class WordProcessingSettings(BaseSettings):
    """Configuración para la estrategia de procesamiento de palabras"""
    enabled: bool = Field(default=True, env="WORD_PROCESSING_ENABLED")
    max_concurrent_words: int = Field(default=5, env="WORD_PROCESSING_MAX_CONCURRENT")
    word_timeout: float = Field(default=300.0, env="WORD_PROCESSING_TIMEOUT")
    
    class Config:
        env_prefix = "WORD_PROCESSING_"


class Settings(BaseSettings):
    """Configuración principal de la aplicación"""
    app_name: str = Field(default="higgs-audio-service", env="APP_NAME")
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="audio_processing.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"


def get_settings() -> Settings:
    """Factory para obtener la configuración"""
    settings = Settings()
    # Crear sub-configuraciones manualmente para evitar el error de validación
    settings.rabbitmq = RabbitMQSettings()
    settings.audio = AudioSettings()
    settings.upload = UploadSettings()
    settings.queue = ProcessingQueueSettings()
    settings.validation = ValidationSettings()
    settings.post_processing = PostProcessingSettings()
    settings.transcription = TranscriptionSettings()
    settings.auth = AuthSettings()
    settings.llm = LLMSettings()
    settings.word_processing = WordProcessingSettings()
    return settings