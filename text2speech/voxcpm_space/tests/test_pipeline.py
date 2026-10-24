from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import runpy
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audio import export_wav, QUANTIZATION_STEP
from configuration import load_settings
from engine import VoxCPMEngine, Waveform
from service import SpeechService


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.waveform = Waveform(np.array([-0.5, 0.0, 0.1, 0.75], dtype=np.float32), 48000)

    def synthesize(self, text, settings):
        self.calls.append((text, settings))
        return self.waveform

    def provenance(self):
        return {"model_id": "test-engine", "model_revision": "test-revision"}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-pcm24-", dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = load_settings(ROOT / "config" / "default.yaml")

    def test_export_has_real_24bit_pcm_payload_and_preserves_samples(self):
        rng = np.random.default_rng(42)
        samples = rng.uniform(-0.9, 0.9, 4800).astype(np.float32)
        path = self.root / "speech.wav"
        record = export_wav(Waveform(samples, 48000), path)
        # Independently parse RIFF chunks, rather than trusting a filename or libsndfile metadata.
        raw = path.read_bytes()
        self.assertEqual(raw[:4], b"RIFF")
        self.assertEqual(raw[8:12], b"WAVE")
        offset, chunks = 12, {}
        while offset + 8 <= len(raw):
            name, size = struct.unpack_from("<4sI", raw, offset)
            chunks[name] = raw[offset + 8:offset + 8 + size]
            offset += 8 + size + size % 2
        fmt = struct.unpack_from("<HHIIHH", chunks[b"fmt "])
        self.assertEqual(fmt, (1, 1, 48000, 144000, 3, 24))
        self.assertEqual(len(chunks[b"data"]), len(samples) * 3)
        decoded, rate = sf.read(path, dtype="float64")
        self.assertEqual(rate, 48000)
        self.assertLessEqual(float(np.max(np.abs(decoded - samples))), QUANTIZATION_STEP)
        self.assertEqual(record["wav_sha256"], hashlib.sha256(raw).hexdigest())

    def test_rejects_invalid_waveforms_without_creating_output(self):
        bad = [
            Waveform(np.zeros(4), 24000), Waveform(np.zeros((4, 2)), 48000),
            Waveform(np.array([]), 48000), Waveform(np.array([np.nan]), 48000),
            Waveform(np.array([np.inf]), 48000), Waveform(np.array([1.0]), 48000),
            Waveform(np.array([-1.01]), 48000), Waveform(np.array([1], dtype=np.int16), 48000),
        ]
        for waveform in bad:
            with self.subTest(waveform=waveform):
                path = self.root / "bad.wav"
                with self.assertRaises(ValueError):
                    export_wav(waveform, path)
                self.assertFalse(path.exists())

    def test_preserves_existing_output(self):
        path = self.root / "speech.wav"
        path.write_bytes(b"existing user data")
        with self.assertRaises(FileExistsError):
            export_wav(FakeEngine().waveform, path)
        self.assertEqual(path.read_bytes(), b"existing user data")

    def test_configuration_rejects_unknown_duplicate_and_invalid_values(self):
        original = (ROOT / "config" / "default.yaml").read_text(encoding="utf-8")
        bad = [
            original + "unknown: true\n", original + "model: {}\n",
            original.replace("seed: 42", "seed: true"),
            original.replace("guidance_scale: 2.0", "guidance_scale: .nan"),
            original.replace("language: auto", "language: Klingon"),
            original.replace(self.settings.model.revision, "main"),
            original.replace("gpu_seconds: 60", "gpu_seconds: 0"),
            original.replace("inference_steps: 10", "inference_steps: 1.5"),
        ]
        path = self.root / "config.yaml"
        for content in bad:
            with self.subTest(content=content):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_settings(path)

    def test_service_records_provenance_and_uses_unique_paths(self):
        engine = FakeEngine()
        service = SpeechService(engine, self.settings, self.root)
        first = service.generate("Hello.")
        second = service.generate("Hello.")
        self.assertNotEqual(first.wav, second.wav)
        record = json.loads(first.manifest.read_text(encoding="utf-8"))
        self.assertEqual(record["engine"], engine.provenance())
        self.assertEqual(record["generation"]["seed"], self.settings.generation.seed)
        self.assertEqual(record["audio"]["wav_sha256"], hashlib.sha256(first.wav.read_bytes()).hexdigest())
        self.assertEqual(record["audio"]["waveform_sha256"], hashlib.sha256(engine.waveform.samples.tobytes()).hexdigest())
        self.assertEqual(record["text_sha256"], hashlib.sha256(b"Hello.").hexdigest())
        self.assertEqual(engine.calls[0], ("Hello.", self.settings.generation))
        self.assertEqual(record["source_sha256"]["audio.py"], hashlib.sha256((ROOT / "audio.py").read_bytes()).hexdigest())

    def test_invalid_text_does_not_call_engine(self):
        engine = FakeEngine()
        service = SpeechService(engine, self.settings, self.root)
        for text in ("", "  ", None, "x" * (self.settings.runtime.max_text_chars + 1)):
            with self.assertRaises(ValueError):
                service.generate(text)
        self.assertEqual(engine.calls, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_engine_downloads_pinned_model_and_returns_waveform_directly(self):
        samples = FakeEngine().waveform.samples
        model = Mock()
        model.tts_model.sample_rate = 48000
        model.generate.return_value = samples
        constructor = Mock(return_value=model)
        download = Mock(return_value="pinned-local-snapshot")
        with patch.dict(sys.modules, {
            "huggingface_hub": SimpleNamespace(snapshot_download=download),
            "voxcpm": SimpleNamespace(VoxCPM=SimpleNamespace(from_pretrained=constructor)),
        }):
            engine = VoxCPMEngine(self.settings.model)
            generation = replace(self.settings.generation, language="French")
            waveform = engine.synthesize("Bonjour.", generation)
        download.assert_called_once_with(
            repo_id="openbmb/VoxCPM2", revision=self.settings.model.revision,
        )
        constructor.assert_called_once_with(
            "pinned-local-snapshot", device="cuda", optimize=False, load_denoiser=False,
        )
        self.assertIs(waveform.samples, samples)
        self.assertEqual(waveform.sample_rate, 48000)
        call = model.generate.call_args.kwargs
        self.assertTrue(call["text"].startswith("(Speak in French."))
        self.assertTrue(call["text"].endswith(")Bonjour."))
        self.assertEqual(call["max_len"], generation.max_tokens)
        self.assertEqual(call["inference_timesteps"], generation.inference_steps)
        self.assertFalse(call["normalize"])
        self.assertFalse(call["denoise"])
        self.assertFalse(call["retry_badcase"])

    def test_export_verification_detects_corrupted_readback(self):
        with patch("audio.sf.read", return_value=(np.zeros(4), 48000)):
            with self.assertRaisesRegex(RuntimeError, "quantization"):
                export_wav(FakeEngine().waveform, self.root / "invalid.wav")

    def test_app_wiring_and_download_cache_preserve_wav_bytes(self):
        import gradio.processing_utils

        with patch("engine.VoxCPMEngine", return_value=FakeEngine()), patch(
            "tempfile.tempdir", str(self.root),
        ):
            app = runpy.run_path(str(ROOT / "app.py"), run_name="test_app")
        self.addCleanup(app["OUTPUTS"].cleanup)
        self.addCleanup(app["demo"].close)
        wav, manifest = app["generate"]("Hello from the app.")
        component = app["audio_file"]
        component.GRADIO_CACHE = str(self.root / "download-cache")
        output = component.postprocess(wav)
        cached = gradio.processing_utils.move_files_to_cache(
            output.model_dump(), component, postprocess=True,
        )
        original_hash = hashlib.sha256(Path(wav).read_bytes()).hexdigest()
        cached_hash = hashlib.sha256(Path(cached["path"]).read_bytes()).hexdigest()
        self.assertEqual(original_hash, cached_hash)
        self.assertEqual(json.loads(Path(manifest).read_text())["audio"]["wav_sha256"], cached_hash)
        with patch.dict(app["generate"].__globals__, {"synthesize_on_gpu": Mock()}) as namespace:
            with self.assertRaises(gradio.Error):
                app["generate"]("")
            namespace["synthesize_on_gpu"].assert_not_called()
        self.assertTrue(any(
            dependency["api_name"] == "generate"
            for dependency in app["demo"].config["dependencies"]
        ))

    def test_failed_export_removes_only_its_own_artifacts(self):
        sentinel = self.root / "user.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        engine = FakeEngine()
        engine.waveform = Waveform(np.array([np.nan]), 48000)
        service = SpeechService(engine, self.settings, self.root)
        with self.assertRaises(ValueError):
            service.generate("Hello")
        self.assertEqual(list(self.root.iterdir()), [sentinel])

    def test_expiration_preserves_unrelated_files(self):
        settings = replace(self.settings, runtime=replace(self.settings.runtime, artifact_ttl_seconds=60))
        service = SpeechService(FakeEngine(), settings, self.root)
        with patch("service.time.monotonic", return_value=0):
            first = service.generate("Hello")
        sentinel = self.root / "unrelated"
        sentinel.mkdir()
        with patch("service.time.monotonic", return_value=61):
            second = service.generate("World")
        self.assertFalse(first.wav.exists())
        self.assertTrue(second.wav.exists())
        self.assertTrue(sentinel.exists())


if __name__ == "__main__":
    unittest.main()
