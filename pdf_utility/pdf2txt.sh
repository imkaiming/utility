#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$PROJECT_ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    echo "[ERROR] Project environment not found at $PROJECT_ROOT/.venv" >&2
    exit 1
fi

# Simple wrapper to run the PDF -> text converter
# Usage: ./run_pdf2txt.sh [input.pdf] [output.txt]

INPUT="${1:-input.pdf}"
OUTPUT="${2:-output.txt}"

"$PYTHON" "$SCRIPT_DIR/pdf2txt.py" "$INPUT" "$OUTPUT"
