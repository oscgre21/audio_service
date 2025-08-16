"""
Estrategia de validación para mensajes entrantes
"""
from typing import Dict, Any
import logging
from datetime import datetime
import re

from ..interfaces import MessageProcessingStrategy, StrategyResult

logger = logging.getLogger(__name__)


class ValidationStrategy(MessageProcessingStrategy):
    """
    Estrategia que valida los mensajes antes del procesamiento principal.
    
    Ejecuta primero para asegurar que los mensajes cumplan con los
    requisitos mínimos antes de pasar a estrategias más costosas.
    """
    
    def __init__(self, min_text_length: int = 1, max_text_length: int = 10000):
        """
        Inicializa la estrategia de validación.
        
        Args:
            min_text_length: Longitud mínima del texto
            max_text_length: Longitud máxima del texto
        """
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length
        self._validation_rules = self._setup_validation_rules()
    
    @property
    def name(self) -> str:
        return "validation"
    
    @property
    def order(self) -> int:
        return 10  # Ejecuta primero
    
    def _setup_validation_rules(self) -> Dict[str, Any]:
        """Configura las reglas de validación"""
        return {
            "required_fields": {
                "root": ["id", "data"],
                "data": ["speechDto"],
                "speechDto": ["original_text"]  # language is now optional
            },
            "valid_languages": ["en", "es", "pt", "fr", "de", "it", "ja", "ko", "zh"],
            "forbidden_patterns": [
                r"<script[^>]*>.*?</script>",  # Scripts
                r"javascript:",  # JavaScript URLs
                r"data:text/html",  # Data URLs peligrosas
            ]
        }
    
    async def can_handle(self, message: Dict[str, Any]) -> bool:
        """
        La validación puede manejar cualquier mensaje.
        """
        return True
    
    async def execute(self, message: Dict[str, Any], context: Dict[str, Any]) -> StrategyResult:
        """
        Ejecuta las validaciones sobre el mensaje.
        """
        start_time = datetime.now()
        validation_errors = []
        
        try:
            # Log the actual message structure for debugging
            logger.info(f"Validating message structure: {message}")
            
            # 1. Validar estructura básica
            structure_errors = self._validate_structure(message)
            validation_errors.extend(structure_errors)
            
            # Si hay errores de estructura, no continuar
            if structure_errors:
                return self._create_failure_result(
                    validation_errors, 
                    (datetime.now() - start_time).total_seconds()
                )
            
            # 2. Extraer datos para validación
            data = message.get("data", {})
            speech_dto = data.get("speechDto", {})
            original_text = speech_dto.get("original_text", "")
            language = speech_dto.get("language", "en")  # Default to English if not provided
            
            # 3. Validar contenido del texto
            text_errors = self._validate_text(original_text)
            validation_errors.extend(text_errors)
            
            # 4. Validar idioma
            if language not in self._validation_rules["valid_languages"]:
                validation_errors.append(
                    f"Unsupported language: {language}. "
                    f"Supported: {', '.join(self._validation_rules['valid_languages'])}"
                )
            
            # 5. Validar patrones peligrosos
            security_errors = self._validate_security(original_text)
            validation_errors.extend(security_errors)
            
            # 6. Validar metadata adicional
            metadata_errors = self._validate_metadata(speech_dto)
            validation_errors.extend(metadata_errors)
            
            # Preparar resultado
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if validation_errors:
                logger.warning(
                    f"Message {message.get('id')} failed validation: "
                    f"{len(validation_errors)} errors"
                )
                return self._create_failure_result(validation_errors, processing_time)
            
            # Validación exitosa - enriquecer contexto
            context["validation_passed"] = True
            context["validation_time"] = processing_time
            context["text_stats"] = {
                "length": len(original_text),
                "word_count": len(original_text.split()),
                "language": language
            }
            
            logger.info(f"Message {message.get('id')} passed validation")
            
            return StrategyResult(
                success=True,
                data={
                    "message": "Validation passed",
                    "text_length": len(original_text),
                    "language": language
                },
                processing_time=processing_time,
                should_continue=True
            )
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            return StrategyResult(
                success=False,
                data={"message": "Validation error"},
                error=str(e),
                processing_time=(datetime.now() - start_time).total_seconds(),
                should_continue=False
            )
    
    def _validate_structure(self, message: Dict[str, Any]) -> list[str]:
        """Valida la estructura del mensaje"""
        errors = []
        
        # Validar campos requeridos en el nivel raíz
        for field in self._validation_rules["required_fields"]["root"]:
            if field not in message:
                errors.append(f"Missing required field: {field}")
        
        # Si no hay campos básicos, retornar errores
        if errors:
            return errors
        
        # Validar estructura de data
        if "data" in message:
            if not isinstance(message["data"], dict):
                errors.append("Field 'data' must be an object")
            else:
                # Validar campos requeridos en data
                for field in self._validation_rules["required_fields"]["data"]:
                    if field not in message["data"]:
                        errors.append(f"Missing required field: data.{field}")
                
                # Validar estructura de speechDto
                if "speechDto" in message["data"]:
                    if not isinstance(message["data"]["speechDto"], dict):
                        errors.append("Field 'data.speechDto' must be an object")
                    else:
                        # Validar campos requeridos en speechDto
                        for field in self._validation_rules["required_fields"]["speechDto"]:
                            if field not in message["data"]["speechDto"]:
                                errors.append(f"Missing required field: data.speechDto.{field}")
        
        return errors
    
    def _validate_text(self, text: str) -> list[str]:
        """Valida el contenido del texto"""
        errors = []
        
        if not text:
            errors.append("Text is empty")
            return errors
        
        text_length = len(text)
        
        if text_length < self.min_text_length:
            errors.append(f"Text too short: {text_length} < {self.min_text_length}")
        
        if text_length > self.max_text_length:
            errors.append(f"Text too long: {text_length} > {self.max_text_length}")
        
        # Validar que no sea solo espacios en blanco
        if not text.strip():
            errors.append("Text contains only whitespace")
        
        return errors
    
    def _validate_security(self, text: str) -> list[str]:
        """Valida seguridad del contenido"""
        errors = []
        
        for pattern in self._validation_rules["forbidden_patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append(f"Text contains forbidden pattern: {pattern}")
        
        return errors
    
    def _validate_metadata(self, speech_dto: Dict[str, Any]) -> list[str]:
        """Valida metadata adicional del speech"""
        errors = []
        
        # Validar user_id si está presente
        user_id = speech_dto.get("user_uuid", speech_dto.get("userId", ""))
        if user_id and not isinstance(user_id, str):
            errors.append("user_id must be a string")
        
        # Validar velocidad si está presente
        speed = speech_dto.get("speed", 1.0)
        if speed is not None:
            try:
                speed_float = float(speed)
                if speed_float < 0.5 or speed_float > 2.0:
                    errors.append(f"Speed out of range: {speed_float} (must be 0.5-2.0)")
            except (ValueError, TypeError):
                errors.append("Speed must be a number")
        
        return errors
    
    def _create_failure_result(self, errors: list[str], processing_time: float) -> StrategyResult:
        """Crea un resultado de falla con los errores"""
        return StrategyResult(
            success=False,
            data={
                "message": "Validation failed",
                "errors": errors,
                "error_count": len(errors)
            },
            error=f"Validation failed with {len(errors)} errors",
            processing_time=processing_time,
            should_continue=False  # No continuar si la validación falla
        )