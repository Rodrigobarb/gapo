#!/usr/bin/env python3
"""Atalho para `gapo doctor`.

A logica de diagnostico mora em gapo/bootstrap/doctor.py - este arquivo existe
so para manter funcionando `python -m scripts.doctor`.
"""

from gapo.cli import doctor

if __name__ == "__main__":
    doctor()
