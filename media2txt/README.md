# Media to Text

Transcribe a local audio file, local video, or video URL to UTF-8 text with
Faster Whisper. FFprobe inspects the actual media streams rather than relying on
the filename extension. Audio-only media is transcribed directly, while video
input is converted to a temporary mono 16 kHz WAV file first.

## Requirements

- Python 3
- [FFmpeg](https://ffmpeg.org/) tools available on `PATH`: FFprobe for stream
  detection and FFmpeg for video extraction
- A Bash shell for `media2txt.sh`
- `faster-whisper`
- `yt-dlp` for URL input

Verified locally with Python 3.14.6, Faster Whisper 1.2.1, yt-dlp 2026.8.19,
and FFmpeg. The installed Python dependencies pass `pip check`.

## Setup

From this directory in PowerShell:

```powershell
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install faster-whisper==1.2.1 yt-dlp==2026.8.19
ffmpeg -version
ffprobe -version
```

The wrapper invokes the environment's Python interpreter directly, so activation
is not required.

On Linux or macOS, create the environment with:

```bash
python3 -m venv venv
./venv/bin/python -m pip install faster-whisper==1.2.1 yt-dlp==2026.8.19
```

FFmpeg must be installed separately on every platform.

## Usage

```bash
./media2txt.sh recording.mp3
./media2txt.sh recording.mp3 -o transcript.txt -l fr
./media2txt.sh video.mp4
./media2txt.sh video.mp4 -o transcript.txt -l fr
./media2txt.sh "https://example.com/video" -o transcript.txt -l en
```

Options:

- `-o`, `--output`: output text file
- `-l`, `--lang`: language code; omit it for automatic detection

Media type is determined from its streams, so direct audio input is not limited
to a hard-coded list of filename extensions.

Without `--output`, local input uses the media file's base name and URL input
uses `transcript.txt`. Temporary downloaded video and extracted audio files are
removed after a successful run. Original local media is never removed.

## Model settings

`audio2txt.py` currently uses the Faster Whisper `small` model on CPU with
`int8` computation. The model is downloaded on first use and cached locally.
