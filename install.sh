#!/bin/bash

# Script de instalación para Higgs Audio Service
# Este script configura el entorno completo para ejecutar el servicio

set -e  # Salir si hay algún error

echo "🎵 Instalación de Higgs Audio Service"
echo "===================================="

# Verificar versión de Python
echo "1. Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado. Por favor instala Python 3.8 o superior."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION encontrado"

# Verificar ffmpeg
echo ""
echo "2. Verificando ffmpeg (requerido para transcripción)..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg no está instalado. Es requerido para la transcripción con WhisperX."
    echo "   Instálalo con:"
    echo "   - macOS: brew install ffmpeg"
    echo "   - Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "   - Windows: Descarga desde https://ffmpeg.org/download.html"
    echo ""
    read -p "¿Continuar sin ffmpeg? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
else
    echo "✅ ffmpeg encontrado"
fi

# Verificar CUDA (opcional)
echo ""
echo "3. Verificando CUDA (opcional para GPU)..."
if command -v nvidia-smi &> /dev/null; then
    echo "✅ CUDA disponible. El servicio puede usar GPU."
else
    echo "ℹ️  CUDA no detectado. El servicio usará CPU."
fi

# Crear entorno virtual
echo ""
echo "4. Creando entorno virtual..."
if [ -d "venv" ]; then
    echo "⚠️  El entorno virtual ya existe. ¿Deseas recrearlo?"
    read -p "   (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo "✅ Entorno virtual recreado"
    else
        echo "✅ Usando entorno virtual existente"
    fi
else
    python3 -m venv venv
    echo "✅ Entorno virtual creado"
fi

# Activar entorno virtual
echo ""
echo "5. Activando entorno virtual..."
source venv/bin/activate
echo "✅ Entorno virtual activado"

# Actualizar pip
echo ""
echo "6. Actualizando pip..."
pip install --upgrade pip
echo "✅ pip actualizado"

# Instalar dependencias
echo ""
echo "7. Instalando dependencias..."
echo "   Esto puede tomar varios minutos..."

# Instalar PyTorch primero (para evitar conflictos)
echo "   - Instalando PyTorch..."
if command -v nvidia-smi &> /dev/null; then
    # Detectar modelo de GPU
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
    GPU_ARCH=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d '.')
    
    echo "   GPU detectada: $GPU_NAME (compute capability: $GPU_ARCH)"
    
    # RTX 5070 Ti y GPUs muy nuevas (sm_120+)
    if [ -n "$GPU_ARCH" ] && [ "$GPU_ARCH" -ge "120" ]; then
        echo "   ⚠️  GPU muy nueva detectada. Usando CPU por compatibilidad..."
        pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
        USE_CUDA=false
    # RTX 4090 y GPUs modernas (sm_89)
    elif [[ "$GPU_NAME" == *"RTX 4090"* ]] || [[ "$GPU_NAME" == *"RTX 4080"* ]] || [[ "$GPU_NAME" == *"RTX 4070"* ]] || [ "$GPU_ARCH" -eq "89" ]; then
        echo "   ✅ GPU RTX 40 series detectada. Instalando PyTorch con CUDA 11.8..."
        pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
        USE_CUDA=true
    # Otras GPUs compatibles
    else
        echo "   ✅ GPU compatible detectada. Instalando PyTorch con CUDA 11.8..."
        pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
        USE_CUDA=true
    fi
else
    # CPU only
    echo "   No se detectó GPU NVIDIA. Instalando PyTorch para CPU..."
    pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
    USE_CUDA=false
fi

# Instalar el resto de dependencias
echo "   - Instalando otras dependencias..."
echo "   Nota: Esto puede tomar 10-15 minutos debido a las dependencias de ML..."

# Instalar pydantic-settings primero (requerido pero no siempre listado)
echo "   - Instalando pydantic-settings..."
pip install pydantic-settings

# Instalar requirements.txt con manejo especial para conflictos
echo "   - Instalando dependencias del proyecto..."

# Primero instalar transformers y tokenizers compatibles
pip install transformers==4.41.2 tokenizers>=0.13,<0.16

