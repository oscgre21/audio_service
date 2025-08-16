# Flujo de Componentes - Higgs Audio Service

Este documento describe el flujo de componentes y la comunicación entre los diferentes módulos del sistema con el patrón Strategy implementado.

## Diagrama de Flujo Principal con Patrón Strategy

```mermaid
graph TB
    %% External Systems
    RMQ[RabbitMQ<br/>rabbit.oscgre.com:5672]
    API[API Server<br/>localhost:3000]
    
    %% Entry Points
    MAIN[main.py<br/>Entry Point]
    
    %% Workers & Queue
    WORKER[MessageConsumerWorker<br/>Message Processing Orchestrator]
    QUEUE[InMemoryProcessingQueue<br/>FIFO Queue with Priority]
    
    %% Strategy Pattern Components
    ORCHESTRATOR[StrategyOrchestrator<br/>Strategy Coordinator]
    VAL_STRATEGY[ValidationStrategy<br/>Order: 10]
    SPEECH_STRATEGY[SpeechProcessingStrategy<br/>Order: 100]
    TRANS_STRATEGY[TranscriptionProcessingStrategy<br/>Order: 150]
    POST_STRATEGY[PostProcessingStrategy<br/>Order: 200]
    WORD_STRATEGY[WordProcessingStrategy<br/>Order: 250]
    
    %% Infrastructure Layer
    RMQC[RabbitMQConsumer<br/>Message Queue Consumer]
    HIGGS[HiggsAudioGenerator<br/>TTS Engine MPS/CUDA/CPU]
    CHUNKER[SimpleTextChunker<br/>Text Splitter]
    STORAGE[LocalFileStorage<br/>File & Metadata]
    UPLOADER[HttpAudioUploader<br/>HTTP Client]
    VOICEREF[VoiceReferenceService<br/>Character Voice Manager]
    WHISPERX[WhisperXTranscriptionService<br/>Word-level Transcription]
    AUTH[HttpAuthService<br/>Authentication Service]
    
    %% LLM Services (NEW)
    LLM[LLMService<br/>AI Language Model]
    PROMPT[PromptService<br/>Template Manager]
    
    %% Domain Entities
    MSG[Message Entity<br/>+ retry_count]
    SPEECH[Speech Entity]
    AUDIO[Audio Entity]
    
    %% Flow
    RMQ -->|AMQP| RMQC
    MAIN -->|Initializes| WORKER
    WORKER -->|Consumes| RMQC
    RMQC -->|Message| QUEUE
    QUEUE -->|Dequeue FIFO| WORKER
    WORKER -->|Process| ORCHESTRATOR
    
    %% Strategy Flow
    ORCHESTRATOR -->|1st| VAL_STRATEGY
    ORCHESTRATOR -->|2nd| SPEECH_STRATEGY
    ORCHESTRATOR -->|3rd| TRANS_STRATEGY
    ORCHESTRATOR -->|4th| POST_STRATEGY
    ORCHESTRATOR -->|5th| WORD_STRATEGY
    
    %% Speech Processing Strategy Flow
    SPEECH_STRATEGY -->|Extract| SPEECH
    SPEECH_STRATEGY -->|Get Voice| VOICEREF
    VOICEREF -->|Voice Path| SPEECH_STRATEGY
    SPEECH_STRATEGY -->|Check Length| CHUNKER
    SPEECH_STRATEGY -->|Generate| HIGGS
    HIGGS -->|WAV File| AUDIO
    HIGGS -->|Save| STORAGE
    
    %% Transcription Processing Strategy Flow
    TRANS_STRATEGY -->|Read Audio| AUDIO
    TRANS_STRATEGY -->|Transcribe| WHISPERX
    WHISPERX -->|Word-level SRT| TRANS_STRATEGY
    
    %% Post Processing Strategy Flow
    POST_STRATEGY -->|Check Transcription| POST_STRATEGY
    POST_STRATEGY -->|Upload with Word-level SRT| UPLOADER
    UPLOADER -->|Get Token| AUTH
    AUTH -->|Access Token| UPLOADER
    UPLOADER -->|HTTP POST| API
    
    %% Word Processing Strategy Flow
    WORD_STRATEGY -->|Extract Text| SPEECH
    WORD_STRATEGY -->|Split Words| WORD_STRATEGY
    WORD_STRATEGY -->|For Each Word| HIGGS
    WORD_STRATEGY -->|Generate Word Audio| AUDIO
    WORD_STRATEGY -->|Upload Each Word| UPLOADER
    UPLOADER -->|audio_type=word| WORD_URL
    
    %% LLM Integration (Available for all strategies)
    VAL_STRATEGY -.->|Future Use| LLM
    SPEECH_STRATEGY -.->|Future Use| LLM
    TRANS_STRATEGY -.->|Future Use| LLM
    POST_STRATEGY -.->|Future Use| LLM
    WORD_STRATEGY -.->|Future Use| LLM
    LLM -->|Get Templates| PROMPT
    
    %% Styling
    classDef external fill:#f9f,stroke:#333,stroke-width:2px
    classDef infra fill:#bbf,stroke:#333,stroke-width:2px
    classDef app fill:#bfb,stroke:#333,stroke-width:2px
    classDef strategy fill:#fbb,stroke:#333,stroke-width:3px
    classDef domain fill:#ffd,stroke:#333,stroke-width:2px
    classDef service fill:#fcf,stroke:#333,stroke-width:2px
    classDef llm fill:#9f9,stroke:#333,stroke-width:3px
    
    class RMQ,API external
    class RMQC,HIGGS,CHUNKER,STORAGE,UPLOADER,WHISPERX,AUTH infra
    class VOICEREF service
    class WORKER,QUEUE app
    class ORCHESTRATOR,VAL_STRATEGY,SPEECH_STRATEGY,TRANS_STRATEGY,POST_STRATEGY,WORD_STRATEGY strategy
    class MSG,SPEECH,AUDIO domain
    class LLM,PROMPT llm
```

