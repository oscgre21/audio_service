# 📤 Configuración de Upload

Este documento describe la configuración del sistema de upload de audio, incluyendo los múltiples endpoints disponibles.

## Endpoints Disponibles

El sistema soporta múltiples endpoints para diferentes tipos de audio:

| Tipo | Variable de Entorno | URL por Defecto | Uso |
|------|-------------------|-----------------|-----|
| Speech (principal) | `SPEECH_UPLOAD_URL` | `http://localhost:3000/audio/speech/upload` | Audio completo del texto |
| Word | `WORD_UPLOAD_URL` | `http://localhost:3000/audio/speech/upload` | Audio de palabras individuales |
| Sentence | `SENTENCE_UPLOAD_URL` | `http://localhost:3000/audio/sentence/upload` | Audio de oraciones |
| Custom | `CUSTOM_UPLOAD_URL` | `http://localhost:3000/audio/custom/upload` | Audio personalizado |
| Legacy | `UPLOAD_URL` | `http://localhost:3000/audio/upload` | Compatibilidad hacia atrás |

## Configuración en .env

```bash
# Upload Configuration
UPLOAD_URL=http://localhost:3000/audio/upload
SPEECH_UPLOAD_URL=http://localhost:3000/audio/speech/upload
WORD_UPLOAD_URL=http://localhost:3000/audio/speech/upload
SENTENCE_UPLOAD_URL=http://localhost:3000/audio/sentence/upload
CUSTOM_UPLOAD_URL=http://localhost:3000/audio/custom/upload

# Token de autenticación (JWT)
UPLOAD_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Configuración de reintentos
UPLOAD_MAX_RETRIES=3
UPLOAD_RETRY_DELAY=2

# Habilitar/deshabilitar upload
UPLOAD_ENABLED=true

# Timeout en segundos
UPLOAD_TIMEOUT=30
```

## Estructura del Request

### Headers
```
Authorization: Bearer <UPLOAD_TOKEN>
Content-Type: multipart/form-data
```

### Form Data
```
file: <archivo.wav>
speech_uuid: <ID del speech>
audio_type: "main" | "word" | "sentence" | "custom"
original_text: <texto original completo>
metadata: <JSON con metadata opcional>
```

### Ejemplo de Request con cURL
```bash
curl -X POST http://localhost:3000/audio/speech/upload \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiI..." \
  -F "file=@generated_audio/audio.wav" \
  -F "speech_uuid=123e4567-e89b-12d3-a456-426614174000" \
  -F "audio_type=main" \
  -F "original_text=Este es el texto que se convirtió en audio"
```

## Response Esperado

### Éxito (201 Created)
```json
{
  "uuid": "987fcdeb-51a2-43d1-a456-426614174000",
  "file_url": "https://storage.example.com/audio/987fcdeb.wav",
  "file_path": "/uploads/audio/987fcdeb.wav",
  "created_at": "2025-01-09T10:30:00Z"
}
```

### Error (401 Unauthorized)
```json
{
  "error": "Invalid or expired token"
}
```

## Lógica de Selección de Endpoint

En `HttpAudioUploader`, el endpoint se selecciona según el `audio_type`:

```python
# Use the new speech endpoint for main audio type
upload_url = self.speech_upload_url if audio_type == "main" else self.base_url
```

## Configuración de Metadata

La metadata se puede incluir opcionalmente:

```python
audio_metadata = {
    'duration': 10.5,          # duración en segundos
    'size_bytes': 1048576,     # tamaño en bytes
    'format': 'wav',           # formato del archivo
    'sample_rate': 44100,      # frecuencia de muestreo
    'bitrate': 128000          # bitrate
}
```

## Troubleshooting

### Error: "Invalid URL 'None'"
**Causa**: La URL del endpoint no se está pasando correctamente al HttpAudioUploader.

**Solución**: Verificar que en `main.py` se estén pasando todas las URLs de upload:
```python
'upload': {
    'url': settings.upload.url,
    'speech_upload_url': settings.upload.speech_upload_url,
    'word_upload_url': settings.upload.word_upload_url,
    'sentence_upload_url': settings.upload.sentence_upload_url,
    'custom_upload_url': settings.upload.custom_upload_url,
    # ... otros campos
}
```

### Upload deshabilitado
**Síntoma**: Los logs muestran "⚠️ Upload disabled in configuration"

**Solución**: Establecer `UPLOAD_ENABLED=true` en el archivo `.env`

### Token expirado
**Síntoma**: Response 401 Unauthorized

**Solución**: Actualizar el `UPLOAD_TOKEN` con un JWT válido

## Seguridad

1. **Tokens JWT**: Los tokens deben tener una expiración razonable
2. **HTTPS**: En producción, usar siempre HTTPS para los endpoints
3. **Validación**: El servidor debe validar el tamaño y formato de los archivos
4. **Rate Limiting**: Implementar límites de tasa en el servidor

## Extensibilidad

Para agregar un nuevo tipo de audio:

1. Agregar la URL en `settings.py`:
```python
new_type_upload_url: str = Field(
    default="http://localhost:3000/audio/newtype/upload", 
    env="NEWTYPE_UPLOAD_URL"
)
```

2. Actualizar la lógica en `HttpAudioUploader`:
```python
if audio_type == "main":
    upload_url = self.speech_upload_url
elif audio_type == "newtype":
    upload_url = self.new_type_upload_url
else:
    upload_url = self.base_url
```

3. Agregar la configuración en `main.py` y `.env`