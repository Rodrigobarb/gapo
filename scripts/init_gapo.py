#!/usr/bin/env python3
"""
Script de inicialização do Gapo.
Baixa modelos, configura ambiente e verifica dependências.
"""

import asyncio
import subprocess
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

console = Console()


def run_command(cmd: list[str], description: str) -> bool:
    """Executa comando e retorna sucesso."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(description, total=None)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            progress.update(task, completed=True)

        if result.returncode == 0:
            console.print(f"✅ {description}")
            return True
        else:
            console.print(f"❌ {description}")
            console.print(f"   stderr: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        console.print(f"⏱️  {description} - Timeout")
        return False
    except Exception as e:
        console.print(f"❌ {description} - {e}")
        return False


def check_python_version() -> bool:
    """Verifica versão do Python."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        console.print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    console.print(f"❌ Python {version.major}.{version.minor} - Requer 3.11+")
    return False


def check_gpu() -> bool:
    """Verifica GPU NVIDIA disponível."""
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], 
                                capture_output=True, text=True)
        if result.returncode == 0:
            gpus = result.stdout.strip().split("\n")
            for gpu in gpus:
                console.print(f"🎮 GPU: {gpu}")
            return True
    except FileNotFoundError:
        pass
    console.print("⚠️  GPU NVIDIA não detectada (usando CPU)")
    return False


async def download_ollama_model(model: str = "qwen2.5:7b-instruct-q4_K_M") -> bool:
    """Baixa modelo Ollama."""
    console.print(Panel(f"Baixando modelo LLM: {model}", style="blue"))
    return run_command(["ollama", "pull", model], f"Ollama pull {model}")


def download_piper_model(model: str = "pt_BR-faber-medium") -> bool:
    """Baixa modelo Piper TTS."""
    console.print(Panel(f"Baixando modelo TTS: {model}", style="blue"))
    return run_command(["piper", "--download-model", model], f"Piper download {model}")


def download_yolo_model() -> bool:
    """Baixa modelo YOLOv8n ONNX."""
    console.print(Panel("Baixando YOLOv8n ONNX", style="blue"))
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        model.export(format="onnx", opset=12)
        console.print("✅ YOLOv8n ONNX exportado")
        return True
    except Exception as e:
        console.print(f"❌ Erro ao exportar YOLO: {e}")
        return False


def create_directories() -> bool:
    """Cria diretórios necessários."""
    dirs = [
        "data/champions",
        "data/prompts",
        "data/roi_presets",
        "logs",
        "config",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    console.print("✅ Diretórios criados")
    return True


def create_config_files() -> bool:
    """Cria arquivos de configuração padrão."""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)

    config_yaml = config_dir / "config.yaml"
    if not config_yaml.exists():
        config_yaml.write_text("""# Gapo Configuration
model:
  llm_name: "qwen2.5:7b-instruct-q4_K_M"
  llm_ctx_size: 2048
  llm_temperature: 0.3
  tts_model: "pt_BR-faber-medium"
  yolo_model: "yolov8n.onnx"

capture:
  fps: 3
  monitor_index: 0
  resolution_width: 1920
  resolution_height: 1080
  use_dxcam: true

ocr:
  confidence_threshold: 0.6
  use_gpu: false
  roi_padding: 5
  preprocess_scale: 2.0

coach:
  event_cooldown_seconds: 5.0
  gapo_cooldown_seconds: 10.0
  max_response_sentences: 3
  enable_event_coach: true
  enable_gapo_chat: true
""")
        console.print("✅ config.yaml criado")

    return True


def create_champion_data() -> bool:
    """Cria dados de exemplo de champions."""
    champions_dir = Path("data/champions")
    champions_dir.mkdir(parents=True, exist_ok=True)

    matchups = champions_dir / "matchups.json"
    if not matchups.exists():
        matchups.write_text('{"zed_vs_syndra": {"advice": "Zed vence early, dodge Q com W, all-in level 6"}}')
        console.print("✅ matchups.json criado")

    builds = champions_dir / "builds.json"
    if not builds.exists():
        builds.write_text('{"zed": {"mythic": "divine sunderer", "boots": "ionian", "core": ["youmuu", "serylda", "edge of night"]}}')
        console.print("✅ builds.json criado")

    counters = champions_dir / "counters.json"
    if not counters.exists():
        counters.write_text('{"malphite": ["darius", "fiora", "gwen", "quinn", "vayne"]}')
        console.print("✅ counters.json criado")

    powerspikes = champions_dir / "powerspikes.json"
    if not powerspikes.exists():
        powerspikes.write_text('{"zed": [{"level": 3, "desc": "W-E-Q combo"}, {"level": 6, "desc": "R burst"}, {"item": "youmuu", "desc": "Lethality spike"}]}')
        console.print("✅ powerspikes.json criado")

    return True


