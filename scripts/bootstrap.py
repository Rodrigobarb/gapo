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


def main() -> int:
    if sys.version_info < (3, 11):
        v = sys.version_info
        print(f"Python {v.major}.{v.minor} e antigo demais - o Gapo precisa de 3.11+")
        return 1

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
