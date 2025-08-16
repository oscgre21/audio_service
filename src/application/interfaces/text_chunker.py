"""
Interface para divisores de texto
"""
from abc import ABC, abstractmethod
from typing import List


class TextChunker(ABC):
    """Interface para implementaciones de división de texto"""
    
    @abstractmethod
    def split(self, text: str, max_length: int) -> List[str]:
        """
        Divide texto en chunks respetando límites
        
        Args:
            text: Texto a dividir
            max_length: Longitud máxima por chunk
            
        Returns:
            List[str]: Lista de chunks de texto
        """
        pass
    
    @abstractmethod
    def estimate_chunks(self, text: str, max_length: int) -> int:
        """
        Estima cuántos chunks se generarán
        
        Args:
            text: Texto a analizar
            max_length: Longitud máxima por chunk
            
        Returns:
            int: Número estimado de chunks
        """
        pass