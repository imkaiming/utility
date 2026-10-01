import argparse
import subprocess
from pathlib import Path


def convert_to_audio(
    media_path: str,
    audio_path: str | None = None,
    sample_rate: int | None = None,
    channels: int | None = None,
    codec: str | None = None,
    overwrite: bool = False,
) -> Path:
    media = Path(media_path)
    if not media.exists():
        raise FileNotFoundError(f"Media not found: {media}")

    output = Path(audio_path) if audio_path else media.with_suffix(".wav")
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y" if overwrite else "-n",
        "-i",
        str(media),
        "-map",
        "0:a:0",
        "-vn",
    ]
    if codec:
        command.extend(["-c:a", codec])
    if sample_rate:
        command.extend(["-ar", str(sample_rate)])
    if channels:
        command.extend(["-ac", str(channels)])
    command.append(str(output))

    print(f"Writing audio: {output}")
    subprocess.run(command, check=True)
    print("Done")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract or convert the first audio stream with FFmpeg."
    )
    parser.add_argument("input", help="Local input media file")
    parser.add_argument("output", nargs="?", help="Output audio file")
    parser.add_argument("--sample-rate", type=int, help="Output sample rate in Hz")
    parser.add_argument("--channels", type=int, help="Output channel count")
    parser.add_argument("--codec", help="FFmpeg audio codec name")
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite an existing output"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    convert_to_audio(
        args.input,
        args.output,
        sample_rate=args.sample_rate,
        channels=args.channels,
        codec=args.codec,
        overwrite=args.overwrite,
    )
