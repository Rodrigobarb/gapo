#!/usr/bin/env python3
"""Entrada zero-dependencia: `python scripts/bootstrap.py`.

Serve para a maquina onde nem o comando `gapo` existe ainda: instala o projeto
no interpretador atual e, em seguida, chama `gapo init`, que baixa o resto.
Usa somente a stdlib de proposito - e o unico arquivo que pode rodar antes de
qualquer `pip install`.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}\n")
    return subprocess.call(cmd, cwd=str(ROOT))


ALVO = (3, 11)


def _checar_python() -> int:
    """O projeto e fixado no 3.11: fora disso o pip tenta compilar do zero.

    paddleocr, onnxruntime-gpu e faster-whisper nem sempre publicam wheel para
    a versao mais nova, e a instalacao morre no meio em vez de falhar aqui.
    """
    v = sys.version_info
    if (v.major, v.minor) == ALVO:
        return 0

    alvo = f"{ALVO[0]}.{ALVO[1]}"
    print(f"Python {v.major}.{v.minor}.{v.micro} - o Gapo usa o {alvo}.\n")
    print("Crie a venv apontando para o interpretador certo:")
    if sys.platform == "win32":
        print(f"  py -{alvo} -m venv venv")
        print("  venv/Scripts/python.exe scripts/bootstrap.py")
        print("\n(sem o 3.11 instalado: winget install Python.Python.3.11)")
    else:
        print(f"  python{alvo} -m venv venv")
        print("  venv/bin/python scripts/bootstrap.py")
    return 1


def main() -> int:
    codigo = _checar_python()
    if codigo != 0:
        return codigo

    if sys.prefix == sys.base_prefix:
        print("Aviso: voce nao esta numa venv. Sugerido:")
        print("  python -m venv venv && venv\\Scripts\\activate  (Windows)")
        print("  python -m venv venv && source venv/bin/activate  (Linux/macOS)\n")

    code = _run([sys.executable, "-m", "pip", "install", "-e", "."])
    if code != 0:
        print("\nFalhou o `pip install -e .` - corrija o erro acima e rode de novo.")
        return code

    return _run([sys.executable, "-m", "gapo", "init", "--skip-deps"] + sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
