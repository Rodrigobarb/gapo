#!/usr/bin/env python3
"""Baixa so os modelos (LLM, voz Piper, YOLO), sem mexer em dependencias.

Para o fluxo completo use `gapo init`.
"""

import click

from gapo.bootstrap.console import Terminal
from gapo.bootstrap.diagnostics import SetupReport
from gapo.bootstrap.doctor import resolve_model_names
from gapo.bootstrap.installer import SetupService


@click.command()
@click.option("--llm", default="", help="Modelo Ollama (default: o das settings)")
@click.option("--tts", default="", help="Voz Piper (default: a das settings)")
@click.option("--skip-yolo", is_flag=True, help="Nao exportar o YOLOv8n")
def main(llm: str, tts: str, skip_yolo: bool):
    defaults = resolve_model_names()
    term = Terminal()
    term.banner("Gapo - download de modelos", style="bold blue")

    setup = SetupService(
        terminal=term,
        llm_model=llm or defaults["llm_model"],
        tts_voice=tts or defaults["tts_voice"],
        yolo_model=defaults["yolo_model"],
    )

    report = SetupReport()
    servidor = report.add(setup.ensure_ollama())
    if servidor.ok:
        report.add(setup.pull_llm_model())
    report.add(setup.download_piper_voice())
    if not skip_yolo:
        report.add(setup.export_yolo_model())

    term.section("Resumo")
    if report.healthy:
        term.banner("Modelos prontos", style="green")
        return
    raise SystemExit(1)


if __name__ == "__main__":
    main()
