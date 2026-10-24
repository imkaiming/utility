from __future__ import annotations

# Import spaces before torch/voxcpm so ZeroGPU can initialize CUDA emulation.
import spaces
import gradio as gr
from pathlib import Path
import tempfile

from configuration import GenerationSettings, load_settings
from engine import VoxCPMEngine, Waveform
from service import SpeechService


SETTINGS = load_settings(Path(__file__).resolve().parent / "config" / "default.yaml")
# Load at startup as required by ZeroGPU; optimize=False in the engine avoids torch.compile.
ENGINE = VoxCPMEngine(SETTINGS.model)
OUTPUTS = tempfile.TemporaryDirectory(prefix="voxcpm-pcm24-")


@spaces.GPU(duration=SETTINGS.runtime.gpu_seconds)
def synthesize_on_gpu(text: str, settings: GenerationSettings) -> Waveform:
    return ENGINE.synthesize(text, settings)


class ZeroGPUEngine:
    """Allocate a GPU only for inference; keep file ownership in the main process."""

    def synthesize(self, text: str, settings: GenerationSettings) -> Waveform:
        return synthesize_on_gpu(text, settings)

    def provenance(self) -> dict[str, str]:
        return ENGINE.provenance()


SERVICE = SpeechService(ZeroGPUEngine(), SETTINGS, Path(OUTPUTS.name))


def generate(text: str) -> tuple[str, str]:
    try:
        artifacts = SERVICE.generate(text)
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    return str(artifacts.wav), str(artifacts.manifest)


with gr.Blocks(
    analytics_enabled=False,
    delete_cache=(SETTINGS.runtime.artifact_ttl_seconds, SETTINGS.runtime.artifact_ttl_seconds),
) as demo:
    gr.Markdown("# VoxCPM2 speech samples\nGenerate and download 48 kHz, 24-bit mono WAV audio.")
    text = gr.Textbox(label="Text to speak", lines=6, max_lines=15)
    button = gr.Button("Generate", variant="primary")
    audio_file = gr.File(label="Download WAV")
    manifest_file = gr.File(label="Download generation record")
    button.click(
        generate, inputs=text, outputs=[audio_file, manifest_file],
        api_name="generate", concurrency_limit=1,
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1, max_size=8).launch()
