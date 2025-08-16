"""
Interface para almacenamiento de archivos
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os


class FileStorage(ABC):
    """Interface para implementaciones de almacenamiento"""
    
    @abstractmethod
    async def save(self, file_path: str, content: bytes) -> str:
        """
        Guarda un archivo
        
        Args:
            file_path: Ruta donde guardar el archivo
            content: Contenido del archivo
            
        Returns:
            str: Ruta final del archivo guardado
        """
        pass
    
    @abstractmethod
    async def save_metadata(self, id: str, metadata: Dict[str, Any]) -> None:
        """
        Guarda metadata asociada a un ID
        
        Args:
            id: Identificador único
            metadata: Diccionario con metadata
        """
        pass
    
    @abstractmethod
    async def read_metadata(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Lee metadata asociada a un ID
        
        Args:
            id: Identificador único
            
        Returns:
            Optional[Dict[str, Any]]: Metadata o None si no existe
        """
        pass
    
    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """Verifica si un archivo existe"""
        pass
    
    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """
        Elimina un archivo
        
        Returns:
            bool: True si se eliminó, False si no existía
        """
        pass
    
    @abstractmethod
    async def get_size(self, file_path: str) -> int:
        """Obtiene el tamaño de un archivo en bytes"""
        pass