# Text to Speech

Convert UTF-8 text files into MP3 audio with Microsoft Edge TTS.

The converter supports two input modes:

- A single `.txt` file creates one MP3 in this `text2speech` folder.
- A directory creates one MP3 per text file and, by default, one combined MP3.

The default voice is `fr-FR-VivienneMultilingualNeural`.

## Requirements

- Python 3
- Bash, such as Git Bash on Windows
- An internet connection for speech synthesis
- `edge-tts`
- `imageio-ffmpeg`, or an FFmpeg installation available on `PATH`

## Setup

Run these commands from the `text2speech` folder.

### Windows with Git Bash

```bash
python -m venv venv
./venv/Scripts/python.exe -m pip install edge-tts imageio-ffmpeg
```

### Linux or macOS

```bash
python3 -m venv venv
./venv/bin/python -m pip install edge-tts imageio-ffmpeg
```

Creating `venv` is recommended. If it is missing, `text2speech.sh` falls back to
the system `python3` installation.

## Convert one text file

```bash
./text2speech.sh -i input.txt
```

This creates:

```text
text2speech/input.mp3
```

For a single file, `--output` is ignored. The MP3 is always written to the
`text2speech` folder, even when the source text is located elsewhere.

## Convert a directory of chapters

```bash
./text2speech.sh -i ./chapters
```

Text files are processed in natural filename order. Numbered names such as
`01_Introduction.txt` are recommended.

The default output is:

```text
output_mp3/
├── 01_Introduction.mp3
├── 02_Next_chapter.mp3
└── chapters_integral.mp3
```

Choose another output directory with `--output`:

```bash
./text2speech.sh -i ./chapters --output ./audio
```

Create only the chapter files without the combined MP3:

```bash
./text2speech.sh -i ./chapters --no-combine
```

## Options

| Option | Purpose | Bash default |
| --- | --- | --- |
| `-i`, `--input` | Text file or directory of text files | Required |
| `-o`, `--output` | Output directory for directory input | `output_mp3` |
| `-v`, `--voice` | Edge TTS voice | `fr-FR-VivienneMultilingualNeural` |
| `-r`, `--rate` | Speech rate | `-15%` |
| `--volume` | Speech volume | `+0%` |
| `--pitch` | Speech pitch | `+0Hz` |
| `--no-combine` | Skip the combined MP3 for directory input | Off |

Example with custom speech settings:

```bash
./text2speech.sh -i input.txt \
  --voice fr-FR-VivienneMultilingualNeural \
  --rate -10% \
  --volume +0% \
  --pitch +0Hz
```

## Languages

Vivienne is a multilingual voice. It can speak French, English, and other
supported languages, although pronunciation quality can vary. Using one primary
language per file or chapter generally gives the most predictable result.

Select another available Edge TTS voice with `--voice` when needed.

## Resuming an interrupted conversion

The conversion is resumable. Run the same command again after an interruption;
completed chunks and sufficiently complete chapter files are reused.

Temporary synthesis chunks are stored in `_temporary_audio_chunks` and removed
after their corresponding MP3 is completed.
