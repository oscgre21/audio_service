# 📚 Higgs Audio Service - Documentación

## 🚀 Inicio Rápido

### Instalación

```bash
# 1. Clonar el repositorio
git clone <repository-url>
cd higgs-audio

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### Configuración Mínima

Editar `.env` con los valores requeridos:

```env
# Obligatorios
RABBITMQ_PASSWORD=tu_password_aqui

# Upload (si está habilitado)
UPLOAD_ENABLED=true
UPLOAD_TOKEN=tu_jwt_token_aqui
SPEECH_UPLOAD_URL=http://localhost:3000/audio/speech/upload

# Opcionales (tienen valores por defecto)
RABBITMQ_HOST=rabbit.oscgre.com
AUDIO_OUTPUT_DIR=generated_audio
```

### Ejecutar el Servicio

```bash
# Desde la raíz del proyecto
python src/main.py

# O con más logs
LOG_LEVEL=DEBUG python src/main.py
```

## 📖 Guías Esenciales

### [Arquitectura](ARCHITECTURE.md)
Entender cómo está organizado el código y dónde hacer cambios.

### [Patrón Strategy](STRATEGY_PATTERN.md) 🆕
Guía completa sobre el patrón Strategy implementado para procesamiento extensible.

### [Flujo de Componentes](COMPONENT_FLOW.md)
Diagramas detallados del flujo de datos y comunicación entre componentes.

### [Configuración de Upload](UPLOAD_CONFIGURATION.md)
Cómo configurar los múltiples endpoints de upload de audio.

### [Desarrollo](DEVELOPMENT.md)
Cómo agregar nuevas funcionalidades siguiendo las mejores prácticas.

### [API Reference](API.md)
Referencia de interfaces y clases principales.

### [Troubleshooting](TROUBLESHOOTING.md)
Solución a problemas comunes.

## 🎯 Lo Esencial que Debes Saber

### 1. **Flujo Principal Mejorado**
```
RabbitMQ → Worker → Cola Interna → Orchestrator → Estrategias → Resultado
         ↓         ↓              ↓              ↓
      Consume   Encola FIFO   Coordina     1. Validación
                                          2. Speech Processing
                                          3. Post-Processing
```

### 2. **Dónde Hacer Cambios Comunes**

| Si quieres... | Modifica... |
|--------------|-------------|
| Cambiar configuración | `.env` o `src/config/settings.py` |
| Agregar nueva estrategia | `src/application/strategies/` (ver [STRATEGY_PATTERN.md](STRATEGY_PATTERN.md)) |
| Cambiar cómo se genera audio | `src/infrastructure/audio/` |
| Modificar almacenamiento | `src/infrastructure/storage/` |
| Agregar validaciones | `src/application/strategies/validation_strategy.py` |
| Configurar endpoints de upload | `.env` (ver [UPLOAD_CONFIGURATION.md](UPLOAD_CONFIGURATION.md)) |
| Cambiar orden de procesamiento | Modificar `order` en las estrategias |
| Agregar post-procesamiento | `src/application/strategies/post_processing_strategy.py` |

### 3. **Estructura de Carpetas**
```
src/
├── config/          # Configuración
├── domain/          # Lógica de negocio
├── application/     # Casos de uso y estrategias
│   ├── strategies/  # Estrategias de procesamiento
│   └── orchestrator/# Coordinador de estrategias
├── infrastructure/  # Implementaciones
│   └── queues/     # Cola de procesamiento
└── workers/        # Worker con cola y strategies
```

### 4. **Principios Clave**
- **No modifiques interfaces** - Crea nuevas implementaciones
- **Inyecta dependencias** - No las crees dentro de clases
- **Una responsabilidad por clase** - Si hace dos cosas, divídela
- **Configura, no hardcodees** - Usa `.env` para valores

## 🔍 Ejemplos Rápidos

### Agregar Nueva Estrategia
```python
# src/application/strategies/mi_estrategia.py
class MiEstrategia(MessageProcessingStrategy):
    @property
    def name(self) -> str:
        return "mi_estrategia"
    
    @property
    def order(self) -> int:
        return 75  # Ejecuta entre validación (10) y speech (100)
    
    async def execute(self, message: Dict, context: Dict) -> StrategyResult:
        # Tu lógica aquí
        return StrategyResult(success=True, data={})
```

### Configurar Nueva Variable
```bash
# .env
QUEUE_MAX_SIZE=2000
CONCURRENT_PROCESSORS=5
ENABLE_NOTIFICATIONS=false
WEBHOOK_URL=https://mi-webhook.com/endpoint
```

### Agregar al Container
```python
# src/container.py
mi_estrategia = providers.Factory(MiEstrategia)

strategy_orchestrator = providers.Factory(
    StrategyOrchestrator,
    strategies=providers.List(
        validation_strategy,
        mi_estrategia,  # Nueva
        speech_processing_strategy,
        post_processing_strategy
    )
)
```

## 📞 Soporte

- Logs: `audio_processing.log`
- Debug: `LOG_LEVEL=DEBUG python src/main.py`
- Tests: `pytest tests/`