## Flujo Detallado de Procesamiento con Patrón Strategy

```mermaid
sequenceDiagram
    participant RMQ as RabbitMQ
    participant Consumer as RabbitMQConsumer
    participant Queue as ProcessingQueue
    participant Worker as MessageConsumerWorker
    participant Orch as StrategyOrchestrator
    participant Val as ValidationStrategy
    participant Speech as SpeechProcessingStrategy
    participant Trans as TranscriptionProcessingStrategy
    participant Post as PostProcessingStrategy
    participant Voice as VoiceReferenceService
    participant Higgs as HiggsAudioGenerator
    participant WhisperX as WhisperXTranscriptionService
    participant Storage as LocalFileStorage
    participant Auth as HttpAuthService
    participant Uploader as HttpAudioUploader
    participant API as API Server

    RMQ->>Consumer: New Message
    Consumer->>Queue: enqueue(message, priority)
    
    loop Concurrent Processors (3)
        Worker->>Queue: dequeue()
        Queue-->>Worker: QueuedMessage
        Worker->>Orch: process(message)
        
        %% Validation Strategy
        Orch->>Val: execute(message, context)
        Val->>Val: Validate structure
        Val->>Val: Validate language
        Val->>Val: Security checks
        Val-->>Orch: StrategyResult(success=true)
        
        %% Speech Processing Strategy
        Orch->>Speech: execute(message, context)
        Speech->>Speech: Extract Speech entity
        Speech->>Speech: Extract character from DTO
        
        alt Character provided
            Speech->>Voice: get_voice_path(character)
            Voice-->>Speech: reference_audio_path
        end
        
        alt Text > 566 chars
            Speech->>Higgs: generate_chunked(chunks, language, ref_audio)
            Higgs->>Higgs: Process with timeout
        else Text <= 566 chars
            Speech->>Higgs: generate(text, language, ref_audio)
            Higgs->>Higgs: Process with timeout
        end
        
        Higgs->>Storage: save final.wav
        Higgs-->>Speech: file_path, audio_id
        Speech->>Storage: save_metadata()
        Speech->>Speech: Generate basic SRT
        Speech->>Speech: Set context['uploaded'] = False
        Speech-->>Orch: StrategyResult(success=true)
        
        %% Transcription Processing Strategy
        alt Transcription Enabled
            Orch->>Trans: execute(message, context)
            Trans->>Trans: Get audio from context
            Trans->>WhisperX: transcribe_with_alignment(audio_path)
            WhisperX->>WhisperX: Load Whisper model
            WhisperX->>WhisperX: VAD with Silero
            WhisperX->>WhisperX: Word alignment with wav2vec2
            WhisperX-->>Trans: Word-level SRT
            Trans->>Trans: Update context with SRT
            Trans-->>Orch: StrategyResult(success=true)
        end
        
        %% Post Processing Strategy
        Orch->>Post: execute(message, context)
        alt Upload Enabled
            alt Transcription Completed with Word-level SRT
                Post->>Post: Verify transcription_completed = true
                Post->>Post: Verify transcription_srt exists
                Post->>Uploader: upload(file_path, word_level_srt)
                Uploader->>Auth: get_access_token()
                Auth->>Auth: Check token validity
                alt Token Invalid or Expired
                    Auth->>API: POST /auth/login
                    API-->>Auth: {access_token, refresh_token}
                end
                Auth-->>Uploader: access_token
                Uploader->>API: POST /audio/speech/upload
                API-->>Uploader: {uuid, file_url}
                Post->>Storage: update metadata
            else Transcription Not Ready
                Post->>Post: Log "Skipping upload - waiting for word-level transcription"
                Post->>Post: Set upload result = waiting_for_transcription
            end
        end
        Post-->>Orch: StrategyResult(success=true)
        
        %% Word Processing Strategy
        Orch->>Word as WordProcessingStrategy: execute(message, context)
        Word->>Word: Extract original_text
        Word->>Word: Split into words
        loop For Each Word
            Word->>Higgs: generate(word, language, ref_audio)
            Higgs-->>Word: word_audio_file
            Word->>Uploader: upload(file_path, audio_type="word")
            Uploader->>API: POST /audio/speech/upload
            API-->>Uploader: {uuid, file_url}
        end
        Word-->>Orch: StrategyResult(success=true)
        
        Orch-->>Worker: OrchestratorResult
    end
```

