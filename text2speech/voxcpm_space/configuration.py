from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
from typing import Any

import yaml


LANGUAGES = frozenset({
    "auto", "Arabic", "Burmese", "Chinese", "Danish", "Dutch", "English",
    "Finnish", "French", "German", "Greek", "Hebrew", "Hindi", "Indonesian",
    "Italian", "Japanese", "Khmer", "Korean", "Lao", "Malay", "Norwegian",
    "Polish", "Portuguese", "Russian", "Spanish", "Swahili", "Swedish",
    "Tagalog", "Thai", "Turkish", "Vietnamese",
})


@dataclass(frozen=True)
class ModelSettings:
    id: str
    revision: str


@dataclass(frozen=True)
class GenerationSettings:
    language: str
    voice_description: str
    seed: int
    guidance_scale: float
    inference_steps: int
    max_tokens: int


@dataclass(frozen=True)
class RuntimeSettings:
    max_text_chars: int
    gpu_seconds: int
    artifact_ttl_seconds: int


@dataclass(frozen=True)
class Settings:
    model: ModelSettings
    generation: GenerationSettings
    runtime: RuntimeSettings


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _mapping(loader: yaml.SafeLoader, node: Any) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValueError("YAML keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping
)


def _section(value: Any, keys: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{name} must contain exactly: {', '.join(sorted(keys))}")
    return value


def _integer(value: Any, lower: int, upper: int, name: str) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"{name} must be an integer between {lower} and {upper}")
    return value


def load_settings(path: Path) -> Settings:
    try:
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML configuration: {exc}") from exc
    document = _section(document, {"model", "generation", "runtime"}, "configuration")
    model = _section(document["model"], {"id", "revision"}, "model")
    generation = _section(document["generation"], {
        "language", "voice_description", "seed", "guidance_scale",
        "inference_steps", "max_tokens",
    }, "generation")
    runtime = _section(document["runtime"], {
        "max_text_chars", "gpu_seconds", "artifact_ttl_seconds",
    }, "runtime")
    if model["id"] != "openbmb/VoxCPM2":
        raise ValueError("This application requires openbmb/VoxCPM2")
    if not isinstance(model["revision"], str) or not re.fullmatch(r"[0-9a-f]{40}", model["revision"]):
        raise ValueError("model.revision must be an immutable 40-character commit SHA")
    language = generation["language"]
    if not isinstance(language, str) or language not in LANGUAGES:
        raise ValueError("generation.language must be auto or a supported language name")
    description = generation["voice_description"]
    if not isinstance(description, str) or len(description) > 500 or any(c in description for c in "()\n\r"):
        raise ValueError("voice_description must be at most 500 characters without parentheses or newlines")
    guidance = generation["guidance_scale"]
    if type(guidance) not in (float, int) or not math.isfinite(guidance) or not 0 < guidance <= 10:
        raise ValueError("guidance_scale must be finite and greater than 0, at most 10")
    return Settings(
        ModelSettings(**model),
        GenerationSettings(
            language, description.strip(),
            _integer(generation["seed"], 0, 2**32 - 1, "seed"), float(guidance),
            _integer(generation["inference_steps"], 1, 100, "inference_steps"),
            _integer(generation["max_tokens"], 2, 8192, "max_tokens"),
        ),
        RuntimeSettings(
            _integer(runtime["max_text_chars"], 1, 5000, "max_text_chars"),
            _integer(runtime["gpu_seconds"], 1, 120, "gpu_seconds"),
            _integer(runtime["artifact_ttl_seconds"], 60, 86400, "artifact_ttl_seconds"),
        ),
    )
