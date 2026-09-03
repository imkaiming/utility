#!/bin/bash

# Simple wrapper to run the PDF -> text converter
# Usage: ./run_pdf2txt.sh [input.pdf] [output.txt]

INPUT="${1:-input.pdf}"
OUTPUT="${2:-output.txt}"

python3 pdf2txt.py "$INPUT" "$OUTPUT"