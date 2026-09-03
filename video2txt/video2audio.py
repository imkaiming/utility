import subprocess
from pathlib import Path
import sys

def video2audio(video_path:str, audio_path:str = None) -> Path:
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"video not found: {video_path}")

    if audio_path is None:
        audio_path = video_path.with_suffix(".wav")
    else:
        audio_path = Path(audio_path)

    cmd = ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(audio_path)]

    print(f"Extracting audio : {audio_path}")
    subprocess.run(cmd, check=True, capture_output=True)
    print("Done")
    return audio_path

if __name__ == "__main__":
    video = sys.argv[1] if len(sys.argv) > 1 else "input.mp4"
    out = sys.argv[2] if len(sys.argv) > 2 else None
    video2audio(video, out)

    