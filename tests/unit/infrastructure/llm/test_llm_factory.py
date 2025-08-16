"""
Tests para el factory de proveedores LLM
"""
import pytest
from src.infrastructure.llm import LLMProviderFactory, LLMProvider
from src.infrastructure.llm.ollama_driver import OllamaDriver
from src.infrastructure.llm.claude_driver import ClaudeDriver
from src.infrastructure.llm.openai_driver import OpenAIDriver


class TestLLMProviderFactory:
    """Tests para LLMProviderFactory"""
    
    def test_create_ollama_driver(self):
        """Test crear driver de Ollama"""
        config = {
            "base_url": "https://llm.oscgre.com",
            "model": "llama3.1"
        }
        
        driver = LLMProviderFactory.create_driver("ollama", config)
        
        assert isinstance(driver, OllamaDriver)
        assert driver.base_url == "https://llm.oscgre.com"
        assert driver.model == "llama3.1"
    
    def test_create_claude_driver(self):
        """Test crear driver de Claude"""
        config = {
            "api_key": "test-api-key",
            "model": "claude-3-opus"
        }
        
        driver = LLMProviderFactory.create_driver("claude", config)
        
        assert isinstance(driver, ClaudeDriver)
        assert driver.api_key == "test-api-key"
    
    def test_create_openai_driver(self):
        """Test crear driver de OpenAI"""
        config = {
            "api_key": "test-api-key",
            "model": "gpt-4"
        }
        
        driver = LLMProviderFactory.create_driver("openai", config)
        
        assert isinstance(driver, OpenAIDriver)
        assert driver.api_key == "test-api-key"
    
    def test_create_driver_invalid_provider(self):
        """Test crear driver con proveedor inválido"""
        with pytest.raises(ValueError) as exc_info:
            LLMProviderFactory.create_driver("invalid_provider", {})
        
        assert "no soportado" in str(exc_info.value)
        assert "ollama, claude, openai" in str(exc_info.value)
    
    def test_get_supported_providers(self):
        """Test obtener lista de proveedores soportados"""
        providers = LLMProviderFactory.get_supported_providers()
        
        assert "ollama" in providers
        assert "claude" in providers
        assert "openai" in providers
        assert len(providers) == 3
    
    def test_create_driver_case_insensitive(self):
        """Test crear driver con nombre en diferentes casos"""
        config = {"base_url": "https://test.com"}
        
        # Probar diferentes variaciones de caso
        driver1 = LLMProviderFactory.create_driver("OLLAMA", config)
        driver2 = LLMProviderFactory.create_driver("Ollama", config)
        driver3 = LLMProviderFactory.create_driver("oLLaMa", config)
        
        assert isinstance(driver1, OllamaDriver)
        assert isinstance(driver2, OllamaDriver)
        assert isinstance(driver3, OllamaDriver)