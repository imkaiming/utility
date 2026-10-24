#!/bin/bash

# usage: ./text2speech.sh -i <input_path> [-o <output_dir>] [-v <voice>] [-r <rate>]
# example: ./text2speech.sh -i input.txt -v fr-FR-VivienneMultilingualNeural -r -15%

# 1. Use the single environment at the utility project root.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
if [ -f "$PROJECT_ROOT/.venv/Scripts/python.exe" ]; then
    PYTHON="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    echo "[ERROR] Project environment not found at $PROJECT_ROOT/.venv" >&2
    exit 1
fi

INPUT_DIR=""
OUTPUT_DIR="output_mp3"
VOICE="fr-FR-VivienneMultilingualNeural"
RATE="-15%"
VOLUME="+0%"
PITCH="+0Hz"
NO_COMBINE=false

# 2. Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -i|--input) INPUT_DIR="$2"; shift 2 ;;
    -o|--output) OUTPUT_DIR="$2"; shift 2 ;;
    -v|--voice) VOICE="$2"; shift 2 ;;
    -r|--rate) RATE="$2"; shift 2 ;;
    --volume) VOLUME="$2"; shift 2 ;;
    --pitch) PITCH="$2"; shift 2 ;;
    --no-combine) NO_COMBINE=true; shift ;;
    -*) echo "Unknown option: $1"; exit 1 ;;
    *) echo "Unexpected argument: $1"; exit 1 ;;
  esac
done

if [ -z "$INPUT_DIR" ]; then
    echo "Usage: $0 -i <text_file_or_directory> [-o <output_dir>] [-v <voice>] [-r <rate>]"
    echo "Example (file): $0 -i input.txt"
    echo "Example (directory): $0 -i ./chapters -v fr-FR-VivienneMultilingualNeural -r -15%"
    exit 1
fi

# 3. Check if edge-tts is installed in the environment
if ! "$PYTHON" -c "import edge_tts" &> /dev/null; then
    echo "edge-tts not found in environment. Installing..."
    "$PYTHON" -m pip install edge-tts
    if [ $? -ne 0 ]; then
        echo "Failed to install edge-tts."
        exit 1
    fi
fi

# 4. Execute python script
if [ "$NO_COMBINE" = true ]; then
    "$PYTHON" "$SCRIPT_DIR/text2speech.py" -i "$INPUT_DIR" -o "$OUTPUT_DIR" -v "$VOICE" -r "$RATE" --volume "$VOLUME" --pitch "$PITCH" --no-combine
else
    "$PYTHON" "$SCRIPT_DIR/text2speech.py" -i "$INPUT_DIR" -o "$OUTPUT_DIR" -v "$VOICE" -r "$RATE" --volume "$VOLUME" --pitch "$PITCH"
fi

if [ $? -ne 0 ]; then
    echo "Conversion failed or was interrupted."
    exit 1
fi

echo "Finished."
