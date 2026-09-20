"""Modelos do relatorio do `gapo doctor`.

Dataclasses puras (stdlib) para o relatorio sobreviver a um ambiente sem
pydantic instalado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CheckStatus(str, Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class CheckResult:
    """Resultado de uma verificacao isolada do ambiente.

    `fixable_by_init` marca o que `gapo init` resolve sozinho - e o que separa
    "rode gapo init" de "instale isso na mao".
    """

    name: str
    status: CheckStatus
    detail: str
    hint: str = ""
    fixable_by_init: bool = False

    @property
    def ok(self) -> bool:
        return self.status is CheckStatus.OK

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "detail": self.detail,
            "hint": self.hint,
            "fixable_by_init": self.fixable_by_init,
        }


@dataclass
class DiagnosticsReport:
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, check: CheckResult) -> CheckResult:
        self.checks.append(check)
        return check

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status is CheckStatus.FAIL]

    @property
    def warnings(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status is CheckStatus.WARN]

    @property
    def fixable(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.ok and c.fixable_by_init]

    @property
    def healthy(self) -> bool:
        return not self.failures

    @property
    def exit_code(self) -> int:
        return 0 if self.healthy else 1

    def to_dict(self) -> dict:
        return {
            "healthy": self.healthy,
            "failures": len(self.failures),
            "warnings": len(self.warnings),
            "fixable_by_init": [c.name for c in self.fixable],
            "checks": [c.to_dict() for c in self.checks],
        }


@dataclass
class StepResult:
    """Resultado de um passo do `gapo init`."""

    name: str
    status: CheckStatus
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status is CheckStatus.OK


@dataclass
class SetupReport:
    steps: list[StepResult] = field(default_factory=list)

    def add(self, step: StepResult) -> StepResult:
        self.steps.append(step)
        return step

    @property
    def failures(self) -> list[StepResult]:
        return [s for s in self.steps if s.status is CheckStatus.FAIL]

    @property
    def warnings(self) -> list[StepResult]:
        return [s for s in self.steps if s.status is CheckStatus.WARN]

    @property
    def healthy(self) -> bool:
        return not self.failures
