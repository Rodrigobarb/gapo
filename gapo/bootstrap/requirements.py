"""Metadados estaticos do que o Gapo precisa para rodar.

Fonte unica de verdade usada por `gapo doctor` (verifica) e por `gapo init`
(instala/baixa). So depende da stdlib: este modulo precisa importar num
ambiente ainda quebrado, que e exatamente quando os dois comandos rodam.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

PYTHON_MIN = (3, 11)

# Serie fixada: paddleocr, onnxruntime-gpu e faster-whisper nem sempre tem
# wheel para a versao mais nova do Python, e ai o pip tenta compilar do zero.
PYTHON_TARGET = (3, 11)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OLLAMA_HOST = "http://localhost:11434"
PIPER_VOICES_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
PIPER_MODEL_DIR = Path.home() / ".local" / "share" / "piper"
YOLO_MODEL_FILE = "yolov8n.onnx"

# faster-whisper baixa do HuggingFace e guarda no cache padrao do hub.
WHISPER_REPO_TEMPLATE = "Systran/faster-whisper-{size}"

RUNTIME_DIRS = (
    "logs",
    "config",
    "data/cache",
    "data/champions",
    "data/prompts",
    "data/roi_presets",
)

REQUIRED_DATA_FILES = (
    "data/champions/matchups.json",
    "data/champions/builds.json",
    "data/champions/counters.json",
    "data/champions/powerspikes.json",
    "data/prompts/event_coach_v1.yaml",
    "data/prompts/gapo_coach_v1.yaml",
    "data/roi_presets/1920x1080.yaml",
    "data/roi_presets/2560x1440.yaml",
    "data/roi_presets/3840x2160.yaml",
)


@dataclass(frozen=True)
class PyPackage:
    """Dependencia Python: nome do modulo importavel != nome no PyPI."""

    module: str
    dist: str
    purpose: str
    optional: bool = False
    platforms: tuple[str, ...] = ()

    def applies(self) -> bool:
        """Falso quando o pacote so faz sentido em outro sistema operacional."""
        return not self.platforms or sys.platform in self.platforms


PY_PACKAGES = (
    PyPackage("click", "click", "CLI"),
    PyPackage("rich", "rich", "saida formatada"),
    PyPackage("pydantic", "pydantic", "modelos de dominio"),
    PyPackage("pydantic_settings", "pydantic-settings", "configuracao via .env"),
    PyPackage("yaml", "pyyaml", "presets de ROI e prompts"),
    PyPackage("loguru", "loguru", "logging"),
    PyPackage("numpy", "numpy", "processamento de frames"),
    PyPackage("cv2", "opencv-python", "pre-processamento de imagem"),
    PyPackage("PIL", "pillow", "imagens"),
    PyPackage("mss", "mss", "captura de tela (fallback multiplataforma)"),
    PyPackage("dxcam", "dxcam", "captura de tela rapida", platforms=("win32",)),
    PyPackage("paddleocr", "paddleocr", "OCR do HUD/minimapa/chat"),
    PyPackage("onnxruntime", "onnxruntime-gpu", "inferencia do YOLO"),
    PyPackage("ollama", "ollama", "cliente do LLM local"),
    PyPackage("discord", "discord.py", "bot do Discord"),
    PyPackage("discord.ext.voice_recv", "discord-ext-voice-recv", "receber audio da call"),
    PyPackage("faster_whisper", "faster-whisper", "transcricao da fala (STT)"),
    PyPackage("nacl", "PyNaCl", "voz no Discord"),
    PyPackage("av", "av", "audio/video"),
    PyPackage("prometheus_client", "prometheus-client", "metricas"),
    PyPackage("tenacity", "tenacity", "retries"),
    PyPackage("ultralytics", "ultralytics", "export do YOLOv8n para ONNX", optional=True),
    PyPackage("opuslib", "opuslib", "encoder Opus (exige lib nativa)", optional=True),
)


def is_installed(pkg: PyPackage) -> bool:
    """Se o pacote esta instalado, sem importar nada pesado.

    Submodulo (nome com ponto) e checado pelos metadados da distribuicao:
    `find_spec("discord.ext.voice_recv")` importaria o `discord` inteiro, e o
    doctor tem que continuar leve.
    """
    if "." in pkg.module:
        try:
            importlib.metadata.distribution(pkg.dist)
            return True
        except importlib.metadata.PackageNotFoundError:
            return False
    try:
        return importlib.util.find_spec(pkg.module) is not None
    except (ImportError, ValueError):
        return False


def piper_voice_urls(voice: str) -> tuple[str, str]:
    """URLs do .onnx e do .onnx.json de uma voz Piper no repositorio rhasspy.

    O nome segue o padrao `<lang_code>-<speaker>-<quality>`, e o caminho no
    HuggingFace intercala a familia do idioma: pt/pt_BR/faber/medium/...
    """
    parts = voice.split("-")
    if len(parts) != 3:
        raise ValueError(
            f"Nome de voz Piper invalido: {voice!r} (esperado <lang>-<speaker>-<quality>)"
        )
    lang_code, speaker, quality = parts
    family = lang_code.split("_")[0]
    base = f"{PIPER_VOICES_BASE}/{family}/{lang_code}/{speaker}/{quality}/{voice}"
    return f"{base}.onnx", f"{base}.onnx.json"


def piper_voice_paths(voice: str, model_dir: Path | None = None) -> tuple[Path, Path]:
    """Caminhos locais esperados para o .onnx e o .onnx.json da voz."""
    directory = model_dir or PIPER_MODEL_DIR
    return directory / f"{voice}.onnx", directory / f"{voice}.onnx.json"


def whisper_repo(model_size: str) -> str:
    return WHISPER_REPO_TEMPLATE.format(size=model_size)


def whisper_cached(model_size: str) -> bool:
    """Se o modelo do Whisper ja esta no cache do HuggingFace.

    Le a constante do proprio hub quando ele esta instalado; senao cai no
    caminho padrao, para o doctor nao depender do pacote.
    """
    import os

    try:
        from huggingface_hub.constants import HF_HUB_CACHE

        cache = Path(HF_HUB_CACHE)
    except Exception:
        cache = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"

    pasta = cache / ("models--" + whisper_repo(model_size).replace("/", "--"))
    if not pasta.exists():
        return False
    # Uma pasta so com refs/ e um download interrompido.
    return any((pasta / "snapshots").glob("*/*.bin")) or any(
        (pasta / "snapshots").glob("*/*.safetensors")
    )
