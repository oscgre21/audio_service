#!/bin/bash

# Script para arreglar el problema de CUDA y cambiar a CPU

echo "🔧 Arreglando configuración CUDA..."

# Cambiar a CPU en .env si existe
if [ -f ".env" ]; then
    # Verificar si AUDIO_DEVICE existe
    if grep -q "AUDIO_DEVICE=" .env; then
        # Reemplazar el valor existente
        sed -i.bak 's/AUDIO_DEVICE=.*/AUDIO_DEVICE=cpu/' .env
        echo "✅ Actualizado AUDIO_DEVICE a cpu en .env"
    else
        # Agregar si no existe
        echo "AUDIO_DEVICE=cpu" >> .env
        echo "✅ Agregado AUDIO_DEVICE=cpu a .env"
    fi
    
    # También actualizar TRANSCRIPTION_DEVICE si existe
    if grep -q "TRANSCRIPTION_DEVICE=" .env; then
        sed -i.bak 's/TRANSCRIPTION_DEVICE=.*/TRANSCRIPTION_DEVICE=cpu/' .env
        echo "✅ Actualizado TRANSCRIPTION_DEVICE a cpu"
    fi
else
    echo "❌ No se encontró archivo .env"
    exit 1
fi

# Verificar el cambio
echo ""
echo "Configuración actual:"
grep "DEVICE=" .env | grep -E "(AUDIO_DEVICE|TRANSCRIPTION_DEVICE)"

echo ""
echo "✅ Configuración actualizada para usar CPU"
echo ""
echo "Tu GPU (RTX 5070 Ti) es muy nueva y requiere una versión de PyTorch"
echo "que aún no está disponible en los repositorios estándar."
echo ""
echo "El servicio funcionará correctamente con CPU."
echo ""
echo "Para iniciar el servicio, ejecuta:"
echo "  ./boot.sh"