## Flujo de Datos de Mensaje

```mermaid
graph LR
    subgraph "Mensaje RabbitMQ"
        RAW[Raw Message]
        RAW --> PARSED[Parsed JSON]
        PARSED --> ID[id: string]
        PARSED --> DATA[data]
        DATA --> SPEECHDTO[speechDto]
        SPEECHDTO --> TEXT[original_text]
        SPEECHDTO --> LANG[language]
        SPEECHDTO --> USERID[user_uuid]
        SPEECHDTO --> NAME[name]
        SPEECHDTO --> CHAR[character]
    end
    
    subgraph "Entidades de Dominio"
        MESSAGE[Message Entity<br/>- id<br/>- event_type<br/>- data]
        SPEECH_ENT[Speech Entity<br/>- id<br/>- user_id<br/>- language<br/>- original_text]
        AUDIO_ENT[Audio Entity<br/>- id<br/>- speech_id<br/>- file_path<br/>- was_chunked]
    end
    
    PARSED --> MESSAGE
    SPEECHDTO --> SPEECH_ENT
    SPEECH_ENT --> AUDIO_ENT
```

## Configuración de Upload Endpoints

```mermaid
graph TD
    subgraph "Configuración de URLs"
        ENV[.env file]
        ENV --> SPEECH_URL[SPEECH_UPLOAD_URL<br/>/audio/speech/upload]
        ENV --> WORD_URL[WORD_UPLOAD_URL<br/>/audio/speech/upload]
        ENV --> SENTENCE_URL[SENTENCE_UPLOAD_URL<br/>/audio/sentence/upload]
        ENV --> CUSTOM_URL[CUSTOM_UPLOAD_URL<br/>/audio/custom/upload]
    end
    
    subgraph "Uso en HttpAudioUploader"
        UPLOADER[HttpAudioUploader]
        UPLOADER -->|audio_type=main| SPEECH_URL
        UPLOADER -->|audio_type=word| WORD_URL
        UPLOADER -->|audio_type=sentence| SENTENCE_URL
        UPLOADER -->|audio_type=custom| CUSTOM_URL
    end
```

## Componentes Principales con Patrón Strategy

### 1. **main.py**
- Punto de entrada de la aplicación
- Configura el logging
- Inicializa el contenedor de dependencias con configuración extendida
- Crea y ejecuta el MessageConsumerWorker con procesadores concurrentes

### 2. **MessageConsumerWorker** (Mejorado)
- Separa consumo de RabbitMQ del procesamiento
- Maneja una cola interna FIFO con prioridades
- Ejecuta múltiples procesadores concurrentes (3 por defecto)
- Graceful shutdown con procesamiento de mensajes pendientes
- Estadísticas en tiempo real

### 3. **InMemoryProcessingQueue**
- Cola FIFO con soporte de prioridades (CRITICAL, HIGH, NORMAL, LOW)
- Thread-safe con asyncio
- Estadísticas de cola
- Soporte para requeue con reintentos

