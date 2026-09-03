#!/bin/bash

# usage: ./media2txt.sh <audio_or_video_file OR url> [-o output.txt] [-l language_code]
# examples:
#   ./media2txt.sh video.mp4 -l fr
#   ./media2txt.sh recording.mp3 -l fr
#   ./media2txt.sh video.mp4 -o my_transcript.txt -l en


# 1. Detect virtual environment

if [ -f "./venv/Scripts/python.exe" ]; then
    PYTHON="./venv/Scripts/python.exe"
elif [ -f "./venv/bin/python" ]; then
    PYTHON="./venv/bin/python"
else
    PYTHON="python3"
fi

MEDIA=""
OUTPUT=""
LANG_CODE=""
IS_URL=false

# 2. Parse arguments

while [[ $# -gt 0 ]]; do
  case $1 in
    -o|--output) OUTPUT="$2"; shift 2 ;;
    -l|--lang) LANG_CODE="$2"; shift 2 ;;
    -*) echo "Unknown option: $1"; exit 1 ;;
    *)
      if [ -z "$MEDIA" ]; then MEDIA="$1"
      else echo "Unexpected argument: $1"; exit 1; fi
      shift ;;
  esac
done

if [ -z "$MEDIA" ]; then
    echo "Usage: $0 <audio_or_video_file OR url> [-o output.txt] [-l language_code]"
    exit 1
fi

# 3. Handle URL downloads
if [[ "$MEDIA" == http* ]]; then

    # Check if yt-dlp is installed in the specific Python environment
    if ! "$PYTHON" -c "import yt_dlp" &> /dev/null; then
        echo "Error: yt-dlp is missing in your Python environment."
        echo "Install it with: $PYTHON -m pip install yt-dlp"
        exit 1
    fi
    
    echo "URL detected. Downloading media..."
    # Run yt-dlp using the local Python executable (bypasses PATH issues)
    "$PYTHON" -m yt_dlp --merge-output-format mp4 -o "temp_video.mp4" "$MEDIA"
    
    if [ $? -ne 0 ]; then 
        echo "Media download failed."
        exit 1 
    fi
    IS_URL=true
    MEDIA="temp_video.mp4"
fi


# 4. Set default output name
if [ -z "$OUTPUT" ]; then
    if [ "$IS_URL" = true ]; then
        OUTPUT="transcript.txt"
    else
        OUTPUT="$(basename "${MEDIA%.*}.txt")"
    fi
fi

TEMP_AUDIO="temp_audio.wav"
AUDIO_INPUT="$TEMP_AUDIO"
TEMP_AUDIO_CREATED=false

# 5. Inspect media streams, then use audio directly or extract it from video
if ! command -v ffprobe &> /dev/null; then
    echo "Error: ffprobe is required but was not found on PATH."
    [ "$IS_URL" = true ] && rm -f "$MEDIA"
    exit 1
fi

VIDEO_STREAM=$(ffprobe -v error -select_streams V:0 -show_entries stream=index -of csv=p=0 "$MEDIA")
if [ $? -ne 0 ]; then
    echo "Unable to inspect media: $MEDIA"
    [ "$IS_URL" = true ] && rm -f "$MEDIA"
    exit 1
fi

if [ -n "$VIDEO_STREAM" ]; then
    echo "Video stream detected. Extracting audio..."
    "$PYTHON" video2audio.py "$MEDIA" "$TEMP_AUDIO"
    if [ $? -ne 0 ]; then
        echo "Audio extraction failed"
        [ "$IS_URL" = true ] && rm -f "$MEDIA"
        exit 1
    fi
    TEMP_AUDIO_CREATED=true
else
    AUDIO_STREAM=$(ffprobe -v error -select_streams a:0 -show_entries stream=index -of csv=p=0 "$MEDIA")
    if [ $? -ne 0 ] || [ -z "$AUDIO_STREAM" ]; then
        echo "No audio stream found: $MEDIA"
        [ "$IS_URL" = true ] && rm -f "$MEDIA"
        exit 1
    fi
    AUDIO_INPUT="$MEDIA"
    echo "Audio-only media detected. Skipping audio extraction."
fi

# 6. Transcribe
"$PYTHON" audio2txt.py "$AUDIO_INPUT" "$OUTPUT" "$LANG_CODE"
if [ $? -ne 0 ]; then
    echo "Transcription failed"
    [ "$TEMP_AUDIO_CREATED" = true ] && rm -f "$TEMP_AUDIO"
    [ "$IS_URL" = true ] && rm -f "$MEDIA"
    exit 1
fi

# 7. Clean up
[ "$TEMP_AUDIO_CREATED" = true ] && rm -f "$TEMP_AUDIO"
if [ "$IS_URL" = true ]; then
    rm -f "$MEDIA"
    if [ "$TEMP_AUDIO_CREATED" = true ]; then
        echo "Downloaded media and temporary audio removed"
    else
        echo "Downloaded media removed"
    fi
elif [ "$TEMP_AUDIO_CREATED" = true ]; then
    echo "Temporary audio removed"
else
    echo "Audio input transcribed directly"
fi
echo "Finished : $OUTPUT"
