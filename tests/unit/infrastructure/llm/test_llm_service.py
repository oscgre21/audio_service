"""
Tests para el servicio LLM
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.infrastructure.llm import LLMServiceImpl
from src.application.interfaces.llm_service import LLMResponse
from src.application.interfaces.prompt_service import PromptTemplate, PromptCategory


class TestLLMServiceImpl:
    """Tests para LLMServiceImpl"""
    
    @pytest.fixture
    def mock_prompt_service(self):
        """Mock del servicio de prompts"""
        mock = Mock()
        mock.render_template.return_value = (
            "System prompt",
            "User prompt"
        )
        mock.get_template.return_value = PromptTemplate(
            name="test_template",
            category=PromptCategory.ANALYSIS,
            system_prompt="System",
            user_prompt_template="User",
            variables=[],
            description="Test"
        )
        return mock
    
    @pytest.fixture
    def mock_driver(self):
        """Mock del driver LLM"""
        mock = Mock()
        mock.generate = AsyncMock(return_value={
            "content": "Generated response",
            "model": "test-model",
            "usage": {"total_tokens": 100},
            "metadata": {"test": "data"}
        })
        mock._prepare_messages = Mock(return_value=[
            {"role": "user", "content": "Test prompt"}
        ])
        return mock
    
    @pytest.fixture
    def llm_service(self, mock_prompt_service, mock_driver):
        """Fixture para crear servicio LLM con mocks"""
        with patch('src.infrastructure.llm.llm_service_impl.LLMProviderFactory.create_driver', return_value=mock_driver):
            service = LLMServiceImpl(
                provider="ollama",
                config={"base_url": "https://test.com"},
                prompt_service=mock_prompt_service
            )
            return service
    
    @pytest.mark.asyncio
    async def test_generate_success(self, llm_service):
        """Test generación exitosa"""
        response = await llm_service.generate(
            prompt="Test prompt",
            temperature=0.5,
            max_tokens=100
        )
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Generated response"
        assert response.model == "test-model"
        assert response.usage["total_tokens"] == 100
    
    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, llm_service):
        """Test generación con system prompt"""
        response = await llm_service.generate(
            prompt="User question",
            system_prompt="You are a helpful assistant",
            temperature=0.7
        )
        
        assert response.content == "Generated response"
        llm_service.driver._prepare_messages.assert_called_with(
            "User question",
            "You are a helpful assistant"
        )
    
    @pytest.mark.asyncio
    async def test_generate_with_template(self, llm_service):
        """Test generación usando plantilla"""
        variables = {"content": "Test content"}
        
        response = await llm_service.generate_with_template(
            template_name="test_template",
            variables=variables,
            temperature=0.8
        )
        
        assert response.content == "Generated response"
        llm_service.prompt_service.render_template.assert_called_with(
            "test_template",
            variables
        )
    
    @pytest.mark.asyncio
    async def test_generate_with_template_preferences(self, llm_service):
        """Test generación con preferencias del modelo en plantilla"""
        # Configurar plantilla con preferencias
        template = PromptTemplate(
            name="test_template",
            category=PromptCategory.ANALYSIS,
            system_prompt="System",
            user_prompt_template="User",
            variables=[],
            description="Test",
            model_preferences={"temperature": 0.3, "max_tokens": 500}
        )
        llm_service.prompt_service.get_template.return_value = template
        
        response = await llm_service.generate_with_template(
            template_name="test_template",
            variables={},
            temperature=0.9  # Esto debería sobrescribir la preferencia
        )
        
        # Verificar que se llamó con los parámetros mezclados correctamente
        call_kwargs = llm_service.driver.generate.call_args[1]
        assert call_kwargs["temperature"] == 0.9  # kwargs sobrescribe preferencias
    
    @pytest.mark.asyncio
    async def test_generate_stream(self, llm_service):
        """Test generación en streaming"""
        # Configurar mock para streaming
        async def mock_stream(*args, **kwargs):
            for chunk in ["Hello", " ", "world"]:
                yield chunk
        
        llm_service.driver.generate_stream = mock_stream
        
        chunks = []
        async for chunk in llm_service.generate_stream("Test prompt"):
            chunks.append(chunk)
        
        assert chunks == ["Hello", " ", "world"]
    
    @pytest.mark.asyncio
    async def test_generate_error_handling(self, llm_service):
        """Test manejo de errores en generación"""
        llm_service.driver.generate = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(Exception) as exc_info:
            await llm_service.generate("Test prompt")
        
        assert "API Error" in str(exc_info.value)