### 4. **StrategyOrchestrator**
- Coordina la ejecución de estrategias en orden
- Maneja contexto compartido entre estrategias
- Control de flujo (continuar, parar, saltar)
- Inicialización y limpieza de estrategias

### 5. **Estrategias Implementadas**

#### Orden de Ejecución de Estrategias

| Estrategia | Orden | Descripción |
|------------|-------|-------------|
| ValidationStrategy | 10 | Validación inicial del mensaje |
| SpeechProcessingStrategy | 100 | Generación del audio principal |
| TranscriptionProcessingStrategy | 150 | Transcripción palabra por palabra |
| PostProcessingStrategy | 200 | Upload del audio principal con SRT |
| WordProcessingStrategy | 250 | Procesamiento y upload palabra por palabra |

#### ValidationStrategy (Orden: 10)
- Valida estructura del mensaje
- Verifica campos requeridos
- Valida idiomas soportados
- Controles de seguridad
- Validación de longitud de texto

#### SpeechProcessingStrategy (Orden: 100)
- Refactorización de ProcessSpeechMessageUseCase
- Extrae datos del mensaje incluyendo campo 'character'
- Resuelve voz de referencia usando VoiceReferenceService
- Genera audio con timeout y voz específica
- Maneja chunking para textos largos
- Guarda metadata
- Genera SRT básico (no realiza upload)
- Marca context['uploaded'] = False

#### TranscriptionProcessingStrategy (Orden: 150)
- Transcripción automática del audio generado
- Usa WhisperX con Silero VAD para detección de voz
- Alineación palabra por palabra con wav2vec2.0
- Genera SRT con timestamps precisos por palabra
- Configurable: puede activarse/desactivarse
- No bloquea el flujo si falla

#### PostProcessingStrategy (Orden: 200)
- Upload SOLO cuando transcripción está completa
- Verifica transcription_completed y transcription_srt
- Si transcripción no está lista: skip upload con log "waiting for word-level transcription"
- Solo sube audio con SRT palabra por palabra (nunca con SRT básico)
- Notificaciones (configurable)
- Analytics (configurable)
- Limpieza de archivos temporales (configurable)

#### WordProcessingStrategy (Orden: 250)
- Procesa el texto original palabra por palabra
- Extrae original_text del contexto
- Divide el texto en palabras individuales
- Para cada palabra:
  - Genera audio usando HiggsAudioGenerator
  - Usa la misma voz de referencia del audio principal
  - Sube el audio con audio_type="word"
- Procesamiento concurrente con límite configurable
- Timeout por palabra configurable
- No bloquea el flujo si falla

### 6. **HiggsAudioGenerator** (Mejorado)
- Detección automática de dispositivo (MPS/CUDA/CPU)
- Generación asíncrona con thread pool
- Timeouts configurables
- Soporte para chunking y concatenación
- Soporte para audio de referencia (voice cloning)
- Integración con AudioContent para referencias de voz

### 7. **Configuración Extendida**
- ProcessingQueueSettings: max_size, concurrent_processors
- ValidationSettings: min/max_text_length
- PostProcessingSettings: notifications, analytics, cleanup, webhook
- TranscriptionSettings: enabled, model, device, compute_type, batch_size
- AuthSettings: url, email, password, token_refresh_margin
- LLMSettings: provider, base_url, api_key, model, temperature, max_tokens

## Flujo de Procesamiento Palabra por Palabra

```mermaid
graph TD
    subgraph "Word Processing Strategy Detail"
        WPS_START[WordProcessingStrategy Start]
        CHECK_AUDIO{Audio Generated?}
        CHECK_UPLOAD{Uploader Enabled?}
        EXTRACT[Extract original_text]
        SPLIT[Split into words]
        PROCESS[Process Words Concurrently]
        
        WPS_START --> CHECK_AUDIO
        CHECK_AUDIO -->|No| SKIP_WPS[Skip Processing]
        CHECK_AUDIO -->|Yes| CHECK_UPLOAD
        CHECK_UPLOAD -->|No| SKIP_WPS
        CHECK_UPLOAD -->|Yes| EXTRACT
        EXTRACT --> SPLIT
        SPLIT --> PROCESS
        
        subgraph "Concurrent Word Processing"
            SEMAPHORE[Semaphore Control<br/>Max 5 concurrent]
            WORD1[Word 1]
            WORD2[Word 2]
            WORDN[Word N]
            
            PROCESS --> SEMAPHORE
            SEMAPHORE --> WORD1
            SEMAPHORE --> WORD2
            SEMAPHORE --> WORDN
            
            WORD1 -->|Generate| GEN1[Audio Generation]
            WORD2 -->|Generate| GEN2[Audio Generation]
            WORDN -->|Generate| GENN[Audio Generation]
            
            GEN1 -->|Upload| UP1[Upload word]
            GEN2 -->|Upload| UP2[Upload word]
            GENN -->|Upload| UPN[Upload word]
        end
        
        UP1 --> COMPLETE[Processing Complete]
        UP2 --> COMPLETE
        UPN --> COMPLETE
    end
```

