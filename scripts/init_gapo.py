#!/usr/bin/env python3
"""Atalho para `gapo init`.

A logica de instalacao mora em gapo/bootstrap/installer.py - este arquivo existe
so para manter funcionando `python -m scripts.init_gapo`. Aceita as mesmas
opcoes (--skip-deps, --skip-ollama, --skip-piper, --skip-yolo, ...).
"""

from gapo.cli import init

if __name__ == "__main__":
    init()