# Luego instalar whisperx sin dependencias para evitar conflictos
pip install whisperx==3.1.5 --no-deps

# Instalar faster-whisper manualmente
pip install faster-whisper==1.0.1

# Finalmente instalar el resto de requirements
pip install -r requirements.txt --no-deps 2>/dev/null || {
    echo "   - Instalando dependencias restantes individualmente..."
    # Instalar las dependencias principales una por una
    while IFS= read -r line; do
        # Ignorar comentarios y líneas vacías
        if [[ ! "$line" =~ ^#.*$ ]] && [[ ! -z "$line" ]]; then
            # Ignorar las líneas que ya instalamos
            if [[ ! "$line" =~ transformers ]] && [[ ! "$line" =~ whisperx ]] && [[ ! "$line" =~ tokenizers ]]; then
                pip install "$line" 2>/dev/null || echo "   ⚠️  No se pudo instalar: $line"
            fi
        fi
    done < requirements.txt
}

echo "✅ Dependencias instaladas"

# Crear directorios necesarios
echo ""
echo "8. Creando directorios..."
mkdir -p generated_audio
mkdir -p generated_audio/temp_chunks
mkdir -p logs
echo "✅ Directorios creados"

# Configurar archivo .env
echo ""
echo "9. Configurando archivo .env..."
if [ -f ".env" ]; then
    echo "⚠️  El archivo .env ya existe."
    read -p "   ¿Deseas sobrescribirlo con .env.example? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        cp .env.example .env
        echo "✅ .env copiado desde .env.example"
    else
        echo "✅ Manteniendo .env existente"
    fi
else
    cp .env.example .env
    echo "✅ .env creado desde .env.example"
fi

# Configurar dispositivo según la detección de GPU
echo ""
echo "   Configurando dispositivo de procesamiento..."
if [ "$USE_CUDA" == "true" ]; then
    # Configurar para CUDA
    sed -i.bak 's/AUDIO_DEVICE=.*/AUDIO_DEVICE=cuda/' .env 2>/dev/null || sed -i '' 's/AUDIO_DEVICE=.*/AUDIO_DEVICE=cuda/' .env 2>/dev/null
    sed -i.bak 's/TRANSCRIPTION_DEVICE=.*/TRANSCRIPTION_DEVICE=cuda/' .env 2>/dev/null || sed -i '' 's/TRANSCRIPTION_DEVICE=.*/TRANSCRIPTION_DEVICE=cuda/' .env 2>/dev/null
    echo "   ✅ Configurado para usar GPU (CUDA)"
else
    # Configurar para CPU
    sed -i.bak 's/AUDIO_DEVICE=.*/AUDIO_DEVICE=cpu/' .env 2>/dev/null || sed -i '' 's/AUDIO_DEVICE=.*/AUDIO_DEVICE=cpu/' .env 2>/dev/null
    sed -i.bak 's/TRANSCRIPTION_DEVICE=.*/TRANSCRIPTION_DEVICE=cpu/' .env 2>/dev/null || sed -i '' 's/TRANSCRIPTION_DEVICE=.*/TRANSCRIPTION_DEVICE=cpu/' .env 2>/dev/null
    echo "   ✅ Configurado para usar CPU"
fi

echo "   ⚠️  IMPORTANTE: Edita .env con tus credenciales (contraseñas, tokens, etc.)"

# Descargar modelos (opcional)
echo ""
echo "10. Pre-descarga de modelos (opcional)..."
echo "    Los modelos se descargarán automáticamente en el primer uso."
echo "    Si deseas pre-descargarlos ahora (recomendado), esto tomará ~10GB."
read -p "    ¿Descargar modelos ahora? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "    Descargando modelos de Higgs Audio..."
    python3 -c "
from transformers import AutoTokenizer, AutoModelForCausalLM
print('Descargando tokenizer...')
AutoTokenizer.from_pretrained('bosonai/higgs-audio-v2-tokenizer')
print('Descargando modelo (esto tomará varios minutos)...')
AutoModelForCausalLM.from_pretrained('bosonai/higgs-audio-v2-generation-3B-base')
print('✅ Modelos descargados')
"
fi

# Verificar RabbitMQ
echo ""
echo "11. Verificando conectividad con RabbitMQ..."
RABBITMQ_HOST=$(grep RABBITMQ_HOST .env | cut -d '=' -f2)
RABBITMQ_PORT=$(grep RABBITMQ_PORT .env | cut -d '=' -f2)
if [ -n "$RABBITMQ_HOST" ] && [ -n "$RABBITMQ_PORT" ]; then
    echo "    Probando conexión a $RABBITMQ_HOST:$RABBITMQ_PORT..."
    if timeout 2 bash -c "echo >/dev/tcp/$RABBITMQ_HOST/$RABBITMQ_PORT" 2>/dev/null; then
        echo "✅ RabbitMQ accesible"
    else
        echo "⚠️  No se pudo conectar a RabbitMQ en $RABBITMQ_HOST:$RABBITMQ_PORT"
        echo "   Asegúrate de que RabbitMQ esté ejecutándose y accesible"
    fi
else
    echo "⚠️  Configura RABBITMQ_HOST y RABBITMQ_PORT en .env"
fi

# Arreglar el código de boson_multimodal para compatibilidad
echo ""
echo "11. Aplicando parches de compatibilidad..."
if [ -f "boson_multimodal/model/higgs_audio/modeling_higgs_audio.py" ]; then
    # Verificar si ya tiene el parche
    if ! grep -q "Handle different transformers versions" boson_multimodal/model/higgs_audio/modeling_higgs_audio.py; then
        echo "   - Parcheando modeling_higgs_audio.py para compatibilidad..."
        # Crear archivo temporal con el parche
        cat > /tmp/higgs_patch.py << 'EOF'
import sys
import re

# Leer el archivo
with open(sys.argv[1], 'r') as f:
    content = f.read()

# Aplicar el parche
old_import = """from transformers.models.llama.modeling_llama import (
    LlamaDecoderLayer,
    LlamaRMSNorm,
    LlamaRotaryEmbedding,
    LLAMA_ATTENTION_CLASSES,
    LlamaMLP,
    LlamaRMSNorm,
)"""

new_import = """from transformers.models.llama.modeling_llama import (
    LlamaDecoderLayer,
    LlamaRMSNorm,
    LlamaRotaryEmbedding,
    LlamaMLP,
)

# Handle different transformers versions
try:
    from transformers.models.llama.modeling_llama import LLAMA_ATTENTION_CLASSES
except ImportError:
    # For older versions of transformers
    LLAMA_ATTENTION_CLASSES = {}"""

# Reemplazar
content = content.replace(old_import, new_import)

# Escribir el archivo
with open(sys.argv[1], 'w') as f:
    f.write(content)
EOF
        python /tmp/higgs_patch.py boson_multimodal/model/higgs_audio/modeling_higgs_audio.py
        rm /tmp/higgs_patch.py
        echo "   ✅ Parche aplicado"
    else
        echo "   ✅ Parche ya aplicado previamente"
    fi
fi

# Resumen final
echo ""
echo "===================================="
echo "✅ Instalación completada!"
echo ""
echo "Configuración detectada:"
if [ "$USE_CUDA" == "true" ]; then
    echo "- Dispositivo: GPU (CUDA)"
    echo "- GPU: $GPU_NAME"
else
    echo "- Dispositivo: CPU"
fi
echo ""
echo "Próximos pasos:"
echo "1. Edita el archivo .env con tus credenciales:"
echo "   - RABBITMQ_PASSWORD"
echo "   - UPLOAD_TOKEN (si usas upload)"
echo "   - AUTH_EMAIL y AUTH_PASSWORD (para autenticación)"
echo ""
echo "2. Para ejecutar el servicio:"
echo "   source venv/bin/activate"
echo "   python src/main.py"
echo ""
echo "   O usa el script de arranque:"
echo "   ./boot.sh"
echo ""
echo "4. Para más información:"
echo "   - README.md: Documentación general"
echo "   - src/docs/: Documentación técnica detallada"
echo ""
echo "¡Disfruta usando Higgs Audio Service! 🎵"