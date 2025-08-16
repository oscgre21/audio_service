"""
SRT format generator utility
"""
import re
from typing import List, Tuple


def generate_srt_from_text(text: str, words_per_second: float = 2.5) -> str:
    """
    Generate SRT format from plain text.
    
    Args:
        text: Original text to convert
        words_per_second: Average speaking rate (default 2.5 words/second)
        
    Returns:
        Text in SRT format with timestamps
    """
    if not text or not text.strip():
        return ""
    
    # Split text into sentences (keeping the delimiter)
    sentence_endings = r'[.!?]'
    sentences = re.split(f'({sentence_endings})', text)
    
    # Combine sentence with its ending punctuation
    combined_sentences = []
    for i in range(0, len(sentences), 2):
        sentence = sentences[i].strip()
        if sentence:
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            combined_sentences.append(sentence)
    
    if not combined_sentences:
        # If no sentence endings found, treat the whole text as one subtitle
        combined_sentences = [text.strip()]
    
    # Generate SRT entries
    srt_entries = []
    current_time = 0.0
    
    for idx, sentence in enumerate(combined_sentences, 1):
        # Calculate duration based on word count
        word_count = len(sentence.split())
        duration = max(1.0, word_count / words_per_second)  # Minimum 1 second
        
        # Format timestamps
        start_time = format_srt_timestamp(current_time)
        end_time = format_srt_timestamp(current_time + duration)
        
        # Create SRT entry
        srt_entry = f"{idx}\n{start_time} --> {end_time}\n{sentence}\n"
        srt_entries.append(srt_entry)
        
        # Update current time with small pause between sentences
        current_time += duration + 0.5  # 0.5 second pause
    
    return "\n".join(srt_entries)


def format_srt_timestamp(seconds: float) -> str:
    """
    Format seconds into SRT timestamp format (HH:MM:SS,mmm)
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def split_text_for_subtitles(text: str, max_chars_per_line: int = 80) -> List[str]:
    """
    Split long text into subtitle-friendly chunks.
    
    Args:
        text: Text to split
        max_chars_per_line: Maximum characters per subtitle line
        
    Returns:
        List of text chunks suitable for subtitles
    """
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1  # +1 for space
        
        if current_length + word_length > max_chars_per_line:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                # Single word longer than max_chars_per_line
                chunks.append(word)
                current_chunk = []
                current_length = 0
        else:
            current_chunk.append(word)
            current_length += word_length
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks


def generate_advanced_srt(text: str, chunk_duration: float = 3.0) -> str:
    """
    Generate SRT with better chunking for readability.
    
    Args:
        text: Original text
        chunk_duration: Target duration per subtitle chunk in seconds
        
    Returns:
        Text in SRT format optimized for readability
    """
    if not text or not text.strip():
        return ""
    
    # Split into subtitle-friendly chunks
    chunks = split_text_for_subtitles(text, max_chars_per_line=60)
    
    # Generate SRT entries
    srt_entries = []
    current_time = 0.0
    
    for idx, chunk in enumerate(chunks, 1):
        # Format timestamps
        start_time = format_srt_timestamp(current_time)
        end_time = format_srt_timestamp(current_time + chunk_duration)
        
        # Create SRT entry
        srt_entry = f"{idx}\n{start_time} --> {end_time}\n{chunk}\n"
        srt_entries.append(srt_entry)
        
        # Update current time
        current_time += chunk_duration
    
    return "\n".join(srt_entries)