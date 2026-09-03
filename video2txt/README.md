# Video to Text

Transcribe a local video or a video URL to UTF-8 text. The utility extracts a
mono 16 kHz WAV file with FFmpeg, then transcribes it with Faster Whisper.

## Requirements

- Python 3
- [FFmpeg](https://ffmpeg.org/) available on `PATH`
- A Bash shell for `video2txt.sh`
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
```

Before running the wrapper from Git Bash, activate the environment. This also
makes the `yt-dlp` command available for URL input.

```bash
source venv/Scripts/activate
```

On Linux or macOS, create and activate the environment with:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install faster-whisper==1.2.1 yt-dlp==2026.8.19
```

FFmpeg must be installed separately on every platform.

## Usage

```bash
./video2txt.sh video.mp4
./video2txt.sh video.mp4 -o transcript.txt -l fr
./video2txt.sh "https://example.com/video" -o transcript.txt -l en
```

Options:

- `-o`, `--output`: output text file
- `-l`, `--lang`: language code; omit it for automatic detection

Without `--output`, local input uses the video's base name and URL input uses
`transcript.txt`. Temporary downloaded video and audio files are removed after
a successful run.

## Model settings

`audio2txt.py` currently uses the Faster Whisper `small` model on CPU with
`int8` computation. The model is downloaded on first use and cached locally.
