"""
Test script for transcription functionality
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.transcription import WhisperXTranscriptionService

async def test_transcription():
    """Test the transcription service"""
    print("=== Testing Transcription Service ===\n")
    
    # Create service
    service = WhisperXTranscriptionService(
        model_name="base",
        device="cpu",
        compute_type="int8"
    )
    
    # Check availability
    print(f"Service available: {service.is_available()}")
    
    if not service.is_available():
        print("WhisperX not installed. Install with:")
        print("pip install git+https://github.com/m-bain/whisperX.git")
        return
    
    # Test with a sample audio file
    test_audio = "generated_audio/test.wav"  # Replace with actual audio file
    
    if Path(test_audio).exists():
        print(f"\nTranscribing: {test_audio}")
        
        # Get SRT with alignment
        srt_content = await service.transcribe_with_alignment(
            audio_path=test_audio,
            language="en"
        )
        
        if srt_content:
            print("\nGenerated SRT:")
            print("-" * 50)
            print(srt_content)
            print("-" * 50)
            print(f"\nTotal subtitles: {srt_content.count(' --> ')}")
        else:
            print("Transcription failed or returned empty")
    else:
        print(f"\nTest audio file not found: {test_audio}")
        print("Please generate an audio file first using the main application")

    print("\n=== Test completed ===")

if __name__ == "__main__":
    asyncio.run(test_transcription())