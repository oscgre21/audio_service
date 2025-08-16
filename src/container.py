"""
Container de inyección de dependencias mejorado con patrón Strategy
"""
from dependency_injector import containers, providers

from .config import get_settings
from .infrastructure.audio import HiggsAudioGenerator, SimpleTextChunker
from .infrastructure.storage import LocalFileStorage
from .infrastructure.external import HttpAudioUploader, HttpAuthService
from .infrastructure.messaging import RabbitMQConsumer
from .infrastructure.queues import InMemoryProcessingQueue
from .infrastructure.services import LocalVoiceReferenceService
from .infrastructure.transcription import WhisperXTranscriptionService
from .infrastructure.prompts import LocalPromptService
from .infrastructure.llm import LLMServiceImpl
from .application.services import AudioService, MetadataService
from .application.strategies import (
    SpeechProcessingStrategy,
    ValidationStrategy,
    PostProcessingStrategy,
    TranscriptionProcessingStrategy,
    WordProcessingStrategy
)
from .application.orchestrator import StrategyOrchestrator


class Container(containers.DeclarativeContainer):
    """Container principal de DI con soporte para Strategy Pattern"""
    
    # Configuración
    config = providers.Configuration()
    
    # Infrastructure - Storage
    file_storage = providers.Singleton(
        LocalFileStorage,
        base_path=config.audio.output_dir
    )
    
    # Infrastructure - Audio
    text_chunker = providers.Factory(
        SimpleTextChunker
    )
    
    audio_generator = providers.Singleton(
        HiggsAudioGenerator,
        model_path=config.audio.model_path,
        tokenizer_path=config.audio.tokenizer_path,
        output_dir=config.audio.output_dir,
        device=config.audio.device,
        torch_seed=config.audio.torch_seed,
        text_chunker=text_chunker,
        generation_config=providers.Dict({
            "max_new_tokens": config.audio.max_new_tokens,
            "temperature": config.audio.temperature,
            "top_p": config.audio.top_p,
            "top_k": config.audio.top_k
        }),
        output_format=config.audio.output_format,
        mp3_bitrate=config.audio.mp3_bitrate
    )
    
    # Infrastructure - External
    auth_service = providers.Singleton(
        HttpAuthService,
        auth_url=config.auth.url,
        email=config.auth.email,
        password=config.auth.password,
        token_refresh_margin=config.auth.token_refresh_margin,
        timeout=config.upload.timeout
    )
    
    audio_uploader = providers.Factory(
        HttpAudioUploader,
        base_url=config.upload.url,
        speech_upload_url=config.upload.speech_upload_url,
        word_upload_url=config.upload.word_upload_url,
        token=config.upload.token,
        max_retries=config.upload.max_retries,
        retry_delay=config.upload.retry_delay,
        timeout=config.upload.timeout,
        enabled=config.upload.enabled,
        auth_service=auth_service
    )
    
    # Infrastructure - Messaging
    message_queue = providers.Singleton(
        RabbitMQConsumer,
        host=config.rabbitmq.host,
        port=config.rabbitmq.port,
        username=config.rabbitmq.username,
        password=config.rabbitmq.password,
        virtual_host=config.rabbitmq.virtual_host,
        exchange_name=config.rabbitmq.exchange_name,
        queue_prefix=config.rabbitmq.queue_prefix
    )
    
    # Infrastructure - Processing Queue
    processing_queue = providers.Singleton(
        InMemoryProcessingQueue,
        max_size=config.queue.max_size
    )
    
    # Infrastructure - Voice Reference Service
    voice_reference_service = providers.Singleton(
        LocalVoiceReferenceService,
        default_character="belinda"
    )
    
    # Infrastructure - Transcription Service
    transcription_service = providers.Singleton(
        WhisperXTranscriptionService,
        model_name=config.transcription.model,
        device=config.transcription.device,
        compute_type=config.transcription.compute_type,
        batch_size=config.transcription.batch_size,
        words_per_subtitle=1  # Word-by-word timestamps
    )
    
    # Infrastructure - Prompt Service
    prompt_service = providers.Singleton(
        LocalPromptService
    )
    
    # Infrastructure - LLM Service
    llm_service = providers.Singleton(
        LLMServiceImpl,
        provider=config.llm.provider,
        config=providers.Dict({
            "base_url": config.llm.base_url,
            "api_key": config.llm.api_key,
            "model": config.llm.model,
            "timeout": config.llm.timeout,
            # Provider specific configs
            "ollama_model": config.llm.ollama_model,
            "claude_api_key": config.llm.claude_api_key,
            "claude_model": config.llm.claude_model,
            "openai_api_key": config.llm.openai_api_key,
            "openai_model": config.llm.openai_model
        }),
        prompt_service=prompt_service
    )
    
    # Application - Services
    audio_service = providers.Factory(
        AudioService,
        audio_generator=audio_generator,
        file_storage=file_storage
    )
    
    metadata_service = providers.Factory(
        MetadataService,
        file_storage=file_storage
    )
    
    # Application - Strategies
    validation_strategy = providers.Factory(
        ValidationStrategy,
        min_text_length=config.validation.min_text_length,
        max_text_length=config.validation.max_text_length
    )
    
    speech_processing_strategy = providers.Factory(
        SpeechProcessingStrategy,
        audio_generator=audio_generator,
        text_chunker=text_chunker,
        file_storage=file_storage,
        audio_uploader=audio_uploader,
        voice_reference_service=voice_reference_service,
        max_chunk_length=config.audio.max_chunk_length
    )
    
    transcription_processing_strategy = providers.Factory(
        TranscriptionProcessingStrategy,
        transcription_service=transcription_service,
        enabled=config.transcription.enabled
    )
    
    post_processing_strategy = providers.Factory(
        PostProcessingStrategy,
        enable_notifications=config.post_processing.enable_notifications,
        enable_analytics=config.post_processing.enable_analytics,
        enable_cleanup=config.post_processing.enable_cleanup,
        webhook_url=config.post_processing.webhook_url,
        audio_uploader=audio_uploader
    )
    
    word_processing_strategy = providers.Factory(
        WordProcessingStrategy,
        audio_generator=audio_generator,
        audio_uploader=audio_uploader,
        file_storage=file_storage,
        max_concurrent_words=config.word_processing.max_concurrent_words,
        word_timeout=config.word_processing.word_timeout,
        enable_word_processing=config.word_processing.enabled
    )
    
    # Application - Strategy Orchestrator
    strategy_orchestrator = providers.Factory(
        StrategyOrchestrator,
        strategies=providers.List(
            validation_strategy,
            speech_processing_strategy,
            transcription_processing_strategy,
            post_processing_strategy,
            word_processing_strategy
        )
    )
    
    # Application - Use Cases (eliminado - ahora usa SpeechProcessingStrategy)