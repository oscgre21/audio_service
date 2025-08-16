#!/bin/bash

# Script de arranque para Higgs Audio Service
# Este script activa el entorno virtual y ejecuta el servicio

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎵 Iniciando Higgs Audio Service${NC}"
echo "===================================="

# Verificar que el entorno virtual existe
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Error: El entorno virtual no existe.${NC}"
    echo "   Por favor ejecuta primero: ./install.sh"
    exit 1
fi

# Verificar que las dependencias están instaladas
if [ ! -f "venv/bin/python" ] && [ ! -f "venv/Scripts/python.exe" ]; then
    echo -e "${RED}❌ Error: El entorno virtual parece estar corrupto.${NC}"
    echo "   Por favor ejecuta: ./install.sh"
    exit 1
fi

# Verificar que el archivo .env existe
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: El archivo .env no existe.${NC}"
    echo "   Por favor copia .env.example a .env y configura tus credenciales"
    exit 1
fi

# Activar entorno virtual
echo -e "${YELLOW}1. Activando entorno virtual...${NC}"
source venv/bin/activate
echo -e "${GREEN}✅ Entorno virtual activado${NC}"

# Verificar e instalar dependencias faltantes
echo -e "${YELLOW}   Verificando dependencias...${NC}"
python -c "import pydantic_settings" 2>/dev/null || {
    echo -e "${YELLOW}   ⚠️  Instalando dependencias faltantes...${NC}"
    pip install pydantic-settings >/dev/null 2>&1
    echo -e "${GREEN}   ✅ Dependencias actualizadas${NC}"
}

# Verificar configuración crítica
echo -e "\n${YELLOW}2. Verificando configuración...${NC}"

# Verificar RabbitMQ password
RABBITMQ_PASSWORD=$(grep RABBITMQ_PASSWORD .env | cut -d '=' -f2)
if [ "$RABBITMQ_PASSWORD" == "your_password_here" ] || [ -z "$RABBITMQ_PASSWORD" ]; then
    echo -e "${RED}⚠️  Advertencia: RABBITMQ_PASSWORD no está configurado en .env${NC}"
    echo "   El servicio no podrá conectarse a RabbitMQ sin la contraseña correcta"
    read -p "   ¿Continuar de todos modos? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ RabbitMQ configurado${NC}"
fi

# Verificar si upload está habilitado
UPLOAD_ENABLED=$(grep UPLOAD_ENABLED .env | cut -d '=' -f2)
if [ "$UPLOAD_ENABLED" == "true" ]; then
    echo -e "${BLUE}ℹ️  Upload habilitado - verificando credenciales...${NC}"
    
    # Verificar token de upload
    UPLOAD_TOKEN=$(grep UPLOAD_TOKEN .env | cut -d '=' -f2)
    if [ "$UPLOAD_TOKEN" == "your_jwt_token_here" ] || [ -z "$UPLOAD_TOKEN" ]; then
        echo -e "${YELLOW}   ⚠️  UPLOAD_TOKEN no configurado - se usará autenticación${NC}"
        
        # Verificar credenciales de autenticación
        AUTH_EMAIL=$(grep AUTH_EMAIL .env | cut -d '=' -f2)
        AUTH_PASSWORD=$(grep AUTH_PASSWORD .env | cut -d '=' -f2)
        if [ -z "$AUTH_EMAIL" ] || [ -z "$AUTH_PASSWORD" ]; then
            echo -e "${RED}   ❌ AUTH_EMAIL y AUTH_PASSWORD son requeridos para autenticación${NC}"
            echo "      Por favor configura las credenciales en .env"
            exit 1
        else
            echo -e "${GREEN}   ✅ Credenciales de autenticación configuradas${NC}"
        fi
    else
        echo -e "${GREEN}   ✅ Token de upload configurado${NC}"
    fi
else
    echo -e "${BLUE}ℹ️  Upload deshabilitado - los archivos solo se guardarán localmente${NC}"
fi

# Verificar dispositivo de audio
AUDIO_DEVICE=$(grep AUDIO_DEVICE .env | cut -d '=' -f2 || echo "cuda")
if [ "$AUDIO_DEVICE" == "cuda" ]; then
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${GREEN}✅ GPU detectada - usando CUDA${NC}"
    else
        echo -e "${YELLOW}⚠️  CUDA solicitado pero no disponible - cambiando a CPU${NC}"
        # Actualizar temporalmente la variable de entorno
        export AUDIO_DEVICE=cpu
    fi
