"""
Script de prueba para verificar la integración del servicio LLM
"""
import asyncio
from src.config import get_settings
from src.infrastructure.prompts import LocalPromptService
from src.infrastructure.llm import LLMServiceImpl, LLMProviderFactory

async def test_llm_integration():
    """Prueba la integración del servicio LLM"""
    print("=== Probando integración del servicio LLM ===\n")
    
    # 1. Verificar configuración
    settings = get_settings()
    print(f"✓ Configuración cargada")
    print(f"  - Proveedor LLM: {settings.llm.provider}")
    print(f"  - URL base: {settings.llm.base_url}")
    print(f"  - Modelo: {settings.llm.model}\n")
    
    # 2. Verificar servicio de prompts
    prompt_service = LocalPromptService()
    templates = prompt_service.list_templates()
    print(f"✓ Servicio de prompts inicializado")
    print(f"  - Plantillas disponibles: {len(templates)}")
    print(f"  - Categorías: {set(t.category.value for t in templates)}\n")
    
    # 3. Verificar factory de proveedores
    providers = LLMProviderFactory.get_supported_providers()
    print(f"✓ Factory de proveedores LLM")
    print(f"  - Proveedores soportados: {providers}\n")
    
    # 4. Verificar creación del servicio LLM
    try:
        llm_config = {
            "base_url": settings.llm.base_url,
            "api_key": settings.llm.api_key,
            "model": settings.llm.model,
            "timeout": settings.llm.timeout,
            "ollama_model": settings.llm.ollama_model,
        }
        
        llm_service = LLMServiceImpl(
            provider=settings.llm.provider,
            config=llm_config,
            prompt_service=prompt_service
        )
        print(f"✓ Servicio LLM creado exitosamente")
        print(f"  - Driver: {llm_service.driver.__class__.__name__}")
        print(f"  - Modelo configurado: {llm_service.driver.model}\n")
        
    except Exception as e:
        print(f"✗ Error creando servicio LLM: {e}\n")
        return
    
    # 5. Probar renderizado de plantilla
    try:
        system_prompt, user_prompt = prompt_service.render_template(
            "enhance_transcription",
            {"transcription": "Esta es una prueba de transcripción"}
        )
        print(f"✓ Renderizado de plantilla exitoso")
        print(f"  - System prompt: {system_prompt[:50]}...")
        print(f"  - User prompt: {user_prompt[:50]}...\n")
    except Exception as e:
        print(f"✗ Error renderizando plantilla: {e}\n")
    
    print("=== Integración completada exitosamente ===")

if __name__ == "__main__":
    asyncio.run(test_llm_integration())