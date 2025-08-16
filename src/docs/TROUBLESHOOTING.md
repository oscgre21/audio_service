# 🔧 Troubleshooting - Solución de Problemas

## 🚨 Problemas Comunes

### 1. Error de Conexión a RabbitMQ

**Síntoma:**
```
Error al conectar con RabbitMQ: Connection refused
```

**Soluciones:**
- Verificar que RabbitMQ esté corriendo
- Verificar credenciales en `.env`
- Verificar conectividad de red: `telnet rabbit.oscgre.com 5672`
- Revisar firewall/proxy

**Debug:**
```bash
# Probar conexión
python -c "import pika; pika.BlockingConnection(pika.ConnectionParameters('rabbit.oscgre.com'))"
```

### 2. Error de Token JWT (401)

**Síntoma:**
```
Error de autenticación (401): Token inválido o expirado
```

**Soluciones:**
- Obtener nuevo token del servidor
- Actualizar `UPLOAD_TOKEN` en `.env`
- Verificar formato del token (debe empezar con `eyJ`)
- Deshabilitar uploads temporalmente: `UPLOAD_ENABLED=false`

### 3. Error al Generar Audio

**Síntoma:**
```
Error al inicializar Higgs Audio Engine: CUDA out of memory
```

**Soluciones:**
- Usar CPU: `AUDIO_DEVICE=cpu`
- Reducir tamaño de chunks: `AUDIO_MAX_CHUNK_LENGTH=300`
- Liberar memoria GPU: `nvidia-smi` y matar procesos
- Reducir `max_new_tokens` en configuración

### 4. Archivos No Encontrados

**Síntoma:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'generated_audio/...'
```

**Soluciones:**
```bash
# Crear directorios necesarios
mkdir -p generated_audio/temp_chunks

# Verificar permisos
chmod -R 755 generated_audio/
```

### 5. Error de Importación

**Síntoma:**
```
ModuleNotFoundError: No module named 'src'
```

**Soluciones:**
- Ejecutar desde la raíz del proyecto
- Agregar al PYTHONPATH: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`
- Usar rutas absolutas en imports

## 📋 Checklist de Diagnóstico

### Variables de Entorno
```bash
# Verificar que .env existe
ls -la .env

# Ver variables cargadas
python -c "from src.config import get_settings; print(get_settings().dict())"

# Verificar variable específica
echo $RABBITMQ_PASSWORD
```

### Dependencias
```bash
# Verificar instalación
pip list | grep -E "pika|torch|dependency-injector|pydantic"

# Reinstalar si es necesario
pip install --force-reinstall -r requirements.txt
```

### Permisos
```bash
# Verificar permisos de escritura
touch generated_audio/test.txt && rm generated_audio/test.txt

# Arreglar permisos
sudo chown -R $USER:$USER generated_audio/
```

### Conectividad
```bash
# Test RabbitMQ
nc -zv rabbit.oscgre.com 5672

# Test API Upload
curl -X GET http://localhost:3000/health

# Test con token
curl -H "Authorization: Bearer $UPLOAD_TOKEN" http://localhost:3000/audio/test
```

## 🐛 Debugging Avanzado

### Habilitar Logs Detallados

```python
# src/main.py - Agregar al inicio
import logging
logging.getLogger('pika').setLevel(logging.DEBUG)
logging.getLogger('urllib3').setLevel(logging.DEBUG)
```

### Modo Debug Interactivo

```python
# Agregar breakpoint donde necesites
import pdb; pdb.set_trace()

# O con ipdb (más features)
import ipdb; ipdb.set_trace()
```

### Inspeccionar Container DI

```python
# Debug script
from src.container import Container
from src.config import get_settings

settings = get_settings()
container = Container()
container.config.from_dict(settings.dict())

# Ver providers disponibles
print(container.providers)

# Probar instanciación
audio_gen = container.audio_generator()
print(audio_gen)
```

## 💊 Soluciones Rápidas

### Reset Completo
```bash
# 1. Limpiar cache Python
find . -type d -name __pycache__ -exec rm -r {} +

# 2. Reinstalar dependencias
pip uninstall -y -r requirements.txt
pip install -r requirements.txt

# 3. Limpiar archivos generados
rm -rf generated_audio/*

# 4. Restart
python src/main.py
```

### Modo Mínimo (sin uploads)
```bash
# .env
UPLOAD_ENABLED=false
LOG_LEVEL=WARNING
```

### Verificar Salud del Sistema

```python
# health_check.py
import asyncio
from src.container import Container
from src.config import get_settings

async def health_check():
    settings = get_settings()
    container = Container()
    container.config.from_dict(settings.dict())
    
    print("🔍 Verificando componentes...")
    
    # 1. Configuración
    print(f"✓ Configuración cargada: {settings.app_name}")
    
    # 2. Storage
    storage = container.file_storage()
    exists = await storage.exists(".")
    print(f"✓ Storage funcionando: {exists}")
    
    # 3. Message Queue
    try:
        mq = container.message_queue()
        await mq.connect()
        print("✓ RabbitMQ conectado")
        await mq.disconnect()
    except Exception as e:
        print(f"✗ RabbitMQ error: {e}")
    
    # 4. Audio Generator
    try:
        gen = container.audio_generator()
        print("✓ Audio Generator inicializado")
    except Exception as e:
        print(f"✗ Audio Generator error: {e}")

if __name__ == "__main__":
    asyncio.run(health_check())
```

## 📞 Logs Útiles para Soporte

Cuando reportes un problema, incluye:

```bash
# 1. Versión de Python
python --version

# 2. Dependencias instaladas
pip freeze > installed_packages.txt

# 3. Variables de entorno (sin passwords)
env | grep -E "RABBITMQ|AUDIO|UPLOAD" | sed 's/PASSWORD=.*/PASSWORD=***/'

# 4. Últimas líneas del log
tail -n 100 audio_processing.log

# 5. Estructura de archivos
tree -L 3 src/
```

## 🆘 Errores Críticos

### Out of Memory
```bash
# Monitorear memoria
watch -n 1 free -h

# Limitar memoria Python
export PYTHONMALLOC=malloc
python src/main.py
```

### Proceso Zombie
```bash
# Encontrar proceso
ps aux | grep python

# Matar proceso
kill -9 <PID>

# Limpiar locks
rm -f /tmp/*.lock
```

### Corrupción de Archivos
```bash
# Verificar integridad
find generated_audio -name "*.wav" -exec file {} \; | grep -v "WAVE audio"

# Limpiar corruptos
find generated_audio -name "*.wav" -size 0 -delete
```