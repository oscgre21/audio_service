"""
Interfaz para el servicio de gestión de prompts
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum


class PromptCategory(str, Enum):
    """Categorías disponibles para prompts"""
    TRANSCRIPTION = "transcription"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    VALIDATION = "validation"
    CUSTOM = "custom"


@dataclass
class PromptTemplate:
    """Plantilla de prompt"""
    name: str
    category: PromptCategory
    system_prompt: str
    user_prompt_template: str
    variables: List[str]
    description: str
    tags: List[str] = field(default_factory=list)
    model_preferences: Optional[Dict[str, Any]] = None
    

class PromptService(ABC):
    """Interfaz para el servicio de gestión de prompts"""
    
    @abstractmethod
    def get_template(self, name: str) -> PromptTemplate:
        """
        Obtiene una plantilla por nombre
        
        Args:
            name: Nombre de la plantilla
            
        Returns:
            PromptTemplate
            
        Raises:
            PromptNotFoundError: Si la plantilla no existe
        """
        pass
    
    @abstractmethod
    def get_by_category(self, category: PromptCategory) -> List[PromptTemplate]:
        """
        Obtiene todas las plantillas de una categoría
        
        Args:
            category: Categoría de prompts
            
        Returns:
            Lista de PromptTemplate
        """
        pass
    
    @abstractmethod
    def get_by_tags(self, tags: List[str]) -> List[PromptTemplate]:
        """
        Obtiene plantillas que contengan cualquiera de los tags especificados
        
        Args:
            tags: Lista de tags a buscar
            
        Returns:
            Lista de PromptTemplate
        """
        pass
    
    @abstractmethod
    def render_template(
        self, 
        template_name: str, 
        variables: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Renderiza una plantilla con las variables proporcionadas
        
        Args:
            template_name: Nombre de la plantilla
            variables: Variables para renderizar
            
        Returns:
            Tupla de (system_prompt, user_prompt) renderizados
            
        Raises:
            PromptNotFoundError: Si la plantilla no existe
            MissingVariableError: Si faltan variables requeridas
        """
        pass
    
    @abstractmethod
    def list_templates(self) -> List[PromptTemplate]:
        """
        Lista todas las plantillas disponibles
        
        Returns:
            Lista de todas las PromptTemplate
        """
        pass


class PromptNotFoundError(Exception):
    """Error cuando no se encuentra una plantilla"""
    pass


class MissingVariableError(Exception):
    """Error cuando faltan variables requeridas en una plantilla"""
    pass