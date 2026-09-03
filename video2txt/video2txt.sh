#!/bin/bash

# usage: ./video2txt.sh <video.mp4 OR url> [-o output.txt] [-l language_code]
# examples: 
#   ./video2txt.sh video.mp4 -l fr
#   ./video2txt.sh video.mp4 -o my_transcript.txt -l en


# 1. Detect virtual environment

if [ -f "./venv/Scripts/python.exe" ]; then
    PYTHON="./venv/Scripts/python.exe"
elif [ -f "./venv/bin/python" ]; then
    PYTHON="./venv/bin/python"
else
    PYTHON="python3"
fi

VIDEO=""
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
      if [ -z "$VIDEO" ]; then VIDEO="$1"
      else echo "Unexpected argument: $1"; exit 1; fi
      shift ;;
  esac
done

if [ -z "$VIDEO" ]; then
    echo "Usage: $0 <video.mp4 OR url> [-o output.txt] [-l language_code]"
    exit 1
fi

# 3. Handle URL downloads
if [[ "$VIDEO" == http* ]]; then

    # Check if yt-dlp is installed in the specific Python environment
    if ! $PYTHON -c "import yt_dlp" &> /dev/null; then
        echo "Error: yt-dlp is missing in your Python environment."
        echo "Activate your venv and run: pip install yt-dlp"
        exit 1
    fi
    
    echo "URL detected. Downloading video..."
    # Run yt-dlp using the local Python executable (bypasses PATH issues)
    $PYTHON -m yt_dlp --merge-output-format mp4 -o "temp_video.mp4" "$VIDEO"
    
    if [ $? -ne 0 ]; then 
        echo "Video download failed."
        exit 1 
    fi
    IS_URL=true
    VIDEO="temp_video.mp4"
fi


# 4. Set default output name
if [ -z "$OUTPUT" ]; then
    if [ "$IS_URL" = true ]; then
        OUTPUT="transcript.txt"
    else
        OUTPUT="$(basename "${VIDEO%.*}.txt")"
    fi
fi

TEMP_AUDIO="temp_audio.wav"

# 5. Extract audio
$PYTHON video2audio.py "$VIDEO" "$TEMP_AUDIO"
if [ $? -ne 0 ]; then
    echo "Audio extraction failed"
    [ "$IS_URL" = true ] && rm -f "$VIDEO"
    exit 1
fi

# 6. Transcribe
$PYTHON audio2txt.py "$TEMP_AUDIO" "$OUTPUT" "$LANG_CODE"
if [ $? -ne 0 ]; then
    echo "Transcription failed"
    rm -f "$TEMP_AUDIO"
    [ "$IS_URL" = true ] && rm -f "$VIDEO"
    exit 1
fi

# 7. Clean up
rm -f "$TEMP_AUDIO"
if [ "$IS_URL" = true ]; then
    rm -f "$VIDEO"
    echo "Downloaded video and temporary audio removed"
else
    echo "Temporary audio removed"
fi
echo "Finished : $OUTPUT"