## Flujo de Upload con Transcripción

```mermaid
graph TD
    START[Audio Generado]
    CHECK_TRANS{¿Transcripción<br/>Completa?}
    CHECK_SRT{¿SRT Palabra<br/>por Palabra?}
    UPLOAD[Upload con SRT]
    SKIP[Skip Upload<br/>"waiting for transcription"]
    SUCCESS[Upload Exitoso]
    
    START --> CHECK_TRANS
    CHECK_TRANS -->|Sí| CHECK_SRT
    CHECK_TRANS -->|No| SKIP
    CHECK_SRT -->|Sí| UPLOAD
    CHECK_SRT -->|No| SKIP
    UPLOAD --> SUCCESS
```

## Flujo de Procesamiento de Palabras Detallado

```mermaid
sequenceDiagram
    participant WPS as WordProcessingStrategy
    participant Text as Text Splitter
    participant Sem as Semaphore(5)
    participant Gen as HiggsAudioGenerator
    participant Up as HttpAudioUploader
    participant Store as FileStorage
    
    Note over WPS: Check if enabled and audio exists
    WPS->>Text: Split original_text into words
    Text-->>WPS: ["Hello", "world", "example"]
    
    loop For each word (concurrent)
        WPS->>Sem: Acquire slot
        Sem-->>WPS: Slot acquired
        
        WPS->>Gen: generate(word, language, voice_ref)
        Gen-->>WPS: word_audio_path
        
        WPS->>Up: upload(path, audio_type="word")
        Note over Up: metadata: {word_index, word_text}
        Up-->>WPS: {uuid, file_url}
        
        WPS->>Store: save_metadata(word_audio_id)
        Store-->>WPS: OK
        
        WPS->>Sem: Release slot
    end
    
    Note over WPS: Compile results and stats
```

## Flujo de Error y Reintentos

```mermaid
graph TD
    START[Inicio Upload]
    ATTEMPT[Intento N]
    CHECK{¿Éxito?}
    RETRY{¿N < 3?}
    SUCCESS[Upload Exitoso]
    FAIL[Upload Fallido]
    
    START --> ATTEMPT
    ATTEMPT --> CHECK
    CHECK -->|Sí| SUCCESS
    CHECK -->|No| RETRY
    RETRY -->|Sí| WAIT[Esperar 2s]
    WAIT --> ATTEMPT
    RETRY -->|No| FAIL
```

## Flujo de Prioridades y Control de Estrategias

```mermaid
graph TD
    subgraph "Priority Queue System"
        MSG1[Message Priority: CRITICAL]
        MSG2[Message Priority: HIGH]
        MSG3[Message Priority: NORMAL]
        MSG4[Message Priority: LOW]
        
        QUEUE[Processing Queue<br/>FIFO + Priority]
        
        MSG1 -->|Priority 0| QUEUE
        MSG2 -->|Priority 1| QUEUE
        MSG3 -->|Priority 2| QUEUE
        MSG4 -->|Priority 3| QUEUE
    end
    
    subgraph "Strategy Flow Control"
        RESULT[StrategyResult]
        RESULT -->|should_continue=true| NEXT[Next Strategy]
        RESULT -->|should_continue=false| STOP[Stop Processing]
        RESULT -->|next_strategy='specific'| JUMP[Jump to Strategy]
    end
```

## Configuración de Variables de Entorno

