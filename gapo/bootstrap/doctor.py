"""`gapo doctor`: verifica tudo que o bot precisa, sem importar o runtime.

Cada check devolve um CheckResult e nunca levanta excecao: o diagnostico roda
em ambiente quebrado por definicao. Nenhum check instala ou baixa nada - isso
e trabalho do `gapo init`, e o campo `fixable_by_init` diz quais falhas ele
resolve sozinho.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from gapo.bootstrap.diagnostics import CheckResult, CheckStatus, DiagnosticsReport
from gapo.bootstrap.requirements import (
    OLLAMA_HOST,
    PROJECT_ROOT,
    PY_PACKAGES,
    PYTHON_MIN,
    REQUIRED_DATA_FILES,
    YOLO_MODEL_FILE,
    piper_voice_paths,
)

INIT_HINT = "rode: gapo init"

# VRAM minima para o qwen2.5-7b-q4 caber na GPU sem cair para CPU.
VRAM_MIN_MIB = 6000


class DoctorService:
    """Roda as verificacoes de ambiente e monta o relatorio."""

    def __init__(
        self,
        llm_model: str = "",
        tts_voice: str = "",
        yolo_model: str = "",
        ollama_host: str = OLLAMA_HOST,
        cwd: Path | None = None,
    ) -> None:
        defaults = resolve_model_names()
        self.llm_model = llm_model or defaults["llm_model"]
        self.tts_voice = tts_voice or defaults["tts_voice"]
        self.yolo_model = yolo_model or defaults["yolo_model"]
        self.ollama_host = ollama_host
        self.cwd = cwd or Path.cwd()

    def run(self) -> DiagnosticsReport:
        report = DiagnosticsReport()
        for check in (
            self.check_python,
            self.check_platform,
            self.check_gpu,
            self.check_dependencies,
            self.check_project_files,
            self.check_env_file,
            self.check_discord_token,
            self.check_ollama_server,
            self.check_llm_model,
            self.check_piper_voice,
            self.check_yolo_model,
            self.check_opus,
        ):
            try:
                report.add(check())
            except Exception as e:  # pragma: no cover - blindagem do diagnostico
                report.add(
                    CheckResult(
                        name=check.__name__.removeprefix("check_"),
                        status=CheckStatus.FAIL,
                        detail=f"Verificacao quebrou: {e}",
                    )
                )
        return report

    # -- ambiente ----------------------------------------------------------

    def check_python(self) -> CheckResult:
        v = sys.version_info
        atual = f"Python {v.major}.{v.minor}.{v.micro}"
        if (v.major, v.minor) >= PYTHON_MIN:
            return CheckResult("Python", CheckStatus.OK, atual)
        minimo = ".".join(str(p) for p in PYTHON_MIN)
        return CheckResult(
            "Python",
            CheckStatus.FAIL,
            f"{atual} - requer {minimo}+",
            hint=f"instale Python {minimo}+ e recrie a venv",
        )

    def check_platform(self) -> CheckResult:
        detail = f"{platform.system()} {platform.release()} ({sys.platform})"
        if sys.platform == "win32":
            return CheckResult("Sistema", CheckStatus.OK, f"{detail} - captura via dxcam")
        return CheckResult(
            "Sistema",
            CheckStatus.WARN,
            f"{detail} - dxcam e so Windows, captura cai para mss",
            hint="para capturar o cliente do LoL use Windows",
        )

    def check_gpu(self) -> CheckResult:
        smi = shutil.which("nvidia-smi")
        if not smi:
            return CheckResult(
                "GPU NVIDIA",
                CheckStatus.WARN,
                "nvidia-smi nao encontrado - LLM e OCR rodam na CPU (lento)",
                hint="instale o driver NVIDIA se a maquina tiver GPU",
            )
        ok, out = _run([smi, "--query-gpu=name,memory.total", "--format=csv,noheader"])
        if not ok or not out:
            return CheckResult(
                "GPU NVIDIA",
                CheckStatus.WARN,
                "nvidia-smi falhou - seguindo em CPU",
                hint="verifique o driver NVIDIA",
            )

        detail = "; ".join(out.splitlines())
        vram = _max_vram_mib(out)
        if vram and vram < VRAM_MIN_MIB:
            return CheckResult(
                "GPU NVIDIA",
                CheckStatus.WARN,
                f"{detail} - menos de {VRAM_MIN_MIB} MiB, o LLM 7B pode nao caber",
                hint="use um modelo menor: GAPO_MODEL_LLM_NAME=qwen2.5:3b-instruct-q4_K_M",
            )
        return CheckResult("GPU NVIDIA", CheckStatus.OK, detail)

    def check_dependencies(self) -> CheckResult:
        faltando: list[str] = []
        opcionais: list[str] = []
        for pkg in PY_PACKAGES:
            if not pkg.applies() or _module_available(pkg.module):
                continue
            (opcionais if pkg.optional else faltando).append(pkg.dist)

        if faltando:
            return CheckResult(
                "Dependencias Python",
                CheckStatus.FAIL,
                f"{len(faltando)} faltando: {', '.join(faltando)}",
                hint=INIT_HINT,
                fixable_by_init=True,
            )
        if opcionais:
            return CheckResult(
                "Dependencias Python",
                CheckStatus.WARN,
                f"obrigatorias OK; opcionais faltando: {', '.join(opcionais)}",
                hint=INIT_HINT,
                fixable_by_init=True,
            )
        return CheckResult("Dependencias Python", CheckStatus.OK, "todas instaladas")

    # -- arquivos do projeto -----------------------------------------------

    def check_project_files(self) -> CheckResult:
        faltando = [f for f in REQUIRED_DATA_FILES if not (self.cwd / f).exists()]
        if not faltando:
            return CheckResult(
                "Arquivos de dados",
                CheckStatus.OK,
                f"{len(REQUIRED_DATA_FILES)} arquivos OK",
            )

        no_repo = [f for f in faltando if (PROJECT_ROOT / f).exists()]
        if no_repo:
            return CheckResult(
                "Arquivos de dados",
                CheckStatus.FAIL,
                f"{len(faltando)} nao encontrados a partir de {self.cwd}",
                hint=f"rode os comandos de dentro de {PROJECT_ROOT}",
            )
        return CheckResult(
            "Arquivos de dados",
            CheckStatus.FAIL,
            f"faltando: {', '.join(faltando)}",
            hint="restaure os arquivos do repositorio (git checkout data/)",
        )

    def check_env_file(self) -> CheckResult:
        env = self.cwd / ".env"
        if env.exists():
            return CheckResult("Arquivo .env", CheckStatus.OK, str(env))
        return CheckResult(
            "Arquivo .env",
            CheckStatus.WARN,
            ".env nao existe",
            hint=INIT_HINT,
            fixable_by_init=True,
        )

    def check_discord_token(self) -> CheckResult:
        token = _discord_token(self.cwd)
        if not token:
            return CheckResult(
                "Token do Discord",
                CheckStatus.WARN,
                "DISCORD_TOKEN vazio - `gapo capture` funciona, `gapo run` nao",
                hint="cole o token do bot no .env (o init cria o arquivo)",
            )
        if token in {"your_token_here", "seu_token_aqui"}:
            return CheckResult(
                "Token do Discord",
                CheckStatus.WARN,
                "DISCORD_TOKEN ainda e o placeholder",
                hint="troque pelo token real do seu bot no .env",
            )
        return CheckResult("Token do Discord", CheckStatus.OK, f"configurado ({len(token)} chars)")

    # -- modelos ------------------------------------------------------------

    def check_ollama_server(self) -> CheckResult:
        if ollama_reachable(self.ollama_host):
            return CheckResult(
                "Servidor Ollama",
                CheckStatus.OK,
                f"respondendo em {self.ollama_host}",
            )
        if shutil.which("ollama"):
            return CheckResult(
                "Servidor Ollama",
                CheckStatus.FAIL,
                f"binario instalado, mas {self.ollama_host} nao responde",
                hint="`gapo init` sobe o servidor, ou rode `ollama serve`",
                fixable_by_init=True,
            )
        return CheckResult(
            "Servidor Ollama",
            CheckStatus.FAIL,
            "ollama nao instalado",
            hint="baixe em https://ollama.com/download (ou: gapo init --install-ollama)",
        )

    def check_llm_model(self) -> CheckResult:
        modelos = ollama_models(self.ollama_host)
        if modelos is None:
            return CheckResult(
                "Modelo LLM",
                CheckStatus.FAIL,
                f"{self.llm_model} - impossivel verificar com o Ollama fora do ar",
                hint=INIT_HINT,
                fixable_by_init=True,
            )
        if _model_present(self.llm_model, modelos):
            return CheckResult("Modelo LLM", CheckStatus.OK, self.llm_model)
        return CheckResult(
            "Modelo LLM",
            CheckStatus.FAIL,
            f"{self.llm_model} nao baixado (~4.2GB)",
            hint=INIT_HINT,
            fixable_by_init=True,
        )

    def check_piper_voice(self) -> CheckResult:
        onnx, config = piper_voice_paths(self.tts_voice)
        if onnx.exists() and config.exists():
            mb = onnx.stat().st_size / 1_048_576
            return CheckResult(
                "Voz Piper (TTS)",
                CheckStatus.OK,
                f"{self.tts_voice} ({mb:.0f} MB)",
            )
        faltando = [p.name for p in (onnx, config) if not p.exists()]
        return CheckResult(
            "Voz Piper (TTS)",
            CheckStatus.FAIL,
            f"{self.tts_voice} incompleto em {onnx.parent} (falta: {', '.join(faltando)})",
            hint=INIT_HINT,
            fixable_by_init=True,
        )

    def check_yolo_model(self) -> CheckResult:
        path = self.cwd / self.yolo_model
        if path.exists():
            return CheckResult("Modelo YOLO", CheckStatus.OK, str(path))
        return CheckResult(
            "Modelo YOLO",
            CheckStatus.WARN,
            f"{self.yolo_model} ausente - OCR usa so os presets de ROI",
            hint=INIT_HINT,
            fixable_by_init=True,
        )

    def check_opus(self) -> CheckResult:
        """opuslib importa mesmo sem a lib nativa do Opus; so o encoder revela."""
        if not _module_available("opuslib"):
            return CheckResult(
                "Opus (voz Discord)",
                CheckStatus.WARN,
                "opuslib nao instalado",
                hint=INIT_HINT,
                fixable_by_init=True,
            )
        try:
            import opuslib

            opuslib.Encoder(48000, 1, opuslib.APPLICATION_AUDIO)
        except Exception as e:
            return CheckResult(
                "Opus (voz Discord)",
                CheckStatus.WARN,
                f"lib nativa indisponivel: {str(e)[:80]}",
                hint="Windows: opus.dll no PATH | Linux: apt install libopus0",
            )
        return CheckResult("Opus (voz Discord)", CheckStatus.OK, "encoder Opus funcionando")


# -- helpers compartilhados com o setup -------------------------------------


def ollama_reachable(host: str = OLLAMA_HOST, timeout: float = 3.0) -> bool:
    return ollama_models(host, timeout) is not None


def ollama_models(host: str = OLLAMA_HOST, timeout: float = 3.0) -> list[str] | None:
    """Modelos presentes no Ollama, ou None se o servidor nao responde.

    Fala HTTP direto em vez de usar o pacote `ollama`: o doctor precisa rodar
    antes de as dependencias existirem.
    """
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return [m.get("name", "") for m in payload.get("models", [])]


def _model_present(wanted: str, available: list[str]) -> bool:
    """O Ollama lista `nome` como `nome:latest` quando nao ha tag explicita."""
    alvo = wanted if ":" in wanted else f"{wanted}:latest"
    return any(m in {wanted, alvo} for m in available)


def _max_vram_mib(saida_nvidia_smi: str) -> int:
    """Maior VRAM (MiB) entre as GPUs listadas; 0 se nao der para ler."""
    maior = 0
    for linha in saida_nvidia_smi.splitlines():
        for campo in linha.split(","):
            campo = campo.strip()
            if campo.endswith("MiB"):
                try:
                    maior = max(maior, int(campo.removesuffix("MiB").strip()))
                except ValueError:
                    continue
    return maior


def _module_available(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _run(cmd: list[str], timeout: float = 10.0) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return False, ""
    return result.returncode == 0, result.stdout.strip()


def _discord_token(cwd: Path) -> str:
    """Le o token do ambiente ou do .env, sem depender de pydantic-settings."""
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if token:
        return token
    env = cwd / ".env"
    if not env.exists():
        return ""
    for raw in env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("DISCORD_TOKEN="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def resolve_model_names() -> dict[str, str]:
    """Nomes dos modelos vindos das settings; cai nos defaults se pydantic faltar."""
    try:
        from gapo.config.settings import get_settings

        settings = get_settings()
        return {
            "llm_model": settings.model.llm_name,
            "tts_voice": settings.model.tts_model,
            "yolo_model": settings.model.yolo_model,
        }
    except Exception:
        return {
            "llm_model": "qwen2.5:7b-instruct-q4_K_M",
            "tts_voice": "pt_BR-faber-medium",
            "yolo_model": YOLO_MODEL_FILE,
        }
