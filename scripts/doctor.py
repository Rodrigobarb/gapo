#!/usr/bin/env python3
"""
Script de diagnóstico do sistema Gapo.
"""

import sys
import subprocess
import importlib
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def check_python() -> tuple[bool, str]:
    version = sys.version_info
    ok = version.major >= 3 and version.minor >= 11
    return ok, f"Python {version.major}.{version.minor}.{version.micro}"


def check_gpu() -> tuple[bool, str]:
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            gpus = result.stdout.strip().split("\n")
            info = "; ".join(gpus)
            return True, info
    except Exception:
        pass
    return False, "GPU NVIDIA não detectada ou nvidia-smi não encontrado"


def check_ollama() -> tuple[bool, str]:
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                models = [l.split()[0] for l in lines[1:] if l.strip()]
                return True, f"Modelos: {', '.join(models[:3])}"
            return True, "Ollama rodando (sem modelos)"
    except Exception:
        pass
    return False, "Ollama não encontrado ou não rodando"


def check_piper() -> tuple[bool, str]:
    try:
        result = subprocess.run(["piper", "--help"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True, "Piper TTS disponível"
    except Exception:
        pass
    return False, "Piper não encontrado"


def check_discord_token() -> tuple[bool, str]:
    from gapo.config.settings import get_settings
    try:
        settings = get_settings()
        if settings.discord.token and settings.discord.token != "your_token_here":
            return True, "Token configurado"
    except Exception:
        pass
    return False, "DISCORD_TOKEN não configurado no .env"


def check_imports() -> tuple[bool, str]:
    required = [
        "dxcam", "mss", "cv2", "numpy", "paddleocr", 
        "onnxruntime", "ultralytics", "ollama", "piper_tts",
        "discord", "pydantic", "loguru", "yaml", "click", "rich",
    ]
    missing = []
    for mod in required:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(mod)
    
    if not missing:
        return True, "Todas as dependências OK"
    return False, f"Faltando: {', '.join(missing)}"


def check_files() -> tuple[bool, str]:
    required_files = [
        "config/config.yaml",
        "data/champions/matchups.json",
        "data/champions/builds.json",
        "data/champions/counters.json",
        "data/champions/powerspikes.json",
        "data/prompts/event_coach_v1.yaml",
        "data/prompts/gapo_coach_v1.yaml",
        "data/roi_presets/1920x1080.yaml",
        "data/roi_presets/2560x1440.yaml",
    ]
    missing = [f for f in required_files if not Path(f).exists()]
    if not missing:
        return True, "Arquivos de configuração OK"
    return False, f"Faltando: {', '.join(missing)}"


def check_yolo_model() -> tuple[bool, str]:
    yolo_path = Path("yolov8n.onnx")
    if yolo_path.exists():
        return True, "yolov8n.onnx encontrado"
    return False, "yolov8n.onnx não encontrado (execute scripts/download_models.py)"


@click.command()
def main():
    console.print(Panel("🔍 Gapo - Diagnóstico do Sistema", style="bold cyan"))

    checks = [
        ("Python", check_python),
        ("GPU NVIDIA", check_gpu),
        ("Ollama", check_ollama),
        ("Piper TTS", check_piper),
        ("Discord Token", check_discord_token),
        ("Dependências Python", check_imports),
        ("Arquivos de Config", check_files),
        ("Modelo YOLO", check_yolo_model),
    ]

    table = Table(title="Resultados do Diagnóstico")
    table.add_column("Componente", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Detalhes", style="dim")

    all_ok = True
    for name, check_func in checks:
        ok, detail = check_func()
        status = "✅ OK" if ok else "❌ FALHA"
        if not ok:
            all_ok = False
        table.add_row(name, status, detail)

    console.print(table)

    console.print()
    if all_ok:
        console.print(Panel("✅ Sistema pronto para rodar o Gapo!", style="green"))
    else:
        console.print(Panel("⚠️  Algumas verificações falharam. Corrija antes de executar.", style="yellow"))


if __name__ == "__main__":
    main()