```bash
# Processing Queue Configuration
QUEUE_MAX_SIZE=1000              # Tamaño máximo de la cola
CONCURRENT_PROCESSORS=3          # Procesadores concurrentes

# Validation Strategy Configuration
VALIDATION_MIN_TEXT_LENGTH=1     # Longitud mínima del texto
VALIDATION_MAX_TEXT_LENGTH=10000 # Longitud máxima del texto

# Post-Processing Strategy Configuration
ENABLE_NOTIFICATIONS=true        # Habilitar notificaciones
ENABLE_ANALYTICS=true           # Habilitar analytics
ENABLE_CLEANUP=false            # Habilitar limpieza
WEBHOOK_URL=                    # URL para webhooks

# Word Processing Strategy Configuration
WORD_PROCESSING_ENABLED=true         # Habilitar procesamiento por palabras
WORD_PROCESSING_MAX_CONCURRENT=5     # Máximo de palabras procesando concurrentemente
WORD_PROCESSING_TIMEOUT=30.0         # Timeout en segundos por palabra

# Audio Configuration
AUDIO_DEVICE=                   # Dispositivo (auto-detecta si vacío)

# Transcription Configuration
TRANSCRIPTION_ENABLED=true      # Habilitar transcripción WhisperX
TRANSCRIPTION_MODEL=base        # Modelo: tiny, base, small, medium, large
TRANSCRIPTION_DEVICE=cpu        # Dispositivo: cpu o cuda
TRANSCRIPTION_COMPUTE_TYPE=int8 # Precisión: float16, int8
TRANSCRIPTION_BATCH_SIZE=16     # Tamaño del batch

# Authentication Configuration
AUTH_URL=http://localhost:3000/auth/login  # URL del endpoint de autenticación
AUTH_EMAIL=admin@test.com                  # Email para autenticación
AUTH_PASSWORD=password123                  # Contraseña para autenticación
AUTH_TOKEN_REFRESH_MARGIN=300              # Segundos antes de expirar para renovar

# LLM Provider Configuration
LLM_PROVIDER=ollama                        # Proveedor LLM: ollama, claude, openai
LLM_BASE_URL=https://llm.oscgre.com        # URL base para API LLM
LLM_API_KEY=                               # API key para proveedores que lo requieren
LLM_MODEL=llama3.1                         # Modelo por defecto
LLM_TEMPERATURE=0.7                        # Temperatura para generación (0.0-1.0)
LLM_MAX_TOKENS=2000                        # Máximo de tokens a generar
LLM_TIMEOUT=30                             # Timeout en segundos para requests LLM

# Configuración específica por proveedor
OLLAMA_MODEL=llama3.1                      # Modelo de Ollama
CLAUDE_API_KEY=                            # API key de Claude
CLAUDE_MODEL=claude-3-opus-20240229        # Versión del modelo Claude
OPENAI_API_KEY=                            # API key de OpenAI
OPENAI_MODEL=gpt-4-turbo-preview           # Modelo de OpenAI
```

## Notas Importantes

1. **Patrón Strategy**: Permite agregar nuevas estrategias sin modificar código existente
2. **Cola con Prioridades**: Los mensajes críticos se procesan primero
3. **Procesamiento Concurrente**: 3 procesadores trabajan en paralelo por defecto
4. **Detección de GPU**: Automática para MPS (Apple), CUDA (NVIDIA) o CPU
5. **Timeouts**: 5 minutos por chunk para evitar bloqueos indefinidos
6. **Retry Count**: Los mensajes incluyen contador de reintentos
7. **Graceful Shutdown**: Procesa mensajes pendientes antes de cerrar
8. **Contexto Compartido**: Las estrategias pueden compartir datos entre sí
9. **Voice References**: Sistema centralizado de gestión de voces por personaje
10. **Upload Condicional**: El audio SOLO se sube cuando la transcripción palabra por palabra está completa
11. **No Duplicate Uploads**: SpeechProcessingStrategy ya no realiza uploads, todo se centraliza en PostProcessingStrategy
12. **Autenticación Automática**: HttpAuthService maneja login y renovación de tokens automáticamente

## Nuevos Componentes - Sistema de Transcripción

### WhisperXTranscriptionService
- Servicio de transcripción automática con alineación palabra por palabra
- Componentes principales:
  - **Whisper**: Modelo de reconocimiento de voz de OpenAI
  - **Silero VAD**: Voice Activity Detection para segmentación precisa
  - **wav2vec2.0**: Forced alignment para timestamps exactos por palabra
- Características:
  - Detección automática de idioma
  - Soporte para 20+ idiomas
  - Modelos disponibles: tiny, base, small, medium, large
  - Procesamiento en CPU o GPU
  - Genera SRT con timestamp individual para cada palabra

## Sistema de Autenticación

### HttpAuthService
- Servicio de autenticación HTTP para gestión de tokens
- Características principales:
  - **Login automático**: Se autentica con las credenciales configuradas
  - **Caché de tokens**: Mantiene tokens en memoria para evitar múltiples logins
  - **Renovación automática**: Renueva tokens antes de que expiren
  - **Thread-safe**: Uso de locks para evitar autenticaciones simultáneas
