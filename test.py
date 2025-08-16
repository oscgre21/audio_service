from boson_multimodal.serve.serve_engine import HiggsAudioServeEngine, HiggsAudioResponse
from boson_multimodal.data_types import ChatMLSample, Message, AudioContent
import torch
import torchaudio
import time
import click
import base64

MODEL_PATH = "bosonai/higgs-audio-v2-generation-3B-base"
AUDIO_TOKENIZER_PATH = "bosonai/higgs-audio-v2-tokenizer"

# Usar la voz belinda (asumiendo que tienes el repo clonado)
ref_audio_path = "examples/voice_prompts/belinda.wav"
# O para broom_salesman:
# ref_audio_path = "examples/voice_prompts/broom_salesman.wav"

# Encode audio file as base64
with open(ref_audio_path, "rb") as audio_file:
    ref_audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")

system_prompt = (
    "Generate audio following instruction.\n\n<|scene_desc_start|>\nAudio is recorded from a quiet room.\n<|scene_desc_end|>"
)

reference_text = "In the small corner bookstore, among dusty shelves and forgotten books, lived Hope."

messages = [
    Message(
        role="system",
        content=system_prompt,
    ),
    Message(
        role="assistant",
        content=AudioContent(raw_audio=ref_audio_base64, audio_url="placeholder"),
    ),
    Message(
        role="user",
        content=""" The word is: "to" """,
    ),
]

device = "cuda" if torch.cuda.is_available() else "mps"
serve_engine = HiggsAudioServeEngine(MODEL_PATH, AUDIO_TOKENIZER_PATH, device=device)

output: HiggsAudioResponse = serve_engine.generate(
    chat_ml_sample=ChatMLSample(messages=messages),
    max_new_tokens=1024,
    temperature=0.1,
    top_p=0.95,
    top_k=50,
    stop_strings=["<|end_of_text|>", "<|eot_id|>"],
    seed=12345,  # Seed fijo para consistencia
)

torchaudio.save(f"output_belinda.wav", torch.from_numpy(output.audio)[None, :], output.sampling_rate)