"""
Implementación de almacenamiento local
"""
import os
import json
import aiofiles
from typing import Dict, Any, Optional
import logging

from ...application.interfaces import FileStorage

logger = logging.getLogger(__name__)


class LocalFileStorage(FileStorage):
    """Implementación de almacenamiento en sistema de archivos local"""
    
    def __init__(self, base_path: str = "generated_audio"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    async def save(self, file_path: str, content: bytes) -> str:
        """Guarda un archivo en el sistema local"""
        try:
            # Asegurar que el directorio existe
            dir_path = os.path.dirname(file_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            
            # Guardar archivo
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            logger.debug(f"File saved: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise
    
    async def save_metadata(self, id: str, metadata: Dict[str, Any]) -> None:
        """Guarda metadata como archivo JSON"""
        try:
            metadata_path = os.path.join(self.base_path, f"{id}.json")
            
            async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(metadata, indent=2, ensure_ascii=False))
            
            logger.debug(f"Metadata saved for {id}")
            
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
            raise
    
    async def read_metadata(self, id: str) -> Optional[Dict[str, Any]]:
        """Lee metadata desde archivo JSON"""
        try:
            metadata_path = os.path.join(self.base_path, f"{id}.json")
            
            if not os.path.exists(metadata_path):
                return None
            
            async with aiofiles.open(metadata_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
                
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return None
    
    async def exists(self, file_path: str) -> bool:
        """Verifica si un archivo existe"""
        return os.path.exists(file_path)
    
    async def delete(self, file_path: str) -> bool:
        """Elimina un archivo"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    async def get_size(self, file_path: str) -> int:
        """Obtiene el tamaño de un archivo"""
        try:
            if os.path.exists(file_path):
                return os.path.getsize(file_path)
            return 0
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return 0