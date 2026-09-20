"""Saida do `gapo doctor` / `gapo init`.

Usa rich quando disponivel e cai para texto puro quando nao: o diagnostico
precisa funcionar justamente no ambiente onde as dependencias faltam.
"""

from __future__ import annotations

import re

import click

from gapo.bootstrap.diagnostics import CheckStatus, DiagnosticsReport

try:  # pragma: no cover - depende do ambiente
    from rich.console import Console as _RichConsole
    from rich.panel import Panel as _RichPanel
    from rich.table import Table as _RichTable

    HAS_RICH = True
except ImportError:  # pragma: no cover - ambiente sem rich
    HAS_RICH = False

SYMBOLS = {
    CheckStatus.OK: "✅",
    CheckStatus.WARN: "⚠️ ",
    CheckStatus.FAIL: "❌",
}

LABELS = {
    CheckStatus.OK: "OK",
    CheckStatus.WARN: "AVISO",
    CheckStatus.FAIL: "FALHA",
}

STYLES = {
    CheckStatus.OK: "green",
    CheckStatus.WARN: "yellow",
    CheckStatus.FAIL: "red",
}


class Terminal:
    """Fachada minima sobre rich, com fallback em click.echo."""

    def __init__(self) -> None:
        self._console = _RichConsole() if HAS_RICH else None

    def print(self, message: str = "", style: str = "", markup: bool = True) -> None:
        """`markup=False` para texto de terceiros (saida de pip/winget).

        Sem isso o rich tenta interpretar coisas como `[notice]` do pip como tag
        de estilo e quebra no meio da instalacao.
        """
        if self._console is not None:
            self._console.print(message, style=style or None, markup=markup, highlight=False)
        else:
            click.echo(_strip_markup(message) if markup else message)

    def status(self, status: CheckStatus, message: str) -> None:
        self.print(f"{SYMBOLS[status]} {message}", style=STYLES[status])

    def banner(self, title: str, style: str = "bold cyan") -> None:
        if self._console is not None:
            self._console.print(_RichPanel(title, style=style))
        else:
            click.echo("")
            click.echo(f"== {_strip_markup(title)} ==")

    def section(self, title: str) -> None:
        self.print("")
        self.print(f"[bold]{title}[/bold]" if HAS_RICH else title)

    def progress_line(self) -> "ProgressLine":
        """Linha unica reescrita no lugar - evita centenas de linhas de download."""
        return ProgressLine()

    def report(self, report: DiagnosticsReport) -> None:
        """Tabela do diagnostico; a coluna de correcao so aparece se houver o que corrigir."""
        show_hints = any(c.hint for c in report.checks if not c.ok)

        if self._console is None:
            for check in report.checks:
                click.echo(f"{SYMBOLS[check.status]} {check.name:<22} {check.detail}")
                if check.hint and not check.ok:
                    click.echo(f"   {'':<22} -> {check.hint}")
            return

        table = _RichTable(title="Diagnostico do ambiente", title_style="bold")
        table.add_column("Componente", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("Detalhes")
        if show_hints:
            table.add_column("Como resolver", style="dim", overflow="fold")

        for check in report.checks:
            status_cell = f"[{STYLES[check.status]}]{LABELS[check.status]}[/]"
            row = [check.name, status_cell, check.detail]
            if show_hints:
                row.append("" if check.ok else check.hint)
            table.add_row(*row)

        self._console.print(table)

    def verdict(self, report: DiagnosticsReport) -> None:
        if report.healthy and not report.warnings:
            self.banner("Ambiente pronto - rode: gapo run", style="green")
            return
        if report.healthy:
            self.banner(
                f"Pronto para rodar, com {len(report.warnings)} aviso(s) - veja a tabela acima",
                style="yellow",
            )
            return

        automaticas = [c for c in report.failures if c.fixable_by_init]
        manuais = [c for c in report.failures if not c.fixable_by_init]

        linhas = [f"{len(report.failures)} falha(s) bloqueando o `gapo run`."]
        if automaticas:
            linhas.append("`gapo init` resolve: " + ", ".join(c.name for c in automaticas))
        if manuais:
            linhas.append("Precisa de voce: " + ", ".join(c.name for c in manuais))
        self.banner("\n".join(linhas), style="red")


# So as tags de estilo do rich - conteudo entre colchetes (ex.: "[OK]") fica.
_STYLE_WORDS = "bold|italic|dim|green|yellow|red|cyan|blue|magenta|white"
_MARKUP = re.compile(rf"\[/\]|\[/?(?:{_STYLE_WORDS})(?: (?:{_STYLE_WORDS}))*\]")


def _strip_markup(message: str) -> str:
    """Remove as tags do rich quando a saida e texto puro."""
    return _MARKUP.sub("", message)


class ProgressLine:
    """Progresso reescrito sempre na mesma linha (carriage return), com ou sem rich."""

    def __init__(self, prefix: str = "   ") -> None:
        self._prefix = prefix
        self._width = 0
        self._active = False

    def update(self, text: str) -> None:
        if not text:
            return
        linha = f"{self._prefix}{text}"
        padding = max(0, self._width - len(linha))
        click.echo(f"\r{linha}{' ' * padding}", nl=False)
        self._width = len(linha)
        self._active = True

    def close(self) -> None:
        if self._active:
            click.echo("")
            self._active = False
        self._width = 0
