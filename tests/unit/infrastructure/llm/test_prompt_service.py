"""
Tests para el servicio de prompts
"""
import pytest
from src.infrastructure.prompts import LocalPromptService
from src.application.interfaces.prompt_service import (
    PromptCategory,
    PromptNotFoundError,
    MissingVariableError
)


class TestLocalPromptService:
    """Tests para LocalPromptService"""
    
    @pytest.fixture
    def prompt_service(self):
        """Fixture para crear una instancia del servicio"""
        return LocalPromptService()
    
    def test_get_template_success(self, prompt_service):
        """Test obtener plantilla existente"""
        template = prompt_service.get_template("enhance_transcription")
        
        assert template.name == "enhance_transcription"
        assert template.category == PromptCategory.TRANSCRIPTION
        assert "transcription" in template.variables
        assert len(template.system_prompt) > 0
    
    def test_get_template_not_found(self, prompt_service):
        """Test obtener plantilla inexistente"""
        with pytest.raises(PromptNotFoundError):
            prompt_service.get_template("non_existent_template")
    
    def test_get_by_category(self, prompt_service):
        """Test obtener plantillas por categoría"""
        transcription_templates = prompt_service.get_by_category(PromptCategory.TRANSCRIPTION)
        
        assert len(transcription_templates) > 0
        assert all(t.category == PromptCategory.TRANSCRIPTION for t in transcription_templates)
    
    def test_get_by_tags(self, prompt_service):
        """Test obtener plantillas por tags"""
        audio_templates = prompt_service.get_by_tags(["audio"])
        
        assert len(audio_templates) > 0
        assert all("audio" in t.tags for t in audio_templates)
    
    def test_render_template_success(self, prompt_service):
        """Test renderizar plantilla con todas las variables"""
        variables = {
            "transcription": "Esta es una transcripción de prueba"
        }
        
        system_prompt, user_prompt = prompt_service.render_template(
            "enhance_transcription", 
            variables
        )
        
        assert "Esta es una transcripción de prueba" in user_prompt
        assert len(system_prompt) > 0
    
    def test_render_template_missing_variables(self, prompt_service):
        """Test renderizar plantilla sin variables requeridas"""
        with pytest.raises(MissingVariableError) as exc_info:
            prompt_service.render_template("enhance_transcription", {})
        
        assert "transcription" in str(exc_info.value)
    
    def test_render_template_with_multiple_variables(self, prompt_service):
        """Test renderizar plantilla con múltiples variables"""
        variables = {
            "source_lang": "español",
            "target_lang": "inglés",
            "text": "Hola mundo"
        }
        
        system_prompt, user_prompt = prompt_service.render_template(
            "translate_text",
            variables
        )
        
        assert "español" in user_prompt
        assert "inglés" in user_prompt
        assert "Hola mundo" in user_prompt
    
    def test_list_templates(self, prompt_service):
        """Test listar todas las plantillas"""
        templates = prompt_service.list_templates()
        
        assert len(templates) > 0
        assert any(t.name == "enhance_transcription" for t in templates)
        assert any(t.category == PromptCategory.TRANSLATION for t in templates)
    
    def test_custom_prompt_template(self, prompt_service):
        """Test plantilla personalizada"""
        variables = {
            "system_prompt": "Eres un asistente útil",
            "user_prompt": "¿Cuál es la capital de Francia?"
        }
        
        system_prompt, user_prompt = prompt_service.render_template(
            "custom_prompt",
            variables
        )
        
        assert system_prompt == "Eres un asistente útil"
        assert user_prompt == "¿Cuál es la capital de Francia?"