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

# Verificar si pip está actualizado para soportar wheels modernos
echo "   - Verificando versión de pip..."
pip --version

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
        pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cpu
        USE_CUDA=false
    # RTX 4090 y GPUs modernas (sm_89)
    elif [[ "$GPU_NAME" == *"RTX 4090"* ]] || [[ "$GPU_NAME" == *"RTX 4080"* ]] || [[ "$GPU_NAME" == *"RTX 4070"* ]] || [ "$GPU_ARCH" -eq "89" ]; then
        echo "   ✅ GPU RTX 40 series detectada. Instalando PyTorch con CUDA 11.8..."
        pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu118
        USE_CUDA=true
    # Otras GPUs compatibles
    else
        echo "   ✅ GPU compatible detectada. Instalando PyTorch con CUDA 11.8..."
        pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu118
        USE_CUDA=true
    fi
else
    # CPU only
    echo "   No se detectó GPU NVIDIA. Instalando PyTorch para CPU..."
    pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cpu
    USE_CUDA=false
fi

# Instalar el resto de dependencias
echo "   - Instalando otras dependencias..."
echo "   Nota: Esto puede tomar 10-15 minutos debido a las dependencias de ML..."

# Instalar pydantic-settings primero (requerido pero no siempre listado)
echo "   - Instalando pydantic-settings..."
pip install pydantic-settings

# Instalar numpy compatible con PyTorch 2.1.2
echo "   - Instalando numpy compatible..."
pip install "numpy<2.0"

# Instalar requirements.txt con manejo especial para conflictos
echo "   - Instalando dependencias del proyecto..."

# Instalar versiones compatibles de todos los paquetes
echo "   - Resolviendo conflictos de dependencias..."

# Usar versiones más modernas que tienen wheels precompilados
echo "   - Instalando transformers y tokenizers..."
pip install transformers==4.36.2 tokenizers==0.15.0

# Instalar faster-whisper compatible
echo "   - Instalando faster-whisper..."
pip install faster-whisper==1.0.1

# Instalar whisperx y sus dependencias
echo "   - Instalando whisperx..."
pip install whisperx==3.1.5

# Instalar pyannote.audio si no se instaló
echo "   - Verificando pyannote.audio..."
pip install pyannote.audio==3.1.1 || echo "   ⚠️  pyannote.audio ya instalado o con conflictos"

# Instalar botocore y s3transfer para boto3
echo "   - Instalando dependencias de AWS..."
pip install botocore==1.35.36 s3transfer==0.10.2

# Instalar dependencias adicionales
echo "   - Instalando dependencias adicionales..."
pip install pytz>=2020.1 tzdata>=2022.7 nltk

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

# Crear un script Python más completo para parchear todos los problemas de compatibilidad
cat > fix_compatibility.py << 'EOF'
#!/usr/bin/env python3
"""
Script para arreglar problemas de compatibilidad con transformers 4.30.2
"""
import os
import sys
import re

