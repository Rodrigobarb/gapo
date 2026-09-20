#!/usr/bin/env python3
"""
Script para baixar todos os modelos necessários.
"""

import asyncio
import subprocess
import click
from rich.console import Console

console = Console()


def run_cmd(cmd: list[str], desc: str) -> bool:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            console.print(f"✅ {desc}")
            return True
        else:
            console.print(f"❌ {desc}: {result.stderr[:200]}")
            return False
    except Exception as e:
        console.print(f"❌ {desc}: {e}")
        return False


@click.command()
@click.option("--llm", default="qwen2.5:7b-instruct-q4_K_M", help="Modelo Ollama")
@click.option("--tts", default="pt_BR-faber-medium", help="Modelo Piper TTS")
def main(llm: str, tts: str):
    console.print(Panel("📥 Baixando Modelos", style="bold blue"))

    # Ollama
    console.print(f"\n[bold]LLM: {llm}[/bold]")
    run_cmd(["ollama", "pull", llm], f"Ollama pull {llm}")

    # Piper
    console.print(f"\n[bold]TTS: {tts}[/bold]")
    run_cmd(["piper", "--download-model", tts], f"Piper download {tts}")

    # YOLO
    console.print("\n[bold]YOLOv8n ONNX[/bold]")
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        model.export(format="onnx", opset=12)
        console.print("✅ YOLOv8n exportado para ONNX")
    except Exception as e:
        console.print(f"❌ YOLO: {e}")

    console.print("\n✅ Downloads concluídos!")


from rich.panel import Panel

if __name__ == "__main__":
    main()