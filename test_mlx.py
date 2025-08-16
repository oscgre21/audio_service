"""
Test script para MLX-Audio - alternativa optimizada para Apple Silicon
"""
from mlx_audio.tts.generate import generate_audio
import time

def test_mlx_audio():
    """Probar MLX-Audio con modelo Kokoro"""
    
    print("🚀 Probando MLX-Audio...")
    
    # Texto para generar
    text = """In the small corner bookstore, among dusty shelves and forgotten books, lived Hope. 
    She wasn't the owner, but simply an elderly woman who had arrived there one rainy October afternoon 
    and had never left."""
    
    print(f"📝 Texto: {text[:50]}...")
    
    start_time = time.time()
    
    try:
        # Generar audio con MLX-Audio
        output_path = generate_audio(
            text=text,
            model_path="prince-canuma/Kokoro-82M",
            voice="af_heart",  # Voz femenina
            speed=1.0,
            output_path="output_mlx.wav"
        )
        
        generation_time = time.time() - start_time
        
        print(f"✅ Audio generado en {generation_time:.2f} segundos")
        print(f"🎵 Archivo guardado: {output_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Tip: Asegúrate de tener conexión a internet para descargar el modelo")

def test_mlx_web_interface():
    """Instrucciones para la interfaz web"""
    print("\n🌐 Para usar la interfaz web de MLX-Audio:")
    print("1. Ejecuta: mlx-audio web")
    print("2. Abre: http://127.0.0.1:8000")
    print("3. Disfruta de la visualización 3D y controles interactivos")

if __name__ == "__main__":
    test_mlx_audio()
    test_mlx_web_interface()