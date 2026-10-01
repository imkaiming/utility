#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Prefer the environment created by `uv venv .venv`; retain support for `venv`.
if [[ -f ".venv/Scripts/python.exe" ]]; then
  PYTHON=".venv/Scripts/python.exe"
elif [[ -f ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
elif [[ -f "venv/Scripts/python.exe" ]]; then
  PYTHON="venv/Scripts/python.exe"
elif [[ -f "venv/bin/python" ]]; then
  PYTHON="venv/bin/python"
else
  PYTHON="python3"
fi

TEMP_DIR=""
cleanup() {
  if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
    rm -rf -- "$TEMP_DIR"
  fi
}
trap cleanup EXIT

die() { echo "[ERROR] $*" >&2; exit 1; }
require_command() {
  command -v "$1" >/dev/null 2>&1 || die "$1 is required but was not found on PATH."
}
require_python_package() {
  "$PYTHON" -c "import $1" >/dev/null 2>&1 ||
    die "$1 is missing from $PYTHON. Install the project dependencies first."
}
is_url() { [[ "$1" == http://* || "$1" == https://* ]]; }

usage() {
  cat <<'EOF'
Usage:
  ./media.sh -c audio      -i <file-or-url> [-o <directory-or-audio-file>] [audio options]
  ./media.sh -c transcript -i <file-or-url> [-o <directory-or-text-file>] [-l <language>]
  ./media.sh -c download   -i <url>          [-o <directory-or-media-file>]

Required:
  -c, --command NAME       Operation: audio, transcript, or download
  -i, --input PATH_OR_URL  Local media path or supported URL

Common options:
  -o, --output PATH        Output directory, or output filename with extension
  -f, --force              Replace an existing output file
  -h, --help               Show this help

Audio options:
  -r, --sample-rate HZ     Set output sample rate (otherwise preserve the source)
  -n, --channels COUNT     Set output channel count (otherwise preserve the source)
      --codec NAME         Set the FFmpeg audio codec

Transcript options:
  -l, --language CODE      Language code; omit for automatic detection

Examples:
  ./media.sh -c audio -o downloads -i 'C:/Users/kai/dev/utility/media-tools/video.mp4'
  ./media.sh -c transcript -i 'C:/Users/kai/dev/utility/media-tools/video.mp4'
  ./media.sh -c transcript -i 'recording.mp3' -o transcripts -l fr
  ./media.sh -c download -i 'https://example.com/video'

An output path ending in a slash, naming an existing directory, or lacking a
file extension is treated as a directory. A path with an extension is a file.
In Git Bash, Windows paths can be written as C:/Users/... or /c/Users/....
EOF
}

convert_windows_path() {
  local path="$1"
  if [[ "$path" =~ ^[A-Za-z]:[\\/] ]] && command -v cygpath >/dev/null 2>&1; then
    cygpath -u -- "$path"
  else
    printf '%s\n' "$path"
  fi
}

output_is_directory() {
  local path="$1"
  [[ "$path" == */ || -d "$path" || "${path##*/}" != *.* ]]
}

output_path() {
  local requested="$1" input="$2" extension="$3"
  if [[ -z "$requested" ]]; then
    if is_url "$input"; then
      mkdir -p -- "$SCRIPT_DIR/downloads"
      printf '%s\n' "$SCRIPT_DIR/downloads/media.$extension"
      return
    fi
    printf '%s\n' "${input%.*}.$extension"
  elif output_is_directory "$requested"; then
    mkdir -p -- "$requested"
    local name="media"
    if ! is_url "$input"; then name="$(basename -- "${input%.*}")"; fi
    printf '%s/%s.%s\n' "${requested%/}" "$name" "$extension"
  else
    mkdir -p -- "$(dirname -- "$requested")"
    printf '%s\n' "$requested"
  fi
}

download_media() {
  local url="$1" template="$2"
  require_command ffmpeg
  require_python_package yt_dlp
  mkdir -p -- "$(dirname -- "$template")"
  local args=(--merge-output-format mp4)
  [[ "$force" == true ]] && args+=(--force-overwrites)
  "$PYTHON" -m yt_dlp "${args[@]}" -o "$template" "$url"
}

command_name=""
input=""
output=""
language=""
sample_rate=""
channels=""
codec=""
force=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--command) [[ $# -ge 2 ]] || die "$1 requires a value."; command_name="$2"; shift 2 ;;
    -i|--input) [[ $# -ge 2 ]] || die "$1 requires a value."; input="$2"; shift 2 ;;
    -o|--output) [[ $# -ge 2 ]] || die "$1 requires a value."; output="$2"; shift 2 ;;
    -l|--language) [[ $# -ge 2 ]] || die "$1 requires a value."; language="$2"; shift 2 ;;
    -r|--sample-rate) [[ $# -ge 2 ]] || die "$1 requires a value."; sample_rate="$2"; shift 2 ;;
    -n|--channels) [[ $# -ge 2 ]] || die "$1 requires a value."; channels="$2"; shift 2 ;;
    --codec) [[ $# -ge 2 ]] || die "$1 requires a value."; codec="$2"; shift 2 ;;
    -f|--force) force=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1 (use --help for usage)." ;;
  esac
done

[[ -n "$command_name" ]] || { usage >&2; die "Choose an operation with -c."; }
[[ -n "$input" ]] || die "Provide an input path or URL with -i."
input="$(convert_windows_path "$input")"
if [[ -n "$output" ]]; then output="$(convert_windows_path "$output")"; fi
source_input="$input"

case "$command_name" in
  audio)
    require_command ffmpeg
    require_command ffprobe
    if is_url "$input"; then
      TEMP_DIR="$(mktemp -d)"
      download_media "$input" "$TEMP_DIR/source.%(ext)s"
      input="$(find "$TEMP_DIR" -maxdepth 1 -type f | head -n 1)"
      [[ -n "$input" ]] || die "The URL did not produce a media file."
    fi
    [[ -f "$input" ]] || die "Media file not found: $input"
    ffprobe -v error "$input" >/dev/null 2>&1 || die "Unable to inspect media: $input"
    ffprobe -v error -select_streams a:0 -show_entries stream=index -of csv=p=0 "$input" | grep -q . ||
      die "No audio stream found: $input"
    target="$(output_path "$output" "$source_input" wav)"
    [[ ! -e "$target" || "$force" == true ]] || die "Output already exists: $target (use -f to replace it)."
    args=("$input" "$target")
    [[ -n "$sample_rate" ]] && args+=(--sample-rate "$sample_rate")
    [[ -n "$channels" ]] && args+=(--channels "$channels")
    [[ -n "$codec" ]] && args+=(--codec "$codec")
    [[ "$force" == true ]] && args+=(--overwrite)
    "$PYTHON" video2audio.py "${args[@]}"
    ;;
  transcript)
    require_command ffmpeg
    require_command ffprobe
    if is_url "$input"; then
      TEMP_DIR="$(mktemp -d)"
      download_media "$input" "$TEMP_DIR/source.%(ext)s"
      input="$(find "$TEMP_DIR" -maxdepth 1 -type f | head -n 1)"
      [[ -n "$input" ]] || die "The URL did not produce a media file."
    fi
    [[ -f "$input" ]] || die "Media file not found: $input"
    ffprobe -v error "$input" >/dev/null 2>&1 || die "Unable to inspect media: $input"
    ffprobe -v error -select_streams a:0 -show_entries stream=index -of csv=p=0 "$input" | grep -q . ||
      die "No audio stream found: $input"
    target="$(output_path "$output" "$source_input" txt)"
    [[ ! -e "$target" || "$force" == true ]] || die "Output already exists: $target (use -f to replace it)."
    audio_input="$input"
    if ffprobe -v error -select_streams V:0 -show_entries stream=index -of csv=p=0 "$input" | grep -q .; then
      if [[ -z "$TEMP_DIR" ]]; then TEMP_DIR="$(mktemp -d)"; fi
      audio_input="$TEMP_DIR/transcription.wav"
      "$PYTHON" video2audio.py "$input" "$audio_input" --sample-rate 16000 --channels 1 --codec pcm_s16le --overwrite
    fi
    require_python_package faster_whisper
    "$PYTHON" audio2txt.py "$audio_input" "$target" "$language"
    ;;
  download)
    is_url "$input" || die "download requires an http:// or https:// URL."
    if [[ -z "$output" ]]; then output="$SCRIPT_DIR/downloads"; fi
    if output_is_directory "$output"; then
      mkdir -p -- "$output"
      template="$output/%(title)s.%(ext)s"
    else
      mkdir -p -- "$(dirname -- "$output")"
      template="$output"
    fi
    download_media "$input" "$template"
    ;;
  *) die "Unknown operation '$command_name'. Choose audio, transcript, or download." ;;
esac