def create_prompt_templates() -> bool:
    """Cria templates de prompt."""
    prompts_dir = Path("data/prompts")
    prompts_dir.mkdir(parents=True, exist_ok=True)

    event_prompt = prompts_dir / "event_coach_v1.yaml"
    if not event_prompt.exists():
        event_prompt.write_text("""system_prompt: |
  Você é um coach de League of Legends elo Challenger falando português brasileiro.
  Sua função: dar UMA dica curta (máx 2 frases), acionável, focada no AGORA.
  Tom: encorajador, direto, parceiro de duo. NÃO explique conceitos básicos.
  Use o contexto da partida para ser específico: champion, level, itens, posição, timers.
  Se não tiver info suficiente, dê dica genérica de macro.

user_prompt_template: |
  Evento: {event_type}
  Detalhes: {message}
  Contexto: {game_state}

max_tokens: 100
temperature: 0.3
""")
        console.print("✅ event_coach_v1.yaml criado")

    gapo_prompt = prompts_dir / "gapo_coach_v1.yaml"
    if not gapo_prompt.exists():
        gapo_prompt.write_text("""system_prompt: |
  Você é "Gapo", coach de LoL elo Challenger, respondendo por voz no Discord.
  Contexto: partida atual + conhecimento geral (matchups, builds, counters, powerspikes, macro).
  Responda em PT-BR, direto, máx 3 frases. Use contexto da partida SE relevante.
  Tom: parceiro de duo, sem formalidade, gírias de LoL ok.
  Se não souber, diga "Não tenho certeza disso" - NÃO invente.
  Priorize acionável > educativo.

user_prompt_template: |
  Pergunta: {question}
  Contexto: {game_state}

max_tokens: 200
temperature: 0.4
""")
        console.print("✅ gapo_coach_v1.yaml criado")

    return True


def create_roi_presets() -> bool:
    """Cria presets de ROI."""
    roi_dir = Path("data/roi_presets")
    roi_dir.mkdir(parents=True, exist_ok=True)

    presets = {
        "1920x1080.yaml": {
            "hud_hp": {"name": "hud_hp", "x": 15, "y": 15, "width": 180, "height": 35},
            "hud_mana": {"name": "hud_mana", "x": 15, "y": 50, "width": 180, "height": 25},
            "hud_level": {"name": "hud_level", "x": 15, "y": 80, "width": 60, "height": 35},
            "hud_gold": {"name": "hud_gold", "x": 15, "y": 120, "width": 100, "height": 30},
            "hud_cs": {"name": "hud_cs", "x": 15, "y": 150, "width": 80, "height": 30},
            "hud_items": {"name": "hud_items", "x": 100, "y": 1020, "width": 480, "height": 60},
            "hud_spells": {"name": "hud_spells", "x": 600, "y": 1020, "width": 120, "height": 60},
            "minimap": {"name": "minimap", "x": 1600, "y": 15, "width": 300, "height": 300},
            "chat": {"name": "chat", "x": 15, "y": 700, "width": 400, "height": 300},
        },
        "2560x1440.yaml": {
            "hud_hp": {"name": "hud_hp", "x": 20, "y": 20, "width": 240, "height": 45},
            "hud_mana": {"name": "hud_mana", "x": 20, "y": 65, "width": 240, "height": 35},
            "hud_level": {"name": "hud_level", "x": 20, "y": 105, "width": 80, "height": 45},
            "hud_gold": {"name": "hud_gold", "x": 20, "y": 155, "width": 130, "height": 40},
            "hud_cs": {"name": "hud_cs", "x": 20, "y": 195, "width": 100, "height": 40},
            "hud_items": {"name": "hud_items", "x": 130, "y": 1360, "width": 640, "height": 80},
            "hud_spells": {"name": "hud_spells", "x": 800, "y": 1360, "width": 160, "height": 80},
            "minimap": {"name": "minimap", "x": 2140, "y": 20, "width": 400, "height": 400},
            "chat": {"name": "chat", "x": 20, "y": 930, "width": 530, "height": 400},
        },
    }

    import yaml
    for filename, data in presets.items():
        path = roi_dir / filename
        if not path.exists():
            path.write_text(yaml.dump(data, allow_unicode=True))
            console.print(f"✅ {filename} criado")

    return True


@click.command()
@click.option("--skip-ollama", is_flag=True, help="Pular download do modelo Ollama")
@click.option("--skip-piper", is_flag=True, help="Pular download do modelo Piper")
@click.option("--skip-yolo", is_flag=True, help="Pular download/export do YOLO")
def main(skip_ollama: bool, skip_piper: bool, skip_yolo: bool):
    """Inicializa o Gapo - baixa modelos e configura ambiente."""
    console.print(Panel("🚀 Gapo - Inicialização", style="bold green"))

    all_ok = True

    console.print("\n[bold]Verificando ambiente...[/bold]")
    all_ok &= check_python_version()
    check_gpu()

    console.print("\n[bold]Criando estrutura...[/bold]")
    all_ok &= create_directories()
    all_ok &= create_config_files()
    all_ok &= create_champion_data()
    all_ok &= create_prompt_templates()
    all_ok &= create_roi_presets()

    console.print("\n[bold]Baixando modelos...[/bold]")
    if not skip_ollama:
        all_ok &= asyncio.run(download_ollama_model())
    else:
        console.print("⏭️  Pulando Ollama")

    if not skip_piper:
        all_ok &= download_piper_model()
    else:
        console.print("⏭️  Pulando Piper")

    if not skip_yolo:
        all_ok &= download_yolo_model()
    else:
        console.print("⏭️  Pulando YOLO")

    console.print("\n" + "=" * 50)
    if all_ok:
        console.print(Panel("✅ Gapo inicializado com sucesso!\n\nPróximos passos:\n1. Configure DISCORD_TOKEN no .env\n2. Execute: gapo run", style="green"))
    else:
        console.print(Panel("⚠️  Inicialização concluída com avisos\nVerifique os erros acima", style="yellow"))


if __name__ == "__main__":
    main()