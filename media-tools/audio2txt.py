from pathlib import Path
from faster_whisper import WhisperModel
import sys

# | Model | Parameters | Disk size (approx) | RAM / VRAM needed | Relative speed |
# | --- | --- | --- | --- | --- |
# | tiny | 39 M | ~75 MB | ~1 GB | ~10x |
# | base | 74 M | ~140-150 MB | ~1 GB | ~7x |
# | small | 244 M | ~460-500 MB | ~2 GB | ~4x |
# | medium | 769 M | ~1.5 GB | ~5 GB | ~2x |
# | large-v3 | 1550 M | ~2.9-3.1 GB | ~10 GB | 1x |
# | turbo (large-v3-turbo) | 809 M | ~1.5-1.6 GB | ~6 GB | ~8x |

# ============================================================
MODEL_SIZE = "small"         # options: "tiny", "base", "small", "medium", "large-v3", "turbo"
DEVICE = "cpu"               # "cpu" or "cuda"
COMPUTE_TYPE = "int8"        # "int8", "float16", "float32" (int8 is fastest on CPU) (float16 for GPU)
# ============================================================

# the model is downloaded and cached in : C:\Users\<user_name>\.cache\huggingface\hub
# clearing the cache : rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper-small

def audio2text(audio_path: str, output_txt:str = None, language: str = None) -> str:
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found : {audio_path}")

    print(f"Loading {MODEL_SIZE}  model...")
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)

    print("Transcription started")

    # Base transcription arguments
    transcribe_args = {
        "beam_size": 5,
        "vad_filter": True,
        "condition_on_previous_text": False
    }
    
    # Add language parameter if specified and valid
    if language and language.lower() not in ("auto", "none", ""):
        transcribe_args["language"] = language
        print(f"Forcing language: {language}")
        
    segments, info = model.transcribe(str(audio_path), **transcribe_args)

    # Filter out empty segments to avoid double spaces
    text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())

    if output_txt is None:
        output_txt = audio_path.with_suffix(".txt")
    else:
        output_txt = Path(output_txt)

    output_txt.write_text(text, encoding="utf-8")
    print(f"Done : {output_txt}")
    print(f"Detected language: {info.language} (prob {info.language_probability:.2f})")
    return text

if __name__ == "__main__":
    audio = sys.argv[1] if len(sys.argv) > 1 else "input.wav"
    
    # Handle empty string passed from bash for the output file
    out = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "" else None
    
    # Read language argument
    lang = sys.argv[3] if len(sys.argv) > 3 else None
    
    audio2text(audio, out, lang)
