#!/usr/bin/env python3
"""
Script independiente para arreglar problemas de compatibilidad con transformers 4.30.2
Puede ejecutarse manualmente si el install.sh no aplicó los parches correctamente.
"""
import os
import sys
import re

def patch_modeling_higgs_audio():
    """Parchea el archivo modeling_higgs_audio.py para compatibilidad con transformers 4.30.2"""
    file_path = "boson_multimodal/model/higgs_audio/modeling_higgs_audio.py"
    
    if not os.path.exists(file_path):
        print(f"❌ Archivo no encontrado: {file_path}")
        return False
    
    print(f"📝 Parcheando {file_path}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Verificar si ya está parcheado
    if "# Patched for compatibility" in content:
        print("✅ Ya está parcheado")
        return True
    
    original_content = content
    
    # Parche 1: Reemplazar import de AttentionMaskConverter
    content = content.replace(
        "from transformers.modeling_attn_mask_utils import AttentionMaskConverter",
        "# Patched for compatibility with transformers 4.30.2\ntry:\n    from transformers.modeling_attn_mask_utils import AttentionMaskConverter\nexcept ImportError:\n    # For transformers < 4.28.0\n    AttentionMaskConverter = None"
    )
    
    # Parche 2: Reemplazar import de cache_utils
    content = content.replace(
        "from transformers.cache_utils import Cache, DynamicCache, StaticCache",
        "# Patched for compatibility with transformers 4.30.2\ntry:\n    from transformers.cache_utils import Cache, DynamicCache, StaticCache\nexcept ImportError:\n    # For transformers < 4.32.0 - provide fallbacks\n    Cache = None\n    DynamicCache = None\n    StaticCache = None"
    )
    
    # Parche 3: Arreglar imports de Llama duplicados y LLAMA_ATTENTION_CLASSES
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
    
    # Parche 4: Agregar fallbacks para las clases faltantes
    fallback_code = '''

# Fallbacks for missing classes in transformers 4.30.2
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
    
    # Encontrar dónde insertar el código fallback (después de los imports)
    import_end = content.find("from .audio_head import")
    if import_end != -1:
        import_end = content.find("\n", import_end) + 1
        content = content[:import_end] + fallback_code + content[import_end:]
    
    # Verificar si hubo cambios
    if content == original_content:
        print("⚠️  No se realizaron cambios (posiblemente ya parcheado de otra forma)")
        return True
    
    # Escribir el archivo parcheado
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Parche aplicado exitosamente")
    return True

def check_transformers_version():
    """Verifica la versión de transformers instalada"""
    try:
        import transformers
        version = transformers.__version__
        print(f"📦 Transformers versión: {version}")
        
        major, minor, patch = map(int, version.split('.')[:3])
        
        if major == 4 and minor == 30 and patch == 2:
            print("✅ Versión correcta de transformers")
            return True
        else:
            print(f"⚠️  Se recomienda transformers==4.30.2 (actual: {version})")
            return False
    except Exception as e:
        print(f"❌ Error verificando transformers: {e}")
        return False

def main():
    print("🔧 Script de compatibilidad para Higgs Audio Service")
    print("=" * 50)
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("boson_multimodal"):
        print("❌ Error: Este script debe ejecutarse desde el directorio raíz del proyecto")
        print("   (donde está la carpeta boson_multimodal)")
        return 1
    
    # Verificar versión de transformers
    check_transformers_version()
    print()
    
    # Aplicar parches
    success = patch_modeling_higgs_audio()
    
    print()
    if success:
        print("✅ Todos los parches aplicados correctamente")
        print("\n🚀 Ahora puedes ejecutar el servicio con:")
        print("   source venv/bin/activate")
        print("   python src/main.py")
        return 0
    else:
        print("❌ Algunos parches no se pudieron aplicar")
        print("\n⚠️  Es posible que necesites revisar manualmente los archivos")
        return 1

if __name__ == "__main__":
    sys.exit(main())