"""Entrypoint da CLI do Gapo.

Os comandos importam o runtime sob demanda de proposito: `gapo doctor` e
`gapo init` sao chamados justamente quando o ambiente esta quebrado (sem
loguru, sem numpy, sem discord), e um import pesado no topo deste arquivo
derrubaria os dois comandos que existem para consertar isso.
"""

from __future__ import annotations

import asyncio
import json as jsonlib
import sys

import click


@click.group()
def cli() -> None:
    """Gapo - coach de LoL por voz no Discord."""
    # A CLI usa emoji nas mensagens; no Windows o stdout cai em cp1252 quando a
    # saida e redirecionada (gapo doctor > log.txt) e o encode explode.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Sai em JSON, para scripts/CI")
def doctor(as_json: bool) -> None:
    """Diagnostica o ambiente: dependencias, modelos, GPU, Discord.

    Nao instala nem baixa nada. Sai com codigo 1 se houver falha.
    """
    from gapo.bootstrap.console import Terminal
    from gapo.bootstrap.doctor import DoctorService

    report = DoctorService().run()

    if as_json:
        click.echo(jsonlib.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        raise SystemExit(report.exit_code)

    term = Terminal()
    term.banner("Gapo - diagnostico do ambiente")
    term.report(report)
    term.verdict(report)
    raise SystemExit(report.exit_code)


@cli.command()
@click.option("--skip-deps", is_flag=True, help="Nao instalar dependencias Python")
@click.option("--skip-ollama", is_flag=True, help="Nao subir o Ollama nem baixar o LLM")
@click.option("--skip-piper", is_flag=True, help="Nao baixar a voz do Piper")
@click.option("--skip-yolo", is_flag=True, help="Nao exportar o YOLOv8n para ONNX")
@click.option(
    "--install-system",
    is_flag=True,
    help="Instalar Ollama e FFmpeg via winget (Windows)",
)
@click.option("--dev", is_flag=True, help="Instalar tambem as dependencias de desenvolvimento")
@click.option("--no-check", is_flag=True, help="Nao rodar o doctor no fim")
def init(
    skip_deps: bool,
    skip_ollama: bool,
    skip_piper: bool,
    skip_yolo: bool,
    install_system: bool,
    dev: bool,
    no_check: bool,
) -> None:
    """Prepara tudo: dependencias, diretorios, .env, LLM, voz TTS e YOLO.

    Idempotente - o que ja estiver no lugar e pulado. No fim roda o doctor.
    """
    from gapo.bootstrap.console import Terminal
    from gapo.bootstrap.doctor import DoctorService, resolve_model_names
    from gapo.bootstrap.installer import SetupService

    term = Terminal()
    term.banner("Gapo - inicializacao", style="bold green")

    modelos = resolve_model_names()
    setup = SetupService(
        terminal=term,
        llm_model=modelos["llm_model"],
        tts_voice=modelos["tts_voice"],
        yolo_model=modelos["yolo_model"],
    )
    setup_report = setup.run_all(
        skip_deps=skip_deps,
        skip_ollama=skip_ollama,
        skip_piper=skip_piper,
        skip_yolo=skip_yolo,
        install_system=install_system,
        dev=dev,
    )

    if no_check:
        term.section("Resumo")
        if setup_report.healthy:
            term.banner("Init concluido - rode `gapo doctor` para conferir", style="green")
            return
        raise SystemExit(1)

    term.section("Conferindo o resultado")
    report = DoctorService().run()
    term.report(report)
    term.verdict(report)
    raise SystemExit(report.exit_code)


@cli.command()
def run() -> None:
    """Inicia o bot completo com Discord."""
    from gapo.controllers.cli_controller import run_bot

    asyncio.run(run_bot())


@cli.command()
def capture() -> None:
    """Roda apenas captura e OCR (para testes)."""
    from gapo.controllers.cli_controller import run_capture

    asyncio.run(run_capture())


@cli.command()
@click.option("--width", default=1920, help="Largura da resolucao")
@click.option("--height", default=1080, help="Altura da resolucao")
def calibrate(width: int, height: int) -> None:
    """Calibra ROIs para a resolucao especificada."""
    click.echo(f"Calibracao para {width}x{height}")
    click.echo("Execute: python -m scripts.calibrate_roi")


if __name__ == "__main__":
    cli()
