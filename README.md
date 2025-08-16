# 🎵 Higgs Audio Service

Servicio de generación de audio mediante IA que procesa mensajes desde RabbitMQ, genera audio usando Higgs Audio Engine y opcionalmente sube los archivos a un servidor remoto.

## 🚀 Quick Start

### Instalación Rápida

```bash
# 1. Clonar y entrar al proyecto
git clone <repository-url>
cd higgs-audio

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# 3. Instalar ffmpeg (requerido para WhisperX)
# macOS:
brew install ffmpeg
# Ubuntu/Debian:
sudo apt-get install ffmpeg
# Windows: Descargar desde https://ffmpeg.org/download.html

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar
cp .env.example .env
# Editar .env con tus credenciales

# 6. Ejecutar
python src/main.py
```

## 📋 Requisitos

- Python 3.8+
- CUDA (opcional, para GPU)
- RabbitMQ accesible
- ~8GB RAM mínimo
- ~10GB espacio en disco
- ffmpeg (para transcripción con WhisperX)

## 🔧 Configuración

### Variables de Entorno Principales

```env
# RabbitMQ (obligatorio)
RABBITMQ_PASSWORD=tu_password

# Upload API (obligatorio si UPLOAD_ENABLED=true)
UPLOAD_TOKEN=tu_jwt_token

# Opcionales
AUDIO_DEVICE=cuda  # o cpu
AUDIO_MAX_CHUNK_LENGTH=566
LOG_LEVEL=INFO

# Transcripción con WhisperX (opcional)
TRANSCRIPTION_ENABLED=true
TRANSCRIPTION_MODEL=base  # tiny, base, small, medium, large
TRANSCRIPTION_DEVICE=cpu  # o cuda
TRANSCRIPTION_COMPUTE_TYPE=int8  # float16, int8
TRANSCRIPTION_BATCH_SIZE=16
```

Ver `.env.example` para todas las opciones.

## 🏗️ Arquitectura

El servicio sigue principios **SOLID** y **Clean Architecture**:

```
src/
├── config/          # Configuración
├── domain/          # Entidades de negocio
├── application/     # Casos de uso
├── infrastructure/  # Implementaciones
└── presentation/    # Workers/CLI
```

Ver [documentación completa](src/docs/README.md) para más detalles.

## 📚 Características

- ✅ Procesamiento asíncrono de mensajes
- ✅ Generación de audio con Higgs Audio v2
- ✅ División inteligente de textos largos
- ✅ Concatenación automática de chunks
- ✅ Upload opcional a servidor remoto
- ✅ Persistencia local con metadata
- ✅ Manejo robusto de errores
- ✅ Logging detallado
- ✅ Configuración flexible
- ✅ Transcripción con WhisperX para subtítulos palabra por palabra
- ✅ Voice Activity Detection (VAD) con Silero
- ✅ Alineación forzada con wav2vec2.0
- ✅ Autenticación automática con renovación de tokens JWT

## 🔄 Flujo de Procesamiento

1. **Recepción**: Mensaje `speech.created` desde RabbitMQ
2. **Validación**: Verificación de estructura y datos
3. **Chunking**: División si texto > 566 caracteres
4. **Generación**: Audio con Higgs Audio Engine
5. **Almacenamiento**: Guardado local + metadata
6. **Transcripción** (opcional): Generación de SRT palabra por palabra con WhisperX
7. **Autenticación**: Login automático y obtención de token JWT si es necesario
8. **Upload**: Subida al servidor con subtítulos mejorados y token válido
9. **Confirmación**: ACK del mensaje

## 🎯 Transcripción con WhisperX

El servicio incluye transcripción automática con WhisperX para generar subtítulos palabra por palabra con timestamps precisos.

### Características:
- **Alineación palabra por palabra**: Cada palabra tiene su timestamp exacto
- **Voice Activity Detection**: Detección precisa de segmentos de voz con Silero VAD
- **Forced Alignment**: Usa wav2vec2.0 para alineación precisa
- **Multi-idioma**: Soporte para 20+ idiomas con detección automática
- **Procesamiento no invasivo**: Se ejecuta como estrategia separada sin afectar el flujo principal

### Ejemplo de salida SRT:
```srt
1
00:00:00,436 --> 00:00:01,098
Hola,

2
00:00:01,500 --> 00:00:01,881
¿cómo

3
00:00:01,881 --> 00:00:02,164
estás?
```

