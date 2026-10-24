from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from typing import Protocol

import numpy as np

from configuration import GenerationSettings, ModelSettings


@dataclass(frozen=True)
class Waveform:
    samples: np.ndarray
    sample_rate: int


class SynthesisEngine(Protocol):
    def synthesize(self, text: str, settings: GenerationSettings) -> Waveform: ...

    def provenance(self) -> dict[str, str]: ...


class VoxCPMEngine:
    def __init__(self, settings: ModelSettings):
        # Imported only when constructing the real engine, keeping CPU export tests lightweight.
        from huggingface_hub import snapshot_download
        from voxcpm import VoxCPM

        model_path = snapshot_download(repo_id=settings.id, revision=settings.revision)
        self._model = VoxCPM.from_pretrained(
            model_path, device="cuda", optimize=False, load_denoiser=False,
        )
        self._settings = settings

    def synthesize(self, text: str, settings: GenerationSettings) -> Waveform:
        # VoxCPM2 accepts natural-language voice instructions, not a language= argument.
        instructions = []
        if settings.language != "auto":
            instructions.append(f"Speak in {settings.language}.")
        if settings.voice_description:
            instructions.append(settings.voice_description)
        prefix = f"({' '.join(instructions)})" if instructions else ""
        samples = self._model.generate(
            text=prefix + text,
            seed=settings.seed,
            cfg_value=settings.guidance_scale,
            inference_timesteps=settings.inference_steps,
            max_len=settings.max_tokens,
            normalize=False,
            denoise=False,
            retry_badcase=False,
        )
        return Waveform(samples, self._model.tts_model.sample_rate)

    def provenance(self) -> dict[str, str]:
        return {
            "model_id": self._settings.id,
            "model_revision": self._settings.revision,
            "voxcpm_version": version("voxcpm"),
        }
