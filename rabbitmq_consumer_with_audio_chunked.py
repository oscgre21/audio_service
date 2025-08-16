#!/usr/bin/env python3
"""
Consumidor de RabbitMQ con procesamiento de audio integrado
Divide textos largos en chunks y concatena los audios resultantes
"""
import pika
import json
import logging
import sys
import os
import queue
import threading
import time
import uuid
import re
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List

import torch
import torchaudio
import numpy as np
from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine, HiggsAudioResponse
from boson_multimodal.data_types import ChatMLSample, Message, AudioContent

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('audio_processing.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuración de conexión RabbitMQ
RABBITMQ_CONFIG = {
    'host': 'rabbit.oscgre.com',
    'port': 5672,
    'username': 'admin',
    'password': 'f4lyalt4',
    'virtual_host': '/'
}

# Configuración de exchange y colas
EXCHANGE_NAME = 'aloud_exchange'
QUEUE_PREFIX = 'aloud_'

# Configuración de Higgs Audio
MODEL_PATH = "bosonai/higgs-audio-v2-generation-3B-base"
AUDIO_TOKENIZER_PATH = "bosonai/higgs-audio-v2-tokenizer"
OUTPUT_DIR = "generated_audio"
TEMP_DIR = os.path.join(OUTPUT_DIR, "temp_chunks")

# Configuración de generación
GENERATION_CONFIG = {
    'max_new_tokens': 1024,
    'temperature': 0.3,
    'top_p': 0.95,
    'top_k': 50,
    'stop_strings': ["<|end_of_text|>", "<|eot_id|>"]
}

# Seed para reproducibilidad (ayuda a mantener consistencia de voz)
TORCH_SEED = 42

# Configuración del endpoint de upload
# IMPORTANTE: Actualiza el token si recibes error 401
UPLOAD_CONFIG = {
    'url': 'http://localhost:3000/audio/upload',
    'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImFkbWluQHRlc3QuY29tIiwic3ViIjoiZDQxYjMxYzItYWJhNi00YTNhLWJlYjgtODljNWYwMzM2ZDQ0Iiwicm9sZXMiOlsiYWRtaW4iXSwiaWF0IjoxNzU0ODgyODIyLCJleHAiOjE3NTQ5NjkyMjJ9.BIzyl8GLuHJGF-qbg58vNcGTGMJ2q4v5wVyTsY-wfgA',
    'max_retries': 3,
    'retry_delay': 2,
    'enabled': True  # Cambiar a False para deshabilitar uploads
}

# Configuración de chunks
MAX_CHUNK_LENGTH = 566


class TextChunker:
    """Divide texto en chunks sin cortar palabras"""
    
    @staticmethod
    def split_text_into_chunks(text: str, max_length: int = MAX_CHUNK_LENGTH) -> List[str]:
        """
        Divide el texto en chunks respetando límites de palabras
        """
        if len(text) <= max_length:
            return [text.strip()]
        
        chunks = []
        
        # Dividir primero por párrafos para mantener coherencia
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Si el párrafo es muy largo, dividirlo por oraciones
            if len(paragraph) > max_length:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                
                for sentence in sentences:
                    # Si una oración es más larga que max_length, dividirla por palabras
                    if len(sentence) > max_length:
                        words = sentence.split()
                        temp_chunk = ""
                        
                        for word in words:
                            if len(temp_chunk) + len(word) + 1 <= max_length:
                                temp_chunk = temp_chunk + " " + word if temp_chunk else word
                            else:
                                if temp_chunk:
                                    chunks.append(temp_chunk.strip())
                                temp_chunk = word
                        
                        if temp_chunk:
                            # Agregar al chunk actual si cabe
                            if len(current_chunk) + len(temp_chunk) + 1 <= max_length:
                                current_chunk = current_chunk + " " + temp_chunk if current_chunk else temp_chunk
                            else:
                                if current_chunk:
                                    chunks.append(current_chunk.strip())
                                current_chunk = temp_chunk
                    else:
                        # La oración cabe completa
                        if len(current_chunk) + len(sentence) + 1 <= max_length:
                            current_chunk = current_chunk + " " + sentence if current_chunk else sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = sentence
            else:
                # El párrafo cabe completo
                if len(current_chunk) + len(paragraph) + 2 <= max_length:  # +2 para "\n\n"
                    current_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph
        
        # Agregar el último chunk si existe
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Logging de información de chunks
        logger.info(f"Texto dividido en {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            logger.info(f"  Chunk {i+1}: {len(chunk)} caracteres")
        
        return chunks


class AudioProcessor:
    """Procesador de audio usando Higgs Audio Engine con soporte para chunks"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Inicializando AudioProcessor en dispositivo: {self.device}")
        
        try:
            # Establecer seed para reproducibilidad
            torch.manual_seed(TORCH_SEED)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(TORCH_SEED)
            
            self.serve_engine = HiggsAudioServeEngine(
                MODEL_PATH, 
                AUDIO_TOKENIZER_PATH, 
                device=self.device
            )
            logger.info("Higgs Audio Engine inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Higgs Audio Engine: {str(e)}")
            raise
        
        # Crear directorio temporal para chunks
        os.makedirs(TEMP_DIR, exist_ok=True)
    
    def generate_audio_chunked(self, text: str, language: str = "en") -> tuple[str, str]:
        """
        Genera audio a partir de texto, dividiéndolo en chunks si es necesario
        Returns: (audio_path, audio_id)
        """
        audio_id = str(uuid.uuid4())
        final_audio_path = os.path.join(OUTPUT_DIR, f"{audio_id}.wav")
        
        try:
            # Dividir texto en chunks
            chunks = TextChunker.split_text_into_chunks(text)
            
            if len(chunks) == 1:
                # Texto corto, generar directamente
                return self._generate_single_audio(text, language, audio_id, final_audio_path)
            else:
                # Texto largo, generar por chunks y concatenar
                return self._generate_and_concatenate_chunks(chunks, language, audio_id, final_audio_path)
                
        except Exception as e:
            logger.error(f"Error al generar audio: {str(e)}")
            raise
    
    def _generate_single_audio(self, text: str, language: str, audio_id: str, output_path: str) -> tuple[str, str]:
        """Genera un único audio sin chunks"""
        try:
            system_prompt = self._get_system_prompt(language)
            
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=text),
            ]
            
            logger.info(f"Generando audio único para texto de {len(text)} caracteres...")
            start_time = time.time()
            
            output: HiggsAudioResponse = self.serve_engine.generate(
                chat_ml_sample=ChatMLSample(messages=messages),
                **GENERATION_CONFIG
            )
            
            torchaudio.save(
                output_path, 
                torch.from_numpy(output.audio)[None, :], 
                output.sampling_rate
            )
            
            generation_time = time.time() - start_time
            logger.info(f"Audio generado exitosamente: {audio_id} (tiempo: {generation_time:.2f}s)")
            
            return output_path, audio_id
            
        except Exception as e:
            logger.error(f"Error al generar audio único: {str(e)}")
            raise
    
    def _generate_and_concatenate_chunks(self, chunks: List[str], language: str, audio_id: str, output_path: str) -> tuple[str, str]:
        """Genera audio por chunks y los concatena"""
        chunk_files = []
        chunk_audios = []
        sampling_rate = None
        
        try:
            # Usar el mismo prompt para todos los chunks para mantener consistencia de voz
            system_prompt = self._get_system_prompt(language)
            
            # Agregar contexto de continuidad para mantener la misma voz
            voice_context = "\n\n<|voice_consistency|>Maintain the same voice, tone, and speaking style throughout all parts.<|voice_consistency|>"
            
            # Generar audio para cada chunk
            for i, chunk in enumerate(chunks):
                logger.info(f"Procesando chunk {i+1}/{len(chunks)} ({len(chunk)} caracteres)...")
                
                # Para chunks después del primero, agregar contexto de continuidad
                if i > 0:
                    chunk_content = f"[Continuing from previous part] {chunk}"
                else:
                    chunk_content = chunk
                
                messages = [
                    Message(role="system", content=system_prompt + voice_context),
                    Message(role="user", content=chunk_content),
                ]
                
                start_time = time.time()
                
                # Usar configuración más determinística para mantener consistencia
                generation_config = GENERATION_CONFIG.copy()
                generation_config['temperature'] = 0.2  # Más determinístico
                generation_config['top_p'] = 0.9  # Menos variabilidad
                
                output: HiggsAudioResponse = self.serve_engine.generate(
                    chat_ml_sample=ChatMLSample(messages=messages),
                    **generation_config
                )
                
                # Guardar temporalmente
                chunk_path = os.path.join(TEMP_DIR, f"{audio_id}_chunk_{i}.wav")
                chunk_files.append(chunk_path)
                
                # Convertir a tensor para concatenación
                audio_tensor = torch.from_numpy(output.audio)
                chunk_audios.append(audio_tensor)
                
                # Guardar el sampling rate del primer chunk
                if sampling_rate is None:
                    sampling_rate = output.sampling_rate
                
                # Guardar chunk temporal
                torchaudio.save(chunk_path, audio_tensor[None, :], sampling_rate)
                
                generation_time = time.time() - start_time
                logger.info(f"  Chunk {i+1} generado en {generation_time:.2f}s")
            
            # Concatenar todos los audios
            logger.info("Concatenando chunks de audio...")
            
            # Agregar pequeño silencio entre chunks (0.05 segundos - más corto para mejor continuidad)
            silence_samples = int(0.05 * sampling_rate)
            silence = torch.zeros(silence_samples)
            
            # Construir audio final con silencios entre chunks
            final_audio_parts = []
            for i, audio in enumerate(chunk_audios):
                final_audio_parts.append(audio)
                if i < len(chunk_audios) - 1:  # No agregar silencio después del último chunk
                    final_audio_parts.append(silence)
            
            # Concatenar todas las partes
            final_audio = torch.cat(final_audio_parts)
            
            # Guardar audio final
            torchaudio.save(output_path, final_audio[None, :], sampling_rate)
            
            # Limpiar archivos temporales
            for chunk_file in chunk_files:
                try:
                    os.remove(chunk_file)
                except:
                    pass
            
            logger.info(f"Audio concatenado guardado: {output_path}")
            logger.info(f"Duración total: {len(final_audio) / sampling_rate:.2f} segundos")
            
            return output_path, audio_id
            
        except Exception as e:
            # Limpiar archivos temporales en caso de error
            for chunk_file in chunk_files:
                try:
                    os.remove(chunk_file)
                except:
                    pass
            logger.error(f"Error al generar/concatenar chunks: {str(e)}")
            raise
    
    def _get_system_prompt(self, language: str) -> str:
        """Obtiene el prompt del sistema según el idioma"""
        # Usar un prompt consistente con voz específica para mantener la misma voz
        prompts = {
            'es': "Genera audio siguiendo las instrucciones. El audio debe ser claro, en español, con voz femenina joven profesional.",
            'en': "Generate audio following instruction. The audio should be clear and natural, with a young professional female voice.",
            'pt': "Gere áudio seguindo as instruções. O áudio deve ser claro, em português, com voz feminina jovem profissional.",
        }
        return prompts.get(language, prompts['en'])


class AudioUploader:
    """Maneja la subida de archivos de audio al servidor"""
    
    @staticmethod
    def upload_audio_file(file_path: str, speech_uuid: str, audio_type: str = "main", 
                         metadata: Optional[Dict] = None) -> Optional[Dict]:
        """
        Sube un archivo de audio al endpoint
        Returns: Response data dict o None si falla
        """
        try:
            # Verificar que el archivo existe
            if not os.path.exists(file_path):
                logger.error(f"Archivo no encontrado: {file_path}")
                return None
            
            # Preparar los datos del formulario
            # IMPORTANTE: Los campos opcionales NO deben incluirse si no tienen valor
            form_data = {
                'speech_uuid': speech_uuid,
                'audio_type': audio_type
            }
            
            # NO incluir sequence_number para el tipo 'main'
            # Solo agregar para otros tipos como 'word', 'question', etc.
            if audio_type in ['word', 'question', 'connector', 'sentence']:
                form_data['sequence_number'] = '0'
            
            # Solo agregar metadata si existe y tiene contenido
            if metadata and len(metadata) > 0:
                form_data['metadata'] = json.dumps(metadata)
            
            # Preparar el archivo
            with open(file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(file_path), f, 'audio/wav')
                }
                
                # Headers con autorización
                headers = {
                    'Authorization': f"Bearer {UPLOAD_CONFIG['token']}"
                }
                
                # Realizar la petición con reintentos
                for attempt in range(UPLOAD_CONFIG['max_retries']):
                    try:
                        logger.info(f"Subiendo archivo al servidor (intento {attempt + 1}/{UPLOAD_CONFIG['max_retries']})...")
                        
                        # Los datos del formulario deben enviarse exactamente como en los ejemplos curl
                        # Importante: NO modificar form_data, usar como está
                        
                        response = requests.post(
                            UPLOAD_CONFIG['url'],
                            headers=headers,
                            data=form_data,  # Usar form_data original
                            files=files,
                            timeout=30
                        )
                        
                        if response.status_code == 201:
                            result = response.json()
                            logger.info(f"✅ Audio subido exitosamente")
                            logger.info(f"   UUID: {result.get('uuid')}")
                            logger.info(f"   URL: {result.get('file_url')}")
                            return result
                        elif response.status_code == 401:
                            logger.error(f"Error de autenticación (401): Token inválido o expirado")
                            logger.error(f"Por favor actualiza el token en UPLOAD_CONFIG['token']")
                            return None  # No reintentar si es error de autenticación
                        elif response.status_code == 400:
                            logger.error(f"Error de validación (400): {response.text}")
                            # Intentar parsear el error para dar más detalles
                            try:
                                error_data = response.json()
                                if 'message' in error_data:
                                    logger.error(f"Detalles: {error_data['message']}")
                                    # Si el error es sobre el speech_uuid, informar al usuario
                                    if 'Failed to create audio file' in str(error_data.get('message')):
                                        logger.error(f"Posible causa: El speech_uuid '{speech_uuid}' no existe en el servidor")
                                        logger.error(f"Verifica que el speech exista antes de subir el audio")
                            except:
                                pass
                            if attempt < UPLOAD_CONFIG['max_retries'] - 1:
                                time.sleep(UPLOAD_CONFIG['retry_delay'])
                        else:
                            logger.error(f"Error en upload: {response.status_code} - {response.text}")
                            if attempt < UPLOAD_CONFIG['max_retries'] - 1:
                                time.sleep(UPLOAD_CONFIG['retry_delay'])
                            
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Error de conexión: {str(e)}")
                        if attempt < UPLOAD_CONFIG['max_retries'] - 1:
                            time.sleep(UPLOAD_CONFIG['retry_delay'])
                
                logger.error("Falló la subida después de todos los reintentos")
                return None
                
        except Exception as e:
            logger.error(f"Error al subir archivo: {str(e)}")
            return None


class SpeechCreatedConsumerWithAudio:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.processing_queue = queue.Queue()
        self.audio_processor = None
        self.worker_thread = None
        self.should_stop = False
        
    def connect(self):
        """Establecer conexión con RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(
                RABBITMQ_CONFIG['username'],
                RABBITMQ_CONFIG['password']
            )
            
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_CONFIG['host'],
                port=RABBITMQ_CONFIG['port'],
                virtual_host=RABBITMQ_CONFIG['virtual_host'],
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            logger.info(f"Conectando a RabbitMQ en {RABBITMQ_CONFIG['host']}:{RABBITMQ_CONFIG['port']}")
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declarar el exchange
            self.channel.exchange_declare(
                exchange=EXCHANGE_NAME,
                exchange_type='topic',
                durable=True
            )
            
            # Crear una cola exclusiva para este consumidor
            result = self.channel.queue_declare(
                queue='', 
                exclusive=True,
                durable=True
            )
            self.queue_name = result.method.queue
            
            # Bind la cola al exchange
            self.channel.queue_bind(
                exchange=EXCHANGE_NAME,
                queue=self.queue_name,
                routing_key='speech.created'
            )
            
            logger.info(f"Conectado exitosamente a RabbitMQ")
            logger.info(f"Cola creada: {self.queue_name}")
            
        except Exception as e:
            logger.error(f"Error al conectar con RabbitMQ: {str(e)}")
            raise
    
    def process_message(self, ch, method, properties, body):
        """Procesar mensaje recibido de RabbitMQ"""
        try:
            # Decodificar el mensaje
            message = json.loads(body)
            
            # Extraer información relevante
            message_id = message.get('id')
            data = message.get('data', {})
            speech_dto = data.get('speechDto', {})
            
            # Preparar item para la cola de procesamiento
            processing_item = {
                'message_id': message_id,
                'speech_id': data.get('speechId'),
                'original_text': speech_dto.get('original_text', ''),
                'language': speech_dto.get('language', 'en'),
                'timestamp': message.get('timestamp'),
                'speech_dto': speech_dto
            }
            
            # Validar que hay texto para procesar
            if not processing_item['original_text']:
                logger.warning(f"Mensaje sin texto para procesar: {message_id}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Agregar a la cola de procesamiento
            self.processing_queue.put(processing_item)
            logger.info(f"Mensaje agregado a cola de procesamiento: {message_id}")
            logger.info(f"Longitud del texto: {len(processing_item['original_text'])} caracteres")
            logger.info(f"Tamaño de cola: {self.processing_queue.qsize()}")
            
            # Acknowledge el mensaje
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except json.JSONDecodeError as e:
            logger.error(f"Error al decodificar JSON: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def audio_worker(self):
        """Worker thread que procesa la cola de audio"""
        logger.info("Worker de audio iniciado")
        
        # Inicializar el procesador de audio
        try:
            self.audio_processor = AudioProcessor()
        except Exception as e:
            logger.error(f"Error fatal al inicializar AudioProcessor: {str(e)}")
            return
        
        while not self.should_stop:
            try:
                # Obtener item de la cola (timeout de 1 segundo)
                try:
                    item = self.processing_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                logger.info("="*60)
                logger.info(f"Procesando audio para mensaje: {item['message_id']}")
                logger.info(f"Speech ID: {item['speech_id']}")
                logger.info(f"Idioma: {item['language']}")
                logger.info(f"Longitud del texto: {len(item['original_text'])} caracteres")
                
                # Determinar si necesitará chunks
                will_chunk = len(item['original_text']) > MAX_CHUNK_LENGTH
                if will_chunk:
                    logger.info(f"⚠️  El texto excede {MAX_CHUNK_LENGTH} caracteres, se dividirá en chunks")
                
                # Generar audio (con chunks si es necesario)
                try:
                    audio_path, audio_id = self.audio_processor.generate_audio_chunked(
                        text=item['original_text'],
                        language=item['language']
                    )
                    
                    logger.info(f"✅ Audio generado exitosamente")
                    logger.info(f"   ID: {audio_id}")
                    logger.info(f"   Archivo: {audio_path}")
                    
                    # Obtener información del archivo
                    if os.path.exists(audio_path):
                        file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
                        logger.info(f"   Tamaño: {file_size:.2f} MB")
                    
                    # Guardar metadata
                    self._save_metadata(audio_id, item)
                    
                    # Subir audio al servidor
                    logger.info("-" * 40)
                    logger.info("📤 Subiendo audio al servidor...")
                    
                    # Preparar metadata para el upload (opcional, puede causar problemas)
                    # Por ahora, no enviar metadata para evitar errores de validación
                    upload_metadata = None
                    
                    # Si quieres habilitar metadata, descomenta esto:
                    # upload_metadata = {
                    #     'original_text': item['original_text'][:500],
                    #     'language': item['language'],
                    #     'text_length': len(item['original_text']),
                    #     'was_chunked': len(item['original_text']) > MAX_CHUNK_LENGTH,
                    #     'generation_time': datetime.now().isoformat(),
                    #     'message_id': item['message_id'],
                    #     'audio_generator': 'higgs-audio-v2'
                    # }
                    
                    # Solo intentar upload si está habilitado
                    if UPLOAD_CONFIG.get('enabled', True):
                        upload_result = AudioUploader.upload_audio_file(
                            file_path=audio_path,
                            speech_uuid=item['speech_id'],
                            audio_type='main',
                            metadata=upload_metadata
                        )
                    else:
                        logger.info("⚠️  Upload deshabilitado en configuración")
                        upload_result = None
                    
                    if upload_result:
                        logger.info(f"✅ Audio subido correctamente al servidor")
                        logger.info(f"   Accesible en: {upload_result.get('file_url')}")
                        
                        # Actualizar metadata local con info del upload
                        self._update_metadata_with_upload(audio_id, upload_result)
                    else:
                        logger.error("❌ Falló la subida del audio al servidor")
                        # El archivo local permanece disponible
                    
                except Exception as e:
                    logger.error(f"Error al generar audio: {str(e)}")
                    # TODO: Implementar reintentos si es necesario
                
                logger.info("="*60 + "\n")
                
            except Exception as e:
                logger.error(f"Error en worker de audio: {str(e)}")
                time.sleep(1)  # Pausa antes de continuar
        
        logger.info("Worker de audio detenido")
    
    def _save_metadata(self, audio_id: str, item: Dict[str, Any]):
        """Guarda metadata del audio generado"""
        try:
            metadata = {
                'audio_id': audio_id,
                'message_id': item['message_id'],
                'speech_id': item['speech_id'],
                'language': item['language'],
                'original_text': item['original_text'],
                'text_length': len(item['original_text']),
                'was_chunked': len(item['original_text']) > MAX_CHUNK_LENGTH,
                'generated_at': datetime.now().isoformat(),
                'speech_name': item['speech_dto'].get('name'),
                'user_uuid': item['speech_dto'].get('user_uuid')
            }
            
            metadata_path = os.path.join(OUTPUT_DIR, f"{audio_id}.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Metadata guardada: {metadata_path}")
            
        except Exception as e:
            logger.error(f"Error al guardar metadata: {str(e)}")
    
    def _update_metadata_with_upload(self, audio_id: str, upload_result: Dict[str, Any]):
        """Actualiza la metadata local con información del upload"""
        try:
            metadata_path = os.path.join(OUTPUT_DIR, f"{audio_id}.json")
            
            # Leer metadata existente
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Agregar información del upload
            metadata['upload_result'] = {
                'uploaded': True,
                'upload_time': datetime.now().isoformat(),
                'server_uuid': upload_result.get('uuid'),
                'server_url': upload_result.get('file_url'),
                'server_path': upload_result.get('file_path')
            }
            
            # Guardar metadata actualizada
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Metadata actualizada con info de upload")
            
        except Exception as e:
            logger.error(f"Error al actualizar metadata con upload: {str(e)}")
    
    def start(self):
        """Iniciar el consumidor y el worker"""
        try:
            # Conectar a RabbitMQ
            self.connect()
            
            # Iniciar worker thread
            self.worker_thread = threading.Thread(target=self.audio_worker, daemon=True)
            self.worker_thread.start()
            logger.info("Worker thread iniciado")
            
            # Configurar consumo
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.process_message,
                auto_ack=False
            )
            
            logger.info("Iniciando consumo de mensajes...")
            logger.info(f"Configuración de chunks: máximo {MAX_CHUNK_LENGTH} caracteres por chunk")
            logger.info("Presiona CTRL+C para detener")
            logger.info("-"*60)
            
            # Iniciar consumo
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("\nDeteniendo consumidor...")
            self.stop()
        except Exception as e:
            logger.error(f"Error fatal: {str(e)}")
            self.stop()
            raise
    
    def stop(self):
        """Detener el consumidor y limpiar recursos"""
        logger.info("Iniciando proceso de detención...")
        
        # Señalar al worker que debe detenerse
        self.should_stop = True
        
        # Detener consumo de RabbitMQ
        if self.channel and not self.channel.is_closed:
            try:
                self.channel.stop_consuming()
            except:
                pass
        
        # Esperar a que el worker termine
        if self.worker_thread and self.worker_thread.is_alive():
            logger.info("Esperando a que el worker termine...")
            self.worker_thread.join(timeout=5)
        
        # Cerrar conexiones
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except:
            pass
        
        logger.info("Consumidor detenido correctamente")
        logger.info(f"Mensajes pendientes en cola: {self.processing_queue.qsize()}")


def main():
    """Función principal"""
    logger.info("Iniciando consumidor de RabbitMQ con procesamiento de audio (con chunks)")
    logger.info(f"Configuración RabbitMQ: {RABBITMQ_CONFIG['host']}:{RABBITMQ_CONFIG['port']}")
    logger.info(f"Configuración Upload: {UPLOAD_CONFIG['url']}")
    logger.info(f"Directorio de salida: {OUTPUT_DIR}")
    logger.info(f"Tamaño máximo de chunk: {MAX_CHUNK_LENGTH} caracteres")
    
    # Crear directorios necesarios
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Crear y ejecutar consumidor
    consumer = SpeechCreatedConsumerWithAudio()
    
    try:
        consumer.start()
    except Exception as e:
        logger.error(f"Error al ejecutar consumidor: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())