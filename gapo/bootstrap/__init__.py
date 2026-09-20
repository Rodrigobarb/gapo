"""Bootstrap do Gapo: diagnostico (`gapo doctor`) e instalacao (`gapo init`).

Este pacote existe separado de services/ por um motivo pratico: ele precisa
importar num ambiente onde as dependencias do projeto ainda nao existem. Por
isso so usa stdlib + click + rich, e nunca importa gapo.services, gapo.core
ou gapo.infrastructure no topo do modulo.
"""

from gapo.bootstrap.diagnostics import (
    CheckResult,
    CheckStatus,
    DiagnosticsReport,
    SetupReport,
    StepResult,
)
from gapo.bootstrap.doctor import DoctorService, resolve_model_names
from gapo.bootstrap.installer import SetupService
from gapo.bootstrap.opus import ensure_opus_dll, register_opus_path

__all__ = [
    "CheckResult",
    "CheckStatus",
    "DiagnosticsReport",
    "DoctorService",
    "SetupReport",
    "SetupService",
    "StepResult",
    "ensure_opus_dll",
    "register_opus_path",
    "resolve_model_names",
]
