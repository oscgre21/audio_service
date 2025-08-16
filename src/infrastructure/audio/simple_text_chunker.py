"""
Implementación simple de chunking de texto
"""
import re
from typing import List
import logging

from ...application.interfaces import TextChunker

logger = logging.getLogger(__name__)


class SimpleTextChunker(TextChunker):
    """Implementación que divide texto respetando límites de palabras"""
    
    def split(self, text: str, max_length: int) -> List[str]:
        """
        Divide el texto en chunks sin cortar palabras
        
        Args:
            text: Texto a dividir
            max_length: Longitud máxima por chunk
            
        Returns:
            List[str]: Lista de chunks
        """
        if len(text) <= max_length:
            return [text.strip()]
        
        chunks = []
        
        # Dividir primero por párrafos
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Si el párrafo es muy largo, dividirlo por oraciones
            if len(paragraph) > max_length:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                
                for sentence in sentences:
                    # Si una oración es más larga que max_length, dividirla por palabras
                    if len(sentence) > max_length:
                        words = sentence.split()
                        temp_chunk = ""
                        
                        for word in words:
                            if len(temp_chunk) + len(word) + 1 <= max_length:
                                temp_chunk = temp_chunk + " " + word if temp_chunk else word
                            else:
                                if temp_chunk:
                                    chunks.append(temp_chunk.strip())
                                temp_chunk = word
                        
                        if temp_chunk:
                            # Agregar al chunk actual si cabe
                            if len(current_chunk) + len(temp_chunk) + 1 <= max_length:
                                current_chunk = current_chunk + " " + temp_chunk if current_chunk else temp_chunk
                            else:
                                if current_chunk:
                                    chunks.append(current_chunk.strip())
                                current_chunk = temp_chunk
                    else:
                        # La oración cabe completa
                        if len(current_chunk) + len(sentence) + 1 <= max_length:
                            current_chunk = current_chunk + " " + sentence if current_chunk else sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = sentence
            else:
                # El párrafo cabe completo
                if len(current_chunk) + len(paragraph) + 2 <= max_length:  # +2 para "\n\n"
                    current_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph
        
        # Agregar el último chunk si existe
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        logger.info(f"Text split into {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            logger.debug(f"  Chunk {i+1}: {len(chunk)} characters")
        
        return chunks
    
    def estimate_chunks(self, text: str, max_length: int) -> int:
        """
        Estima cuántos chunks se generarán
        
        Args:
            text: Texto a analizar
            max_length: Longitud máxima por chunk
            
        Returns:
            int: Número estimado de chunks
        """
        if len(text) <= max_length:
            return 1
        
        # Estimación simple basada en longitud
        # Asumiendo un 10% de overhead por separación de palabras
        estimated = int(len(text) / (max_length * 0.9)) + 1
        
        return estimated