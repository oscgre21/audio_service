"""
Punto de entrada principal de la aplicación mejorado con patrón Strategy
"""
import asyncio
import logging
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.container import Container
from src.config import get_settings
from src.workers import MessageConsumerWorker

# Configurar logging
def setup_logging(log_level: str, log_file: str):
    """Configura el sistema de logging"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file)
        ]
    )
    
    # Configurar niveles específicos para librerías externas
    logging.getLogger('pika').setLevel(logging.WARNING)
    logging.getLogger('pika.adapters').setLevel(logging.WARNING)
    logging.getLogger('pika.adapters.select_connection').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)


async def main():
    """Función principal con soporte para Strategy Pattern"""
    # Cargar configuración
    settings = get_settings()
    
    # Configurar logging
    setup_logging(settings.log_level, settings.log_file)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {settings.app_name} with Strategy Pattern")
    logger.info(f"Environment: {settings.environment}")
    
    # Configuración extendida con valores por defecto
    config_dict = {
        'rabbitmq': {
            'host': settings.rabbitmq.host,
            'port': settings.rabbitmq.port,
            'username': settings.rabbitmq.username,
            'password': settings.rabbitmq.password,
            'virtual_host': settings.rabbitmq.virtual_host,
            'exchange_name': settings.rabbitmq.exchange_name,
            'queue_prefix': settings.rabbitmq.queue_prefix
        },
        'audio': {
            'model_path': settings.audio.model_path,
            'tokenizer_path': settings.audio.tokenizer_path,
            'output_dir': settings.audio.output_dir,
            'device': settings.audio.device,
            'torch_seed': settings.audio.torch_seed,
            'max_new_tokens': settings.audio.max_new_tokens,
            'temperature': settings.audio.temperature,
            'top_p': settings.audio.top_p,
            'top_k': settings.audio.top_k,
            'max_chunk_length': settings.audio.max_chunk_length,
            'output_format': settings.audio.output_format,
            'mp3_bitrate': settings.audio.mp3_bitrate
        },
        'upload': {
            'url': settings.upload.url,
            'speech_upload_url': settings.upload.speech_upload_url,
            'word_upload_url': settings.upload.word_upload_url,
            'sentence_upload_url': settings.upload.sentence_upload_url,
            'custom_upload_url': settings.upload.custom_upload_url,
            'token': settings.upload.token,
            'max_retries': settings.upload.max_retries,
            'retry_delay': settings.upload.retry_delay,
            'timeout': settings.upload.timeout,
            'enabled': settings.upload.enabled
        },
        'queue': {
            'max_size': settings.queue.max_size,
            'concurrent_processors': settings.queue.concurrent_processors
        },
        'validation': {
            'min_text_length': settings.validation.min_text_length,
            'max_text_length': settings.validation.max_text_length
        },
        'post_processing': {
            'enable_notifications': settings.post_processing.enable_notifications,
            'enable_analytics': settings.post_processing.enable_analytics,
            'enable_cleanup': settings.post_processing.enable_cleanup,
            'webhook_url': settings.post_processing.webhook_url
        },
        'transcription': {
            'enabled': settings.transcription.enabled,
            'model': settings.transcription.model,
            'device': settings.transcription.device,
            'compute_type': settings.transcription.compute_type,
            'batch_size': settings.transcription.batch_size
        },
        'auth': {
            'url': settings.auth.url,
            'email': settings.auth.email,
            'password': settings.auth.password,
            'token_refresh_margin': settings.auth.token_refresh_margin
        },
        'word_processing': {
            'enabled': settings.word_processing.enabled,
            'max_concurrent_words': settings.word_processing.max_concurrent_words,
            'word_timeout': settings.word_processing.word_timeout
        },
        'llm': {
            'provider': settings.llm.provider,
            'base_url': settings.llm.base_url,
            'api_key': settings.llm.api_key,
            'model': settings.llm.model,
            'temperature': settings.llm.temperature,
            'max_tokens': settings.llm.max_tokens,
            'timeout': settings.llm.timeout,
            'ollama_model': settings.llm.ollama_model,
            'claude_api_key': settings.llm.claude_api_key,
            'claude_model': settings.llm.claude_model,
            'openai_api_key': settings.llm.openai_api_key,
            'openai_model': settings.llm.openai_model
        }
    }
    
    # Inicializar container DI
    container = Container()
    container.config.from_dict(config_dict)
    
    # Obtener configuración de procesadores concurrentes
    concurrent_processors = config_dict['queue']['concurrent_processors']
    
    # Crear worker mejorado con dependencias inyectadas
    worker = MessageConsumerWorker(
        message_queue=container.message_queue(),
        processing_queue=container.processing_queue(),
        orchestrator=container.strategy_orchestrator(),
        concurrent_processors=concurrent_processors
    )
    
    # Mostrar estrategias cargadas
    strategies = container.strategy_orchestrator().list_strategies()
    logger.info(f"Loaded {len(strategies)} processing strategies:")
    for strategy in strategies:
        logger.info(f"  - {strategy['name']} (order: {strategy['order']})")
    
    try:
        # Ejecutar worker
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await worker.stop()
        logger.info("Application stopped")


if __name__ == "__main__":
    asyncio.run(main())