- Flujo de autenticación:
  1. HttpAudioUploader solicita token antes de cada upload
  2. HttpAuthService verifica si el token actual es válido
  3. Si no es válido o está por expirar, realiza login automático
  4. Retorna el token válido para el upload

### Flujo de Transcripción

```mermaid
graph TD
    subgraph "Transcription Flow"
        AUDIO[Generated Audio File]
        WHISPER[Whisper Model]
        VAD[Silero VAD]
        ALIGN[wav2vec2.0 Alignment]
        SRT[Word-level SRT]
        
        AUDIO -->|Load| WHISPER
        WHISPER -->|Transcribe| VAD
        VAD -->|Segment speech| ALIGN
        ALIGN -->|Word timestamps| SRT
    end
```

## Sistema de Referencias de Voz

### VoiceReferenceService
- Servicio que gestiona un conjunto de voces predefinidas
- Mapeo de nombres de personajes a archivos de audio de referencia
- Voces disponibles:
  - **belinda** (default): Voz profesional femenina clara
  - **shrek_donkey**: Voz energética en español
  - **narrator**: Voz profunda para audiolibros
  - **child**: Voz juvenil entusiasta
  - **elder**: Voz sabia y cálida
- Fallback automático a voz por defecto si no se encuentra el personaje

### Flujo de Selección de Voz

```mermaid
graph TD
    subgraph "Voice Selection Flow"
        MSG[Message with character field]
        SPEECH[SpeechProcessingStrategy]
        VOICE[VoiceReferenceService]
        DEFAULT[Default: belinda]
        
        MSG -->|character: 'narrator'| SPEECH
        SPEECH -->|get_voice_path| VOICE
        VOICE -->|Check mapping| EXISTS{Exists?}
        EXISTS -->|Yes| PATH[Return audio path]
        EXISTS -->|No| DEFAULT
        DEFAULT --> PATH
        PATH -->|reference_audio_path| HIGGS[HiggsAudioGenerator]
    end
```

## Flujo de Autenticación

```mermaid
graph TD
    subgraph "Authentication Flow"
        UPLOAD[HttpAudioUploader]
        AUTH[HttpAuthService]
        CACHE{Token<br/>Cached?}
        VALID{Token<br/>Valid?}
        LOGIN[Login to API]
        TOKEN[Access Token]
        
        UPLOAD -->|Request Token| AUTH
        AUTH --> CACHE
        CACHE -->|Yes| VALID
        CACHE -->|No| LOGIN
        VALID -->|Yes| TOKEN
        VALID -->|No| LOGIN
        LOGIN -->|Credentials| API[API /auth/login]
        API -->|Tokens| AUTH
        AUTH -->|Cache Tokens| TOKEN
        TOKEN -->|Bearer Token| UPLOAD
    end
```

## Sistema de Language Models (LLM) - NUEVO

### LLMService
- Servicio principal para interacción con modelos de lenguaje
- Soporta múltiples proveedores mediante patrón Factory
- Proveedores implementados:
  - **Ollama**: Configurado por defecto con https://llm.oscgre.com
  - **Claude**: API de Anthropic
  - **OpenAI**: API de OpenAI
- Características:
  - Generación de texto con y sin plantillas
  - Streaming de respuestas
  - Configuración por variables de entorno
  - Selección dinámica de proveedor

### PromptService
- Gestión centralizada de plantillas de prompts
- Categorías disponibles:
  - **transcription**: Mejora y corrección de transcripciones
  - **translation**: Traducción de textos
  - **summarization**: Resumen de contenido
  - **analysis**: Análisis de sentimientos y temas
  - **generation**: Generación de títulos y descripciones
  - **validation**: Validación de calidad y moderación
  - **custom**: Plantillas personalizables
- Sistema de renderizado con variables
- 13 plantillas predefinidas listas para usar

### Flujo de Integración LLM

