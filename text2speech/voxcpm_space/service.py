from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from threading import Lock
import time
from uuid import uuid4

from audio import export_wav
from configuration import Settings
from engine import SynthesisEngine


@dataclass(frozen=True)
class Artifacts:
    wav: Path
    manifest: Path


class SpeechService:
    def __init__(self, engine: SynthesisEngine, settings: Settings, output_root: Path):
        self._engine = engine
        self._settings = settings
        self._root = output_root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        # Cleanup tracks only directories this instance created; never scans unrelated files.
        self._created: dict[Path, float] = {}

    def generate(self, text: str) -> Artifacts:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Enter nonempty text")
        if len(text) > self._settings.runtime.max_text_chars:
            raise ValueError(f"Text exceeds {self._settings.runtime.max_text_chars} characters")
        text = text.strip()
        with self._lock:
            self._cleanup_expired()
            waveform = self._engine.synthesize(text, self._settings.generation)
            directory = self._root / uuid4().hex
            directory.mkdir()
            wav = directory / "speech.wav"
            manifest = directory / "speech.json"
            try:
                audio = export_wav(waveform, wav)
                record = {
                    "schema_version": 1,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "engine": self._engine.provenance(),
                    "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "generation": asdict(self._settings.generation),
                    "pipeline": "VoxCPM2 waveform -> WAV PCM_24 (no intermediate codec or resampling)",
                    "source_sha256": self._source_hashes(),
                    "audio": audio,
                }
                with manifest.open("x", encoding="utf-8") as output:
                    json.dump(record, output, indent=2, allow_nan=False)
                    output.write("\n")
            except Exception:
                self._remove_owned(directory)
                raise
            self._created[directory] = time.monotonic()
            return Artifacts(wav, manifest)

    def _remove_owned(self, directory: Path) -> None:
        if directory.parent != self._root or directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside the owned output directory")
        shutil.rmtree(directory)

    def _cleanup_expired(self) -> None:
        now = time.monotonic()
        for directory, created in list(self._created.items()):
            if now - created >= self._settings.runtime.artifact_ttl_seconds:
                self._remove_owned(directory)
                del self._created[directory]

    @staticmethod
    def _source_hashes() -> dict[str, str]:
        root = Path(__file__).resolve().parent
        return {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("app.py", "configuration.py", "engine.py", "audio.py", "service.py", "requirements.txt")
        }
