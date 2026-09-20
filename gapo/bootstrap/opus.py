"""Acha a libopus no Windows sem pedir download manual de DLL.

O opuslib resolve a biblioteca com `ctypes.util.find_library("opus")`, que no
Windows varre o PATH atras de um arquivo chamado exatamente `opus.dll`. O
discord.py ja instala a mesma libopus dentro do venv, so que com outro nome
(`libopus-0.x64.dll`). Entao o conserto e uma copia renomeada + o PATH
apontando para ela - nada vem da internet.

No Linux/macOS a lib vem do gerenciador de pacotes (libopus0 / brew install
opus) e este modulo nao faz nada.
"""

from __future__ import annotations

import ctypes.util
import os
import shutil
import struct
import sys
from pathlib import Path

DLL_NAME = "opus.dll"


def opus_available() -> bool:
    """True quando o ctypes ja consegue localizar a libopus."""
    return ctypes.util.find_library("opus") is not None


def bundled_opus_dll() -> Path | None:
    """A libopus que o discord.py instalou, na arquitetura deste Python."""
    try:
        import discord
    except ImportError:
        return None

    arquitetura = "x64" if struct.calcsize("P") * 8 == 64 else "x86"
    caminho = Path(discord.__file__).parent / "bin" / f"libopus-0.{arquitetura}.dll"
    return caminho if caminho.exists() else None


def opus_dll_dir() -> Path:
    """Onde a copia mora: ao lado do python.exe (venv/Scripts no Windows)."""
    return Path(sys.executable).parent


def register_opus_path() -> bool:
    """Poe o diretorio da copia no PATH do processo. Nao cria nada.

    Necessario porque `find_library` so olha o PATH - rodar
    `venv/Scripts/python.exe` sem ativar o venv nao coloca Scripts la.
    """
    if sys.platform != "win32":
        return opus_available()
    if opus_available():
        return True

    diretorio = opus_dll_dir()
    if not (diretorio / DLL_NAME).exists():
        return False
    os.environ["PATH"] = f"{diretorio}{os.pathsep}{os.environ.get('PATH', '')}"
    return opus_available()


def ensure_opus_dll() -> tuple[bool, str]:
    """Materializa o opus.dll a partir da copia do discord.py. Passo do init.

    Devolve (resolvido, mensagem). Idempotente: se ja existe, nao copia de novo.
    """
    if sys.platform != "win32":
        if opus_available():
            return True, "libopus do sistema encontrada"
        return False, "instale a libopus do sistema (Debian/Ubuntu: apt install libopus0)"

    if register_opus_path():
        return True, "opus.dll ja acessivel"

    origem = bundled_opus_dll()
    if origem is None:
        return False, "discord.py ainda nao instalado - o Opus vem junto com ele"

    destino = opus_dll_dir() / DLL_NAME
    try:
        shutil.copy2(origem, destino)
    except OSError as e:
        return False, f"nao consegui copiar para {destino}: {e}"

    if register_opus_path():
        return True, f"copiado de {origem.name} para {destino}"
    return False, f"copiei para {destino}, mas o ctypes segue sem achar"
