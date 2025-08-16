"""
Servicio local de gestión de prompts
"""
from typing import List, Dict, Any, Tuple
from string import Template
from src.application.interfaces.prompt_service import (
    PromptService,
    PromptTemplate,
    PromptCategory,
    PromptNotFoundError,
    MissingVariableError
)
import logging

logger = logging.getLogger(__name__)


class LocalPromptService(PromptService):
    """Servicio de prompts con plantillas predefinidas en memoria"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
        
    def _initialize_templates(self) -> Dict[str, PromptTemplate]:
        """Inicializa las plantillas predefinidas"""
        templates = [
            # Transcription prompts
            PromptTemplate(
                name="enhance_transcription",
                category=PromptCategory.TRANSCRIPTION,
                system_prompt="Eres un asistente especializado en mejorar transcripciones de audio. Tu tarea es corregir errores ortográficos, mejorar la puntuación y hacer que el texto sea más legible sin cambiar el significado original.",
                user_prompt_template="Mejora la siguiente transcripción de audio:\n\n$transcription",
                variables=["transcription"],
                description="Mejora transcripciones corrigiendo errores y puntuación",
                tags=["audio", "correction", "formatting"]
            ),
            
            PromptTemplate(
                name="transcription_with_context",
                category=PromptCategory.TRANSCRIPTION,
                system_prompt="Eres un asistente especializado en transcripción contextual. Debes mejorar la transcripción considerando el contexto proporcionado.",
                user_prompt_template="Contexto: $context\n\nTranscripción a mejorar:\n$transcription",
                variables=["context", "transcription"],
                description="Mejora transcripciones usando contexto adicional",
                tags=["audio", "context", "correction"]
            ),
            
            # Translation prompts
            PromptTemplate(
                name="translate_text",
                category=PromptCategory.TRANSLATION,
                system_prompt="Eres un traductor profesional. Traduce el texto manteniendo el tono y estilo original.",
                user_prompt_template="Traduce el siguiente texto de $source_lang a $target_lang:\n\n$text",
                variables=["source_lang", "target_lang", "text"],
                description="Traducción básica de texto",
                tags=["translation", "language"]
            ),
            
            PromptTemplate(
                name="translate_with_style",
                category=PromptCategory.TRANSLATION,
                system_prompt="Eres un traductor especializado. Traduce manteniendo el estilo específico indicado.",
                user_prompt_template="Traduce de $source_lang a $target_lang con estilo $style:\n\n$text",
                variables=["source_lang", "target_lang", "style", "text"],
                description="Traducción con estilo específico",
                tags=["translation", "style", "language"]
            ),
            
            # Summarization prompts
            PromptTemplate(
                name="summarize_audio_content",
                category=PromptCategory.SUMMARIZATION,
                system_prompt="Eres un experto en crear resúmenes concisos y precisos de contenido de audio.",
                user_prompt_template="Resume el siguiente contenido de audio en máximo $max_words palabras:\n\n$content",
                variables=["max_words", "content"],
                description="Resume contenido de audio",
                tags=["summary", "audio", "concise"]
            ),
            
            PromptTemplate(
                name="extract_key_points",
                category=PromptCategory.SUMMARIZATION,
                system_prompt="Eres un analista experto en identificar puntos clave en contenido hablado.",
                user_prompt_template="Extrae los $num_points puntos clave más importantes de:\n\n$content",
                variables=["num_points", "content"],
                description="Extrae puntos clave del contenido",
                tags=["summary", "key_points", "analysis"]
            ),
            
            # Analysis prompts
            PromptTemplate(
                name="analyze_sentiment",
                category=PromptCategory.ANALYSIS,
                system_prompt="Eres un experto en análisis de sentimientos y emociones en texto y audio.",
                user_prompt_template="Analiza el sentimiento y tono emocional del siguiente contenido:\n\n$content",
                variables=["content"],
                description="Analiza sentimiento y emociones",
                tags=["sentiment", "emotion", "analysis"]
            ),
            
            PromptTemplate(
                name="identify_topics",
                category=PromptCategory.ANALYSIS,
                system_prompt="Eres un experto en identificación y categorización de temas en contenido hablado.",
                user_prompt_template="Identifica los temas principales en el siguiente contenido:\n\n$content\n\nFormato de salida: Lista de temas con breve descripción",
                variables=["content"],
                description="Identifica temas principales",
                tags=["topics", "categorization", "analysis"]
            ),
            
            # Generation prompts
            PromptTemplate(
                name="generate_title",
                category=PromptCategory.GENERATION,
                system_prompt="Eres un experto en crear títulos atractivos y descriptivos para contenido de audio.",
                user_prompt_template="Genera un título conciso y atractivo para el siguiente contenido:\n\n$content\n\nIdioma: $language",
                variables=["content", "language"],
                description="Genera títulos para contenido",
                tags=["title", "generation", "creative"]
            ),
            
            PromptTemplate(
                name="generate_description",
                category=PromptCategory.GENERATION,
                system_prompt="Eres un redactor experto en crear descripciones informativas y atractivas.",
                user_prompt_template="Genera una descripción de máximo $max_chars caracteres para:\n\n$content",
                variables=["max_chars", "content"],
                description="Genera descripciones de contenido",
                tags=["description", "generation", "metadata"]
            ),
            
            # Validation prompts
            PromptTemplate(
                name="validate_transcription_quality",
                category=PromptCategory.VALIDATION,
                system_prompt="Eres un experto en control de calidad de transcripciones. Evalúa la precisión y calidad.",
                user_prompt_template="Evalúa la calidad de esta transcripción del 1 al 10 y proporciona sugerencias de mejora:\n\n$transcription",
                variables=["transcription"],
                description="Valida calidad de transcripción",
                tags=["quality", "validation", "transcription"]
            ),
            
            PromptTemplate(
                name="check_content_appropriateness",
                category=PromptCategory.VALIDATION,
                system_prompt="Eres un moderador de contenido. Evalúa si el contenido es apropiado y cumple con las políticas.",
                user_prompt_template="Evalúa si el siguiente contenido es apropiado:\n\n$content\n\nCriterios: $criteria",
                variables=["content", "criteria"],
                description="Verifica si el contenido es apropiado",
                tags=["moderation", "validation", "safety"]
            ),
            
            # Custom prompts
            PromptTemplate(
                name="custom_prompt",
                category=PromptCategory.CUSTOM,
                system_prompt="$system_prompt",
                user_prompt_template="$user_prompt",
                variables=["system_prompt", "user_prompt"],
                description="Plantilla personalizable para cualquier propósito",
                tags=["custom", "flexible"]
            )
        ]
        
        return {template.name: template for template in templates}
    
    def get_template(self, name: str) -> PromptTemplate:
        """Obtiene una plantilla por nombre"""
        if name not in self.templates:
            raise PromptNotFoundError(f"No se encontró la plantilla: {name}")
        return self.templates[name]
    
    def get_by_category(self, category: PromptCategory) -> List[PromptTemplate]:
        """Obtiene todas las plantillas de una categoría"""
        return [
            template for template in self.templates.values()
            if template.category == category
        ]
    
    def get_by_tags(self, tags: List[str]) -> List[PromptTemplate]:
        """Obtiene plantillas que contengan cualquiera de los tags"""
        matching_templates = []
        for template in self.templates.values():
            if any(tag in template.tags for tag in tags):
                matching_templates.append(template)
        return matching_templates
    
    def render_template(
        self, 
        template_name: str, 
        variables: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Renderiza una plantilla con las variables proporcionadas"""
        template = self.get_template(template_name)
        
        # Verificar que todas las variables requeridas estén presentes
        missing_vars = set(template.variables) - set(variables.keys())
        if missing_vars:
            raise MissingVariableError(
                f"Faltan las siguientes variables: {', '.join(missing_vars)}"
            )
        
        # Renderizar usando Template de string
        try:
            system_prompt = Template(template.system_prompt).safe_substitute(variables)
            user_prompt = Template(template.user_prompt_template).safe_substitute(variables)
            
            return system_prompt, user_prompt
            
        except Exception as e:
            logger.error(f"Error al renderizar plantilla {template_name}: {str(e)}")
            raise
    
    def list_templates(self) -> List[PromptTemplate]:
        """Lista todas las plantillas disponibles"""
        return list(self.templates.values())
    
    def add_template(self, template: PromptTemplate) -> None:
        """Agrega una nueva plantilla (método adicional para extensibilidad)"""
        self.templates[template.name] = template
        logger.info(f"Plantilla '{template.name}' agregada exitosamente")