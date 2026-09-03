from __future__ import annotations
import argparse
import asyncio
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print('Missing dependency: edge-tts. Install it via pip.')
    sys.exit(1)

TEMP_DIR_NAME = "_temporary_audio_chunks"
MAX_CHARS = 2600
MAX_RETRIES = 8

def natural_key(path: Path) -> list[object]:
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', path.name)]

def spoken_title(path: Path) -> str:
    title = path.stem
    title = re.sub(r'^\d+', '', title)
    title = title.replace('_', ' ')
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def split_long_piece(piece: str, max_chars: int) -> list[str]:
    if len(piece) <= max_chars:
        return [piece]
    parts: list[str] = []
    remaining = piece.strip()
    while len(remaining) > max_chars:
        window = remaining[:max_chars + 1]
        cut = max(window.rfind('; '), window.rfind(': '), window.rfind(', '), window.rfind(' '))
        if cut < max_chars * 0.55:
            cut = max_chars
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return parts

def chunk_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?…])\s+', text)
    expanded: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            expanded.extend(split_long_piece(sentence, max_chars))
    chunks: list[str] = []
    current = ''
    for piece in expanded:
        candidate = f'{current} {piece}'.strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = piece
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks

async def synthesize_chunk(text: str, output_path: Path, voice: str, rate: str, volume: str, pitch: str) -> None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            communicate = edge_tts.Communicate(
                text=text, voice=voice, rate=rate, volume=volume, pitch=pitch
            )
            await communicate.save(str(output_path))
            if output_path.exists() and output_path.stat().st_size > 1024:
                return
            raise RuntimeError('The service returned an empty audio file.')
        except Exception as exc:
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            if attempt == MAX_RETRIES:
                raise RuntimeError(f'Failed after {MAX_RETRIES} attempts: {exc}') from exc
            delay = min(60, 2 ** attempt)
            print(f'    temporary error: {exc}\n    retrying in {delay} seconds...')
            await asyncio.sleep(delay)

def get_ffmpeg_exe() -> str:
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("Error: ffmpeg not found in system PATH, and imageio-ffmpeg is not installed.")
        sys.exit(1)

def ffmpeg_concat(inputs: list[Path], output: Path) -> None:
    ffmpeg = get_ffmpeg_exe()
    list_file = output.with_suffix('.concat.txt')
    lines = []
    for item in inputs:
        escaped = str(item.resolve()).replace("'", "'\''")
        lines.append(f"file '{escaped}'")
    list_file.write_text('\n'.join(lines), encoding='utf-8')
    cmd = [
        ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
        '-f', 'concat', '-safe', '0', '-i', str(list_file),
        '-c', 'copy', str(output),
    ]
    try:
        subprocess.run(cmd, check=True)
    finally:
        list_file.unlink(missing_ok=True)

async def make_chapter(text_file: Path, chapter_number: int, total: int, output_dir: Path, temp_dir: Path, voice: str, rate: str, volume: str, pitch: str, announce_title: bool = True) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    chapter_name = text_file.stem
    output = output_dir / f'{chapter_name}.mp3'
    
    if output.exists() and output.stat().st_size > 100_000:
        print(f'[{chapter_number}/{total}] Already complete: {output.name}')
        return output

    title = spoken_title(text_file) if announce_title else ''
    text = text_file.read_text(encoding='utf-8').strip()
    narration = f'{title}. {text}' if title else text
    chunks = chunk_text(narration)

    chapter_temp = temp_dir / chapter_name
    chapter_temp.mkdir(parents=True, exist_ok=True)

    display_name = title or text_file.name
    print(f'[{chapter_number}/{total}] {display_name}: {len(chunks)} synthesis chunks')
    chunk_files: list[Path] = []

    for i, chunk in enumerate(chunks, start=1):
        chunk_file = chapter_temp / f'{i:04d}.mp3'
        chunk_files.append(chunk_file)
        if chunk_file.exists() and chunk_file.stat().st_size > 1024:
            print(f'  chunk {i}/{len(chunks)} already complete')
            continue
        print(f'  synthesizing chunk {i}/{len(chunks)}')
        await synthesize_chunk(chunk, chunk_file, voice, rate, volume, pitch)
        await asyncio.sleep(0.25)

    ffmpeg_concat(chunk_files, output)
    shutil.rmtree(chapter_temp, ignore_errors=True)
    print(f'  created: {output}')
    return output

async def run(input_path: Path, output_dir: Path, voice: str, rate: str, volume: str, pitch: str, make_single: bool) -> None:
    single_file = input_path.is_file()

    if single_file:
        if input_path.suffix.lower() != '.txt':
            raise ValueError(f'Input file must be a .txt file: {input_path}')
        project_dir = Path(__file__).resolve().parent
        chapter_files = [input_path]
        output_dir = project_dir
        output_display = project_dir / f'{input_path.stem}.mp3'
        temp_dir = project_dir / TEMP_DIR_NAME
    elif input_path.is_dir():
        chapter_files = sorted(
            (path for path in input_path.iterdir() if path.is_file() and path.suffix.lower() == '.txt'),
            key=natural_key,
        )
        if not chapter_files:
            raise FileNotFoundError(f'No .txt files found in {input_path}')
        output_display = output_dir
        temp_dir = input_path / TEMP_DIR_NAME
    else:
        raise FileNotFoundError(f'Input file or directory not found: {input_path}')
    
    print(f'Text-to-Speech Audio Converter')
    print(f'Voice: {voice} | Rate: {rate}')
    print(f'Input: {input_path}')
    print(f'Output: {output_display}')
    print('The conversion is resumable. Existing completed chapters are skipped.\n')

    chapter_mp3s: list[Path] = []
    for n, text_file in enumerate(chapter_files, start=1):
        chapter_mp3s.append(await make_chapter(
            text_file, n, len(chapter_files), output_dir, temp_dir,
            voice, rate, volume, pitch, announce_title=not single_file,
        ))

    if make_single and not single_file:
        combined = output_dir / f'{input_path.name}_integral.mp3'
        print('\nCombining all chapters into one MP3...')
        ffmpeg_concat(chapter_mp3s, combined)
        print(f'Created: {combined}')

    if temp_dir.exists() and not any(temp_dir.iterdir()):
        temp_dir.rmdir()
    print('\nConversion complete.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert text chapters to an audiobook using Edge-TTS.")
    parser.add_argument("-i", "--input", required=True, help="A .txt file or a directory containing chapter .txt files.")
    parser.add_argument("-o", "--output", default="output_mp3", help="Directory for folder-input MP3 files; single-file output is written beside this script (default: output_mp3).")
    parser.add_argument("-v", "--voice", default="fr-FR-VivienneMultilingualNeural", help="Edge-TTS voice (default: fr-FR-VivienneMultilingualNeural).")
    parser.add_argument("-r", "--rate", default="-0%", help="Speech rate, e.g., '-15%%' or '+10%%' (default: -0%%).")
    parser.add_argument("--volume", default="+0%", help="Speech volume (default: +0%%).")
    parser.add_argument("--pitch", default="+0Hz", help="Speech pitch (default: +0Hz).")
    parser.add_argument("--no-combine", action="store_true", help="Skip creating the single combined MP3.")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run(
            input_path=Path(args.input).resolve(),
            output_dir=Path(args.output).resolve(),
            voice=args.voice, rate=args.rate, volume=args.volume, pitch=args.pitch,
            make_single=not args.no_combine
        ))
    except KeyboardInterrupt:
        print('\nStopped. Run the script again to resume from the existing chunks.')
        sys.exit(130)
