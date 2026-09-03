#!/bin/bash

# usage: ./video2txt.sh <video.mp4> [-o output.txt] [-l language_code]
# examples: 
#   ./video2txt.sh video.mp4 -l fr
#   ./video2txt.sh video.mp4 -o my_transcript.txt -l en

VIDEO=""
OUTPUT=""
LANG_CODE=""

# Arguments parsing
while [[ $# -gt 0 ]]; do
  case $1 in
    -o|--output)
      OUTPUT="$2"
      shift 2
      ;;
    -l|--lang)
      LANG_CODE="$2"
      shift 2
      ;;
    -*)
      echo "Unknown option: $1"
      echo "Usage: $0 <video.mp4> [-o output.txt] [-l language_code]"
      exit 1
      ;;
    *)
      # This catches the video file
      if [ -z "$VIDEO" ]; then
        VIDEO="$1"
      else
        echo "Unexpected argument: $1"
        exit 1
      fi
      shift
      ;;
  esac
done

if [ -z "$VIDEO" ]; then
    echo "Usage: $0 <video.mp4> [-o output.txt] [-l language_code]"
    exit 1
fi

# Default output name to the video's filename + .txt if -o is not provided
if [ -z "$OUTPUT" ]; then
    OUTPUT="$(basename "${VIDEO%.*}.txt")"
fi

TEMP_AUDIO="temp_audio.wav"

# step 1 : extract audio
python3 video2audio.py "$VIDEO" "$TEMP_AUDIO"
if [ $? -ne 0 ]; then
    echo "Audio extraction failed"
    exit 1
fi

# step 2 : transcription to text
python3 audio2txt.py "$TEMP_AUDIO" "$OUTPUT" "$LANG_CODE"
if [ $? -ne 0 ]; then
    echo "Transcription failed"
    rm -f "$TEMP_AUDIO"
    exit 1
fi

# step 3 : clean up
rm -f "$TEMP_AUDIO"
echo "Temporary Audio removed"
echo "Finished : $OUTPUT"