def patch_modeling_higgs_audio():
    """Parchea el archivo modeling_higgs_audio.py para compatibilidad con transformers 4.30.2"""
    file_path = "boson_multimodal/model/higgs_audio/modeling_higgs_audio.py"
    
    if not os.path.exists(file_path):
        print(f"   ⚠️  Archivo no encontrado: {file_path}")
        return False
    
    print(f"   - Parcheando {file_path}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Verificar si ya está parcheado
    if "# Patched for compatibility" in content:
        print("   ✅ Ya está parcheado")
        return True
    
    # Parche 1: Reemplazar import de AttentionMaskConverter
    content = content.replace(
        "from transformers.modeling_attn_mask_utils import AttentionMaskConverter",
        "# Patched for compatibility with transformers 4.30.2\ntry:\n    from transformers.modeling_attn_mask_utils import AttentionMaskConverter\nexcept ImportError:\n    # For transformers < 4.28.0\n    AttentionMaskConverter = None"
    )
    
    # Parche 1b: Reemplazar import de cache_utils
    content = content.replace(
        "from transformers.cache_utils import Cache, DynamicCache, StaticCache",
        "# Patched for compatibility with transformers 4.30.2\ntry:\n    from transformers.cache_utils import Cache, DynamicCache, StaticCache\nexcept ImportError:\n    # For transformers < 4.32.0 - provide fallbacks\n    Cache = None\n    DynamicCache = None\n    StaticCache = None"
    )
    
    # Parche 2: Arreglar imports de Llama duplicados y LLAMA_ATTENTION_CLASSES
    old_llama_import = """from transformers.models.llama.modeling_llama import (
    LlamaDecoderLayer,
    LlamaRMSNorm,
    LlamaRotaryEmbedding,
    LLAMA_ATTENTION_CLASSES,
    LlamaMLP,
    LlamaRMSNorm,
)"""
    
    new_llama_import = """from transformers.models.llama.modeling_llama import (
    LlamaDecoderLayer,
    LlamaRMSNorm,
    LlamaRotaryEmbedding,
    LlamaMLP,
)

# Handle LLAMA_ATTENTION_CLASSES for different transformers versions
try:
    from transformers.models.llama.modeling_llama import LLAMA_ATTENTION_CLASSES
except ImportError:
    # For older versions of transformers
    LLAMA_ATTENTION_CLASSES = {}"""
    
    content = content.replace(old_llama_import, new_llama_import)
    
    # Parche 3: Si AttentionMaskConverter o Cache se usan en el código, agregar fallbacks
    needs_fallback = False
    fallback_code = '''

# Fallbacks for missing classes in transformers 4.30.2
'''
    
    if "AttentionMaskConverter" in content and "class AttentionMaskConverterFallback" not in content:
        needs_fallback = True
        fallback_code += '''
if AttentionMaskConverter is None:
    class AttentionMaskConverterFallback:
        """Simple fallback for AttentionMaskConverter"""
        @staticmethod
        def to_causal_4d(attention_mask, input_shape, dtype, device):
            batch_size, seq_length = input_shape
            causal_mask = torch.triu(torch.ones((seq_length, seq_length), dtype=torch.bool), diagonal=1)
            causal_mask = causal_mask.to(device).unsqueeze(0).unsqueeze(0)
            causal_mask = causal_mask.expand(batch_size, 1, seq_length, seq_length)
            if attention_mask is not None:
                causal_mask = causal_mask.masked_fill(attention_mask[:, None, None, :] == 0, True)
            return causal_mask.to(dtype) * torch.finfo(dtype).min
    
    AttentionMaskConverter = AttentionMaskConverterFallback
'''
    
    if ("Cache" in content or "DynamicCache" in content or "StaticCache" in content) and "class CacheFallback" not in content:
        needs_fallback = True
        fallback_code += '''
# Fallbacks for cache_utils classes
if Cache is None:
    class CacheFallback:
        """Base cache class fallback"""
        def __init__(self):
            self.key_cache = []
            self.value_cache = []
        
        def update(self, key_states, value_states, layer_idx, cache_kwargs=None):
            if len(self.key_cache) <= layer_idx:
                self.key_cache.append(key_states)
                self.value_cache.append(value_states)
            else:
                self.key_cache[layer_idx] = torch.cat([self.key_cache[layer_idx], key_states], dim=2)
                self.value_cache[layer_idx] = torch.cat([self.value_cache[layer_idx], value_states], dim=2)
            return self.key_cache[layer_idx], self.value_cache[layer_idx]
        
        def get_seq_length(self, layer_idx=0):
            if len(self.key_cache) > layer_idx:
                return self.key_cache[layer_idx].shape[2]
            return 0
    
    Cache = CacheFallback

if DynamicCache is None:
    class DynamicCacheFallback(CacheFallback if Cache is not None else object):
        """DynamicCache fallback"""
        pass
    
    DynamicCache = DynamicCacheFallback

if StaticCache is None:
    class StaticCacheFallback(CacheFallback if Cache is not None else object):
        """StaticCache fallback"""
        def __init__(self, config, batch_size, max_cache_len, device, dtype=None):
            super().__init__()
            self.max_cache_len = max_cache_len
            self.batch_size = batch_size
    
    StaticCache = StaticCacheFallback
'''
    
    if needs_fallback:
        # Encontrar dónde insertar el código (después de los imports)
        import_end = content.find("from .audio_head import")
        if import_end != -1:
            import_end = content.find("\n", import_end) + 1
            content = content[:import_end] + fallback_code + content[import_end:]
    
    # Escribir el archivo parcheado
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("   ✅ Parche aplicado exitosamente")
    return True

def check_and_fix_transformers_version():
    """Verifica la versión de transformers y sugiere actualización si es necesario"""
    try:
        import transformers
        version = transformers.__version__
        major, minor, patch = map(int, version.split('.')[:3])
        
        if major == 4 and minor == 30 and patch == 2:
            print(f"   ✅ Transformers {version} es la versión correcta")
            return True
        else:
            print(f"   ⚠️  Transformers {version} detectado, se recomienda 4.30.2")
            return False
    except Exception as e:
        print(f"   ❌ Error verificando transformers: {e}")
        return False

def main():
    print("Aplicando parches de compatibilidad...")
    
    # Aplicar parches
    success = patch_modeling_higgs_audio()
    
    # Verificar versión de transformers
    check_and_fix_transformers_version()
    
    if success:
        print("✅ Todos los parches aplicados correctamente")
        return 0
    else:
        print("⚠️  Algunos parches no se pudieron aplicar")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

# Ejecutar el script de parches
python fix_compatibility.py
PATCH_STATUS=$?

# Limpiar
rm -f fix_compatibility.py

if [ $PATCH_STATUS -eq 0 ]; then
    echo "   ✅ Parches de compatibilidad aplicados"
else
    echo "   ⚠️  Advertencia: Algunos parches no se aplicaron correctamente"
    echo "      El servicio podría tener problemas de compatibilidad"
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

# Preguntar si desea iniciar el servicio
echo "¿Deseas iniciar el servicio ahora? (s/n)"
read -p "Respuesta: " -n 1 -r
echo

if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo ""
    echo "===================================="
    echo "🚀 Iniciando Higgs Audio Service..."
    echo "===================================="
    echo ""
    echo "ℹ️  Presiona Ctrl+C para detener el servicio"
    echo ""
    
    # Verificar credenciales críticas antes de iniciar
    RABBITMQ_PASSWORD=$(grep RABBITMQ_PASSWORD .env | cut -d '=' -f2)
    if [ "$RABBITMQ_PASSWORD" == "your_password_here" ] || [ -z "$RABBITMQ_PASSWORD" ]; then
        echo "⚠️  ADVERTENCIA: RABBITMQ_PASSWORD no está configurado"
        echo "   El servicio puede fallar al conectarse a RabbitMQ"
        echo ""
        echo "   Edita .env y configura:"
        echo "   - RABBITMQ_PASSWORD"
        echo "   - UPLOAD_TOKEN (si usas upload)"
        echo "   - AUTH_EMAIL y AUTH_PASSWORD (si usas autenticación)"
        echo ""
        read -p "¿Continuar de todos modos? (s/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            echo ""
            echo "Para iniciar el servicio más tarde:"
            echo "   ./boot.sh"
            echo ""
            echo "O manualmente:"
            echo "   source venv/bin/activate"
            echo "   python src/main.py"
            exit 0
        fi
    fi
    
    # Iniciar el servicio
    python src/main.py
    
    # Manejar salida
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        echo ""
        echo "✅ Servicio detenido correctamente"
    else
        echo ""
        echo "❌ El servicio terminó con error (código: $EXIT_CODE)"
        echo "   Revisa los logs en: audio_processing.log"
    fi
else
    echo ""
    echo "Para iniciar el servicio más tarde:"
    echo "   ./boot.sh"
    echo ""
    echo "O manualmente:"
    echo "   source venv/bin/activate"
    echo "   python src/main.py"
    echo ""
    echo "Recuerda editar .env con tus credenciales:"
    echo "   - RABBITMQ_PASSWORD"
    echo "   - UPLOAD_TOKEN (si usas upload)"
    echo "   - AUTH_EMAIL y AUTH_PASSWORD (para autenticación)"
fi

echo ""
echo "Para más información:"
echo "   - README.md: Documentación general"
echo "   - src/docs/: Documentación técnica detallada"
echo ""
echo "¡Gracias por usar Higgs Audio Service! 🎵"