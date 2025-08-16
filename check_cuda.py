#!/usr/bin/env python3
"""
Script de diagnóstico CUDA para verificar compatibilidad
"""
import torch
import sys

print("=== Diagnóstico CUDA ===")
print(f"Python: {sys.version}")
print(f"PyTorch: {torch.__version__}")
print(f"CUDA disponible: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"Dispositivos CUDA: {torch.cuda.device_count()}")
    
    for i in range(torch.cuda.device_count()):
        print(f"\nGPU {i}: {torch.cuda.get_device_name(i)}")
        print(f"  Capacidad: {torch.cuda.get_device_capability(i)}")
        print(f"  Memoria: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
    
    # Intentar crear un tensor en GPU
    try:
        x = torch.zeros(1).cuda()
        print("\n✅ Puede crear tensores en GPU")
    except Exception as e:
        print(f"\n❌ Error al crear tensor en GPU: {e}")
else:
    print("\n❌ CUDA no está disponible")
    print("Razones posibles:")
    print("- No hay GPU NVIDIA")
    print("- Drivers NVIDIA no instalados")
    print("- PyTorch instalado sin soporte CUDA")

print("\n=== Recomendación ===")
if torch.cuda.is_available():
    try:
        x = torch.zeros(1).cuda()
        print("✅ Usar device='cuda'")
    except:
        print("❌ Usar device='cpu' (GPU incompatible)")
else:
    print("❌ Usar device='cpu'")