### Configuración:
```env
TRANSCRIPTION_ENABLED=true       # Activar/desactivar
TRANSCRIPTION_MODEL=base         # Modelo: tiny, base, small, medium, large
TRANSCRIPTION_DEVICE=cpu         # Dispositivo: cpu o cuda
TRANSCRIPTION_COMPUTE_TYPE=int8  # Precisión: float16 o int8
```

## 🔐 Sistema de Autenticación

El servicio incluye autenticación automática con el backend para obtener tokens JWT válidos antes de cada upload.

### Características:
- **Login automático**: Se autentica con las credenciales configuradas
- **Caché de tokens**: Mantiene tokens en memoria para evitar múltiples logins
- **Renovación automática**: Renueva tokens 5 minutos antes de que expiren
- **Thread-safe**: Usa locks para evitar autenticaciones simultáneas
- **Fallback**: Si falla el servicio de auth, usa el token legacy configurado

### Configuración:
```env
AUTH_URL=http://localhost:3000/auth/login  # Endpoint de autenticación
AUTH_EMAIL=admin@test.com                  # Email para login
AUTH_PASSWORD=password123                  # Contraseña
AUTH_TOKEN_REFRESH_MARGIN=300              # Segundos antes de renovar (5 min)
```

## 📊 Monitoreo

### Logs
- Consola: Salida estándar
- Archivo: `audio_processing.log`

### Métricas
- Mensajes procesados
- Tiempo de generación
- Tamaño de archivos
- Estado de uploads
- Palabras transcritas

## 🛠️ Desarrollo

### Estructura del Proyecto
```
higgs-audio/
├── src/
│   ├── docs/         # Documentación
│   ├── config/       # Configuración
│   ├── domain/       # Lógica de negocio
│   ├── application/  # Casos de uso
│   └── infrastructure/ # Implementaciones
├── tests/            # Tests
├── generated_audio/  # Output
└── requirements.txt
```

### Agregar Nueva Funcionalidad

1. Crear interface en `application/interfaces/`
2. Implementar en `infrastructure/`
3. Agregar al container DI
4. Documentar cambios

Ver [guía de desarrollo](src/docs/DEVELOPMENT.md).

## 🧪 Testing

```bash
# Ejecutar tests
pytest

# Con coverage
pytest --cov=src

# Test específico
pytest tests/unit/test_use_case.py
```

## 🐛 Troubleshooting

### Problemas Comunes

**Error de conexión RabbitMQ:**
```bash
# Verificar conectividad
telnet rabbit.oscgre.com 5672
```

**CUDA out of memory:**
```bash
# Usar CPU
AUDIO_DEVICE=cpu python src/main.py
```

**Token expirado (401):**
- El sistema renueva tokens automáticamente
- Verificar credenciales en AUTH_EMAIL y AUTH_PASSWORD
- O deshabilitar uploads: `UPLOAD_ENABLED=false`

**ModuleNotFoundError: jwt**
```bash
# Instalar PyJWT
pip install PyJWT
```

**WhisperX no disponible:**
```bash
# Verificar instalación de ffmpeg
ffmpeg -version

# Reinstalar WhisperX
pip install --upgrade git+https://github.com/m-bain/whisperX.git
```

**Error de memoria con WhisperX:**
```bash
# Usar modelo más pequeño
TRANSCRIPTION_MODEL=tiny python src/main.py

# O deshabilitar transcripción
TRANSCRIPTION_ENABLED=false python src/main.py
```

Ver [guía completa](src/docs/TROUBLESHOOTING.md).

## 📖 Documentación

- [Arquitectura](src/docs/ARCHITECTURE.md) - Diseño del sistema
- [Desarrollo](src/docs/DEVELOPMENT.md) - Guía para developers
- [API Reference](src/docs/API.md) - Interfaces y clases
- [Troubleshooting](src/docs/TROUBLESHOOTING.md) - Solución de problemas

## 🤝 Contribuir

1. Fork el proyecto
2. Crear feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto está bajo licencia privada. Ver `LICENSE` para detalles.

## 🙏 Agradecimientos

- Boson AI por Higgs Audio Engine
- Equipo de desarrollo
- Comunidad open source