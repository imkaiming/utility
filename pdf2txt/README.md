# PDF to Text

Extract the embedded text from a PDF into a UTF-8 text file using
[PyMuPDF](https://pymupdf.readthedocs.io/).

## Requirements

- Python 3
- PyMuPDF

Verified locally with Python 3.14.6 and PyMuPDF 1.28.2. This utility does not
perform OCR, so scanned PDFs must be OCR-processed first.

## Setup

From this directory in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install PyMuPDF==1.28.2
```

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install PyMuPDF==1.28.2
```

## Usage

PowerShell:

```powershell
.\.venv\Scripts\python.exe pdf2txt.py input.pdf output.txt
```

Bash:

```bash
./pdf2txt.sh input.pdf output.txt
```

Both arguments are optional and default to `input.pdf` and `output.txt`.
A relative output filename is written in this utility's directory.
