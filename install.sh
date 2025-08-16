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
    # Con CUDA
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    # CPU only
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Instalar el resto de dependencias
echo "   - Instalando otras dependencias..."
echo "   Nota: Esto puede tomar 10-15 minutos debido a las dependencias de ML..."
pip install -r requirements.txt

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
        echo "   ⚠️  IMPORTANTE: Edita .env con tus credenciales"
    else
        echo "✅ Manteniendo .env existente"
    fi
else
    cp .env.example .env
    echo "✅ .env creado desde .env.example"
    echo "   ⚠️  IMPORTANTE: Edita .env con tus credenciales"
fi

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

# Resumen final
echo ""
echo "===================================="
echo "✅ Instalación completada!"
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
echo "3. Para ejecutar con GPU (si está disponible):"
echo "   Asegúrate de que AUDIO_DEVICE=cuda en .env"
echo ""
echo "4. Para más información:"
echo "   - README.md: Documentación general"
echo "   - src/docs/: Documentación técnica detallada"
echo ""
echo "¡Disfruta usando Higgs Audio Service! 🎵"