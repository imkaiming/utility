# Media Tools

One Bash entry point, `media.sh`, downloads media, extracts or converts audio,
and transcribes audio or video. The Python helpers perform FFmpeg conversion and
Faster Whisper transcription.

## Usage

```bash
./media.sh -c audio -i "video.mp4" -o downloads
./media.sh -c transcript -i "video.mp4"
./media.sh -c transcript -i "recording.mp3" -o transcripts -l fr
./media.sh -c download -i "https://example.com/video" -o downloads
```

- `-c`, `--command`: `audio`, `transcript`, or `download`
- `-i`, `--input`: local file or URL (download requires a URL)
- `-o`, `--output`: output directory or output filename with an extension
- `-f`, `--force`: replace an existing output
- `-l`, `--language`: transcription language; omitted means automatic detection
- `-r`, `--sample-rate`: audio output sample rate; omitted preserves the source
- `-n`, `--channels`: audio output channel count; omitted preserves the source
- `--codec`: FFmpeg audio codec

Audio extraction from video and audio transcoding default to WAV. Transcription
of video uses a temporary mono 16 kHz WAV; audio-only input is passed directly
to Faster Whisper. A URL can be used for audio extraction or transcription; the
downloaded intermediate media is temporary. `download` saves the source media.

An output ending in `/`, an existing directory, or a path without a file
extension is treated as a directory. A path with an extension is treated as a
filename. Without `-o`, audio and transcript outputs are placed beside the input;
downloads default to `downloads/`. In Git Bash, use `C:/Users/...` or `/c/Users/...`
for Windows paths.

## Requirements

- Python 3.10 or newer, Bash (Git Bash works on Windows), FFmpeg, and FFprobe
- `yt-dlp` for URL downloads
- `faster-whisper` for transcription

Create and install the environment from this folder:

```bash
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
```

On Linux or macOS, use `uv pip install --python .venv/bin/python -r requirements.txt`.
The script detects `.venv` and the legacy `venv` directory. Activation is not
required. The first transcription downloads the configured Faster Whisper model
and caches it locally.