```mermaid
graph TD
    subgraph "LLM Integration Flow"
        STRATEGY[Any Strategy]
        LLM_SERVICE[LLMService]
        PROMPT_SERVICE[PromptService]
        FACTORY[LLMProviderFactory]
        
        OLLAMA[OllamaDriver]
        CLAUDE[ClaudeDriver]
        OPENAI[OpenAIDriver]
        
        STRATEGY -->|Inject| LLM_SERVICE
        LLM_SERVICE -->|Get Template| PROMPT_SERVICE
        LLM_SERVICE -->|Select Provider| FACTORY
        
        FACTORY -->|provider=ollama| OLLAMA
        FACTORY -->|provider=claude| CLAUDE
        FACTORY -->|provider=openai| OPENAI
        
        OLLAMA -->|API Call| OLLAMA_API[https://llm.oscgre.com]
        CLAUDE -->|API Call| CLAUDE_API[Anthropic API]
        OPENAI -->|API Call| OPENAI_API[OpenAI API]
    end
```

### Uso del Servicio LLM

Las estrategias pueden inyectar el servicio LLM cuando lo necesiten:

```python
# Ejemplo de uso en una estrategia
async def execute(self, message, context):
    # Usar con plantilla predefinida
    response = await self.llm_service.generate_with_template(
        "enhance_transcription",
        {"transcription": context["transcription"]}
    )
    
    # Usar directamente
    response = await self.llm_service.generate(
        prompt="Analiza el siguiente texto...",
        system_prompt="Eres un experto analista...",
        temperature=0.5
    )
```

## Referencias de Archivos

### Archivos de Configuración
- **src/main.py**: Punto de entrada principal
- **src/container.py**: Contenedor de inyección de dependencias
- **.env.example**: Plantilla de configuración

### Capa de Aplicación
- **src/application/interfaces/**
  - `voice_reference_service.py`: Interfaz del servicio de voces
  - `audio_generator.py`: Interfaz del generador de audio
  - `message_processing_strategy.py`: Interfaz base de estrategias
  - `transcription_service.py`: Interfaz del servicio de transcripción
  - `llm_service.py`: Interfaz del servicio LLM (NUEVO)
  - `prompt_service.py`: Interfaz del servicio de prompts (NUEVO)
- **src/application/strategies/**
  - `speech_processing_strategy.py`: Estrategia principal de procesamiento
  - `validation_strategy.py`: Estrategia de validación
  - `transcription_processing_strategy.py`: Estrategia de transcripción
  - `post_processing_strategy.py`: Estrategia de post-procesamiento
  - `word_processing_strategy.py`: Estrategia de procesamiento por palabras
- **src/application/orchestrator.py**: Coordinador de estrategias
- **src/application/utils/srt_generator.py**: Generador de SRT básico

### Capa de Infraestructura
- **src/infrastructure/services/**
  - `local_voice_reference_service.py`: Implementación del servicio de voces
- **src/infrastructure/transcription/**
  - `whisperx_transcription_service.py`: Implementación con WhisperX
- **src/infrastructure/audio/**
  - `higgs_audio_generator.py`: Implementación del generador Higgs
  - `simple_text_chunker.py`: Divisor de texto
- **src/infrastructure/messaging/**
  - `rabbitmq_consumer.py`: Consumidor de RabbitMQ
- **src/infrastructure/queues/**
  - `in_memory_processing_queue.py`: Cola de procesamiento en memoria
- **src/infrastructure/storage/**
  - `local_file_storage.py`: Almacenamiento local de archivos
- **src/infrastructure/external/**
  - `http_audio_uploader.py`: Cliente HTTP para uploads con SRT
  - `http_auth_service.py`: Servicio de autenticación HTTP
- **src/infrastructure/llm/** (NUEVO)
  - `base_driver.py`: Clase base para drivers LLM
  - `ollama_driver.py`: Driver para Ollama
  - `claude_driver.py`: Driver para Claude
  - `openai_driver.py`: Driver para OpenAI
  - `llm_provider_factory.py`: Factory para selección de proveedores
  - `llm_service_impl.py`: Implementación del servicio LLM
- **src/infrastructure/prompts/** (NUEVO)
  - `local_prompt_service.py`: Servicio de prompts con plantillas predefinidas

### Workers
- **src/workers/**
  - `message_consumer_worker.py`: Worker principal con procesamiento concurrente

### Dominio
- **src/domain/entities/**
  - `message.py`: Entidad Message
  - `speech.py`: Entidad Speech
  - `audio.py`: Entidad Audio

### Tests
- **test_voice_reference_service.py**: Test del servicio de voces
- **test_reference_audio.py**: Test de integración con audio de referencia
- **tests/unit/infrastructure/llm/** (NUEVO)
  - `test_prompt_service.py`: Tests del servicio de prompts
  - `test_llm_factory.py`: Tests del factory de proveedores
  - `test_llm_service.py`: Tests del servicio LLM