else
    echo -e "${BLUE}ℹ️  Usando CPU para procesamiento${NC}"
fi

# Verificar transcripción
TRANSCRIPTION_ENABLED=$(grep TRANSCRIPTION_ENABLED .env | cut -d '=' -f2)
if [ "$TRANSCRIPTION_ENABLED" == "true" ]; then
    if ! command -v ffmpeg &> /dev/null; then
        echo -e "${YELLOW}⚠️  Transcripción habilitada pero ffmpeg no está instalado${NC}"
        echo "   La transcripción no funcionará sin ffmpeg"
    else
        echo -e "${GREEN}✅ Transcripción habilitada con WhisperX${NC}"
    fi
else
    echo -e "${BLUE}ℹ️  Transcripción deshabilitada${NC}"
fi

# Crear directorios si no existen
echo -e "\n${YELLOW}3. Verificando directorios...${NC}"
mkdir -p generated_audio
mkdir -p generated_audio/temp_chunks
mkdir -p logs
echo -e "${GREEN}✅ Directorios verificados${NC}"

# Mostrar información del entorno
echo -e "\n${BLUE}===================================="
echo "Configuración del servicio:"
echo "====================================\n"
echo -e "🔧 Entorno: $(grep ENVIRONMENT .env | cut -d '=' -f2 || echo 'development')"
echo -e "📊 Log level: $(grep LOG_LEVEL .env | cut -d '=' -f2 || echo 'INFO')"
echo -e "🖥️  Dispositivo: ${AUDIO_DEVICE:-cuda}"
echo -e "🎯 Procesadores concurrentes: $(grep CONCURRENT_PROCESSORS .env | cut -d '=' -f2 || echo '3')"
echo -e "📝 Transcripción: ${TRANSCRIPTION_ENABLED:-false}"
echo -e "☁️  Upload: ${UPLOAD_ENABLED:-false}"
echo -e "\n====================================${NC}"

# Opciones de ejecución
echo -e "\n${YELLOW}4. Selecciona modo de ejecución:${NC}"
echo "   1) Normal - Ejecutar servicio"
echo "   2) Debug - Ejecutar con logging detallado"
echo "   3) Test - Verificar conexión a RabbitMQ"
echo "   4) Dry run - Simular procesamiento sin consumir mensajes"
read -p "Opción (1-4) [1]: " -n 1 -r MODE
echo

case $MODE in
    2)
        echo -e "\n${YELLOW}Iniciando en modo DEBUG...${NC}"
        export LOG_LEVEL=DEBUG
        python src/main.py
        ;;
    3)
        echo -e "\n${YELLOW}Verificando conexión a RabbitMQ...${NC}"
        python -c "
import pika
import os
from dotenv import load_dotenv
load_dotenv()

try:
    credentials = pika.PlainCredentials(
        os.getenv('RABBITMQ_USERNAME', 'admin'),
        os.getenv('RABBITMQ_PASSWORD')
    )
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.getenv('RABBITMQ_HOST', 'rabbit.oscgre.com'),
            port=int(os.getenv('RABBITMQ_PORT', 5672)),
            virtual_host=os.getenv('RABBITMQ_VHOST', '/'),
            credentials=credentials
        )
    )
    connection.close()
    print('✅ Conexión a RabbitMQ exitosa')
except Exception as e:
    print(f'❌ Error conectando a RabbitMQ: {e}')
"
        ;;
    4)
        echo -e "\n${YELLOW}Iniciando en modo DRY RUN...${NC}"
        echo -e "${BLUE}ℹ️  El servicio se conectará pero no consumirá mensajes${NC}"
        export DRY_RUN=true
        python src/main.py
        ;;
    *)
        echo -e "\n${GREEN}🚀 Iniciando servicio...${NC}"
        echo -e "${BLUE}ℹ️  Presiona Ctrl+C para detener${NC}\n"
        python src/main.py
        ;;
esac

# Manejar salida
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✅ Servicio detenido correctamente${NC}"
else
    echo -e "\n${RED}❌ El servicio terminó con error (código: $EXIT_CODE)${NC}"
    echo -e "   Revisa los logs en: ${YELLOW}audio_processing.log${NC}"
fi

# Desactivar entorno virtual
deactivate 2>/dev/null || true

exit $EXIT_CODE