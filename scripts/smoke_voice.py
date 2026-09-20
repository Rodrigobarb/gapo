#!/usr/bin/env python3
"""
Smoke test de voz: conecta o bot ao Discord e entra num canal de voz.

Nao usa OCR, LLM nem TTS - serve para validar token, intents, permissoes e
conexao de voz antes de ligar o pipeline completo.

    python -m scripts.smoke_voice --list                 # lista guilds e canais
    python -m scripts.smoke_voice --channel-id 123456    # entra, espera, sai
"""

import asyncio
import sys

import click
import discord
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gapo.config import get_settings

console = Console()


def _check_opus() -> tuple[bool, str]:
    """discord.py traz libopus embutida no Windows; so o envio de audio precisa dela."""
    try:
        if discord.opus.is_loaded():
            return True, "ja carregada"
        discord.opus._load_default()
        if discord.opus.is_loaded():
            return True, "carregada (bundled discord.py)"
    except Exception as e:
        return False, str(e)
    return False, "nao encontrada"


async def _run(channel_id: int | None, list_only: bool, seconds: int) -> int:
    settings = get_settings()
    token = settings.discord.token

    if not token:
        console.print(
            Panel(
                "[bold red]DISCORD_TOKEN nao configurado.[/]\n\n"
                "Crie o arquivo [cyan].env[/] na raiz do projeto com:\n\n"
                "  DISCORD_TOKEN=seu_token\n"
                "  DISCORD_APPLICATION_ID=seu_app_id",
                title="Credenciais ausentes",
                border_style="red",
            )
        )
        return 2

    intents = discord.Intents.default()
    intents.voice_states = True
    intents.guilds = True
    # message_content nao e necessario para este teste; exigi-lo faria o login
    # falhar caso a intent ainda nao esteja habilitada no Developer Portal.

    client = discord.Client(intents=intents)
    result = {"code": 1}

    @client.event
    async def on_ready() -> None:
        try:
            console.print(f"[green]Conectado como[/] [bold]{client.user}[/] (ID: {client.user.id})")

            ok, detail = _check_opus()
            style = "green" if ok else "yellow"
            console.print(f"[{style}]Opus:[/] {detail}"
                          + ("" if ok else "  (so afeta o envio de audio, nao a conexao)"))

            guilds = list(client.guilds)
            if not guilds:
                console.print(
                    Panel(
                        "[bold yellow]O bot nao esta em nenhum servidor.[/]\n\n"
                        "Convide-o pelo Developer Portal > OAuth2 > URL Generator,\n"
                        "com os escopos [cyan]bot[/] + [cyan]applications.commands[/] e as permissoes\n"
                        "[cyan]Connect[/] e [cyan]Speak[/].",
                        title="Sem servidores",
                        border_style="yellow",
                    )
                )
                result["code"] = 3
                return

            table = Table(title="Canais de voz visiveis")
            table.add_column("Servidor", style="cyan")
            table.add_column("Canal", style="white")
            table.add_column("ID", style="dim")
            table.add_column("Entrar?", style="white")

            joinable: list[discord.VoiceChannel] = []
            for guild in guilds:
                for ch in guild.voice_channels:
                    perms = ch.permissions_for(guild.me)
                    can = perms.connect and perms.view_channel
                    if can:
                        joinable.append(ch)
                    table.add_row(
                        guild.name,
                        ch.name,
                        str(ch.id),
                        "[green]sim[/]" if can else "[red]sem permissao[/]",
                    )
            console.print(table)

            if list_only:
                console.print("\n[dim]Rode de novo com --channel-id <ID> para entrar no canal.[/]")
                result["code"] = 0
                return

            target = None
            if channel_id is not None:
                ch = client.get_channel(channel_id)
                if ch is None:
                    console.print(f"[red]Canal {channel_id} nao encontrado ou invisivel ao bot.[/]")
                    result["code"] = 4
                    return
                if not isinstance(ch, discord.VoiceChannel):
                    console.print(f"[red]Canal {channel_id} nao e um canal de voz (e {type(ch).__name__}).[/]")
                    result["code"] = 4
                    return
                target = ch
            elif len(joinable) == 1:
                target = joinable[0]
                console.print(f"\n[dim]Unico canal disponivel, usando:[/] [bold]{target.name}[/]")
            else:
                console.print(
                    "\n[yellow]Varios canais disponiveis.[/] Escolha um com "
                    "[cyan]--channel-id <ID>[/] da tabela acima."
                )
                result["code"] = 0
                return

            perms = target.permissions_for(target.guild.me)
            missing = [n for n, v in (("Connect", perms.connect), ("Speak", perms.speak)) if not v]
            if missing:
                console.print(f"[yellow]Aviso: faltam permissoes em {target.name}: {', '.join(missing)}[/]")

            console.print(f"\n[bold]Entrando em[/] [cyan]{target.guild.name} / {target.name}[/] ...")
            voice = await target.connect(timeout=30.0, reconnect=False)
            console.print(f"[green]Conectado.[/] Latencia de voz: {voice.latency * 1000:.0f} ms")
            console.print(f"[dim]Permanecendo {seconds}s no canal - confira no Discord.[/]")

            await asyncio.sleep(seconds)

            await voice.disconnect(force=False)
            console.print("[green]Desconectado do canal de voz.[/]")
            console.print("\n[bold green]Smoke test OK.[/]")
            result["code"] = 0

        except discord.errors.ClientException as e:
            console.print(f"[red]Erro de cliente:[/] {e}")
            result["code"] = 5
        except asyncio.TimeoutError:
            console.print(
                "[red]Timeout ao conectar na voz.[/] "
                "Normalmente e firewall/UDP bloqueado ou regiao de voz instavel."
            )
            result["code"] = 6
        except Exception as e:
            console.print(f"[red]Falha inesperada:[/] {type(e).__name__}: {e}")
            result["code"] = 7
        finally:
            await client.close()

    try:
        await client.start(token)
    except discord.LoginFailure:
        console.print(
            Panel(
                "[bold red]Token recusado pelo Discord.[/]\n\n"
                "Confira se copiou o [cyan]Bot Token[/] (aba Bot), e nao o Client Secret,\n"
                "e se ele nao foi regenerado depois de salvo no .env.",
                title="Login falhou",
                border_style="red",
            )
        )
        return 8
    except discord.PrivilegedIntentsRequired:
        console.print(
            Panel(
                "[bold red]Intents privilegiadas nao habilitadas.[/]\n\n"
                "Developer Portal > sua app > Bot > Privileged Gateway Intents:\n"
                "habilite [cyan]MESSAGE CONTENT INTENT[/] e [cyan]SERVER MEMBERS INTENT[/].",
                title="Intents",
                border_style="red",
            )
        )
        return 9

    return result["code"]


@click.command()
@click.option("--channel-id", type=int, default=None, help="ID do canal de voz para entrar")
@click.option("--list", "list_only", is_flag=True, help="Só lista servidores e canais, não entra")
@click.option("--seconds", type=int, default=120, help="Segundos para permanecer no canal")
def main(channel_id: int | None, list_only: bool, seconds: int) -> None:
    """Testa conexão do bot e entrada em canal de voz, sem OCR/LLM/TTS."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    code = asyncio.run(_run(channel_id, list_only, seconds))
    sys.exit(code)


if __name__ == "__main__":
    main()
