#!/bin/bash

# Script para configurar RTX 4090

echo "🎮 Configurando para RTX 4090..."

# Verificar si el archivo .env existe
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Creado archivo .env desde .env.example"
fi

# Configurar para usar CUDA con RTX 4090
echo "📝 Configurando dispositivos para GPU..."

# Actualizar AUDIO_DEVICE
if grep -q "AUDIO_DEVICE=" .env; then
    sed -i.bak 's/AUDIO_DEVICE=.*/AUDIO_DEVICE=cuda/' .env
else
    echo "AUDIO_DEVICE=cuda" >> .env
fi

# Actualizar TRANSCRIPTION_DEVICE
if grep -q "TRANSCRIPTION_DEVICE=" .env; then
    sed -i.bak 's/TRANSCRIPTION_DEVICE=.*/TRANSCRIPTION_DEVICE=cuda/' .env
else
    echo "TRANSCRIPTION_DEVICE=cuda" >> .env
fi

echo "✅ Configuración actualizada para RTX 4090"

# Instalar PyTorch para RTX 4090 (CUDA 11.8)
echo ""
echo "🔧 Reinstalando PyTorch para RTX 4090..."
source venv/bin/activate

# Desinstalar versiones anteriores
pip uninstall torch torchvision torchaudio -y

# Instalar PyTorch 2.1.2 con CUDA 11.8 (compatible con RTX 4090)
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118

echo ""
echo "✅ PyTorch instalado para RTX 4090"
echo ""
echo "🚀 Ahora puedes continuar con la instalación:"
echo "   pip install -r requirements.txt"
echo ""
echo "O ejecutar directamente:"
echo "   ./boot.sh"