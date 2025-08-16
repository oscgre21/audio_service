# 🛠️ Guía de Desarrollo

## 🚀 Setup de Desarrollo

### Prerrequisitos
- Python 3.8+
- pip
- venv
- Git

### Instalación Completa

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd higgs-audio

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# 3. Instalar dependencias de desarrollo
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Si existe

# 4. Configurar entorno
cp .env.example .env
# Editar .env con tus valores

# 5. Verificar instalación
python -m pytest tests/  # Si hay tests
python src/main.py --help
```

## 📝 Tareas Comunes de Desarrollo

### 1. Agregar Nueva Configuración

```python
# src/config/settings.py
class MiNuevaConfig(BaseSettings):
    parametro1: str = Field(..., env="MI_PARAMETRO1")
    parametro2: int = Field(default=100, env="MI_PARAMETRO2")
    
class Settings(BaseSettings):
    # Agregar aquí
    mi_config: MiNuevaConfig = MiNuevaConfig()
```

Luego agregar a `.env`:
```env
MI_PARAMETRO1=valor
MI_PARAMETRO2=200
```

### 2. Crear Nuevo Caso de Uso

```python
# src/application/use_cases/mi_nuevo_caso_uso.py
from dataclasses import dataclass
from typing import Optional
from ..interfaces import AudioGenerator, FileStorage

@dataclass
class MiResultado:
    exito: bool
    mensaje: Optional[str] = None

class MiNuevoCasoUso:
    """Descripción de qué hace este caso de uso"""
    
    def __init__(
        self,
        audio_generator: AudioGenerator,
        file_storage: FileStorage
    ):
        self.audio_generator = audio_generator
        self.file_storage = file_storage
    
    async def execute(self, parametros: Dict) -> MiResultado:
        try:
            # 1. Validar entrada
            if not parametros.get("campo_requerido"):
                return MiResultado(exito=False, mensaje="Falta campo")
            
            # 2. Ejecutar lógica
            resultado = await self._procesar(parametros)
            
            # 3. Retornar resultado
            return MiResultado(exito=True, mensaje=resultado)
            
        except Exception as e:
            return MiResultado(exito=False, mensaje=str(e))
```

### 3. Implementar Nueva Interface

```python
# src/application/interfaces/mi_servicio.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class MiServicio(ABC):
    """Interface para mi nuevo servicio"""
    
    @abstractmethod
    async def procesar(self, data: Dict[str, Any]) -> str:
        """Procesa datos y retorna resultado"""
        pass
    
    @abstractmethod
    def validar(self, data: Dict[str, Any]) -> bool:
        """Valida los datos de entrada"""
        pass
```

Implementación:
```python
# src/infrastructure/servicios/mi_servicio_impl.py
from ...application.interfaces import MiServicio

class MiServicioImpl(MiServicio):
    async def procesar(self, data: Dict[str, Any]) -> str:
        # Implementación real
        return "procesado"
    
    def validar(self, data: Dict[str, Any]) -> bool:
        return "campo" in data
```

### 4. Agregar al Container DI

```python
# src/container.py
from .infrastructure.servicios import MiServicioImpl
from .application.use_cases import MiNuevoCasoUso

class Container(containers.DeclarativeContainer):
    # ... configuración existente ...
    
    # Agregar servicio
    mi_servicio = providers.Singleton(
        MiServicioImpl,
        config=config.mi_config
    )
    
    # Agregar caso de uso
    mi_caso_uso = providers.Factory(
        MiNuevoCasoUso,
        audio_generator=audio_generator,
        file_storage=file_storage
    )
```

### 5. Crear Nueva Entidad de Dominio

```python
# src/domain/entities/mi_entidad.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

@dataclass
class MiEntidad:
    """Entidad que representa [descripción]"""
    id: str
    nombre: str
    tipo: str
    activo: bool = True
    creado_en: datetime = field(default_factory=datetime.now)
    metadatos: Dict[str, Any] = field(default_factory=dict)
    
    def validar(self) -> bool:
        """Valida que la entidad tenga datos correctos"""
        if not self.id or not self.nombre:
            return False
        
        if self.tipo not in ["tipo1", "tipo2", "tipo3"]:
            return False
            
        return True
    
    def activar(self) -> None:
        """Activa la entidad"""
        self.activo = True
    
    def desactivar(self) -> None:
        """Desactiva la entidad"""
        self.activo = False
    
    @property
    def esta_activo(self) -> bool:
        """Verifica si está activo"""
        return self.activo
```

## 🧪 Testing

### Estructura de Tests
```
tests/
├── unit/
│   ├── domain/
│   │   └── test_entities.py
│   ├── application/
│   │   └── test_use_cases.py
│   └── infrastructure/
│       └── test_implementations.py
├── integration/
│   └── test_integrations.py
└── conftest.py
```

### Ejemplo de Test Unitario

```python
# tests/unit/application/test_mi_caso_uso.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.application.use_cases import MiNuevoCasoUso

@pytest.mark.asyncio
async def test_execute_exitoso():
    # Arrange
    mock_generator = Mock()
    mock_generator.generate = AsyncMock(return_value=("path", "id"))
    
    mock_storage = Mock()
    mock_storage.save = AsyncMock(return_value="saved")
    
    caso_uso = MiNuevoCasoUso(mock_generator, mock_storage)
    
    # Act
    resultado = await caso_uso.execute({"campo_requerido": "valor"})
    
    # Assert
    assert resultado.exito is True
    mock_generator.generate.assert_called_once()

@pytest.mark.asyncio
async def test_execute_falla_sin_campo():
    # Arrange
    caso_uso = MiNuevoCasoUso(Mock(), Mock())
    
    # Act
    resultado = await caso_uso.execute({})
    
    # Assert
    assert resultado.exito is False
    assert "Falta campo" in resultado.mensaje
```

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Con coverage
pytest --cov=src

# Solo unit tests
pytest tests/unit/

# Test específico
pytest tests/unit/application/test_mi_caso_uso.py::test_execute_exitoso

# Con más detalle
pytest -vv
```

## 🐛 Debugging

### Aumentar Nivel de Logs
```bash
LOG_LEVEL=DEBUG python src/main.py
```

### Debugging con VS Code
`.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Higgs Audio",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/main.py",
            "console": "integratedTerminal",
            "env": {
                "LOG_LEVEL": "DEBUG"
            },
            "envFile": "${workspaceFolder}/.env"
        }
    ]
}
```

### Debugging con PyCharm
1. Run → Edit Configurations
2. Add New Configuration → Python
3. Script path: `src/main.py`
4. Environment variables: Cargar desde `.env`
5. Working directory: Raíz del proyecto

## 📦 Dependencias

### Agregar Nueva Dependencia
```bash
pip install nueva-libreria
pip freeze > requirements.txt
```

### Actualizar Dependencias
```bash
pip install --upgrade -r requirements.txt
```

## 🔍 Linting y Formato

### Configurar Pre-commit
```bash
pip install pre-commit
pre-commit install
```

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

### Ejecutar Manualmente
```bash
# Formatear código
black src/

# Ordenar imports
isort src/

# Verificar estilo
flake8 src/

# Type checking
mypy src/
```

## 📚 Recursos Útiles

- [Python Async IO](https://docs.python.org/3/library/asyncio.html)
- [Dependency Injector](https://python-dependency-injector.ets-labs.org/)
- [Pydantic Docs](https://pydantic-docs.helpmanual.io/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)