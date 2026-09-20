"""`gapo init`: deixa a maquina pronta - instala dependencias e baixa modelos.

Cada passo e idempotente: se ja estiver no lugar, e pulado. Nenhum passo
levanta excecao; todos devolvem StepResult para o init seguir em frente e
mostrar o resumo no fim.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from gapo.bootstrap.console import Terminal
from gapo.bootstrap.diagnostics import CheckStatus, SetupReport, StepResult
from gapo.bootstrap.doctor import ollama_models, ollama_reachable
from gapo.bootstrap.requirements import (
    OLLAMA_HOST,
    PROJECT_ROOT,
    PY_PACKAGES,
    RUNTIME_DIRS,
    piper_voice_paths,
    piper_voice_urls,
)

ENV_TEMPLATE = """# Discord Bot Configuration
DISCORD_TOKEN=seu_token_aqui
DISCORD_APPLICATION_ID=seu_app_id_aqui

# Opcional: sobrescreve os defaults
# GAPO_MODEL_LLM_NAME=qwen2.5:7b-instruct-q4_K_M
# GAPO_MODEL_TTS_MODEL=pt_BR-faber-medium
# GAPO_CAPTURE_FPS=3
# GAPO_LOG_LEVEL=INFO
# GAPO_COACH_EVENT_COOLDOWN_SECONDS=5.0
# GAPO_COACH_GAPO_COOLDOWN_SECONDS=10.0
"""

CONFIG_TEMPLATE = """# Gapo Configuration
# Referencia dos defaults. O runtime le de gapo/config/settings.py + .env;
# use este arquivo como documentacao e para montar overrides no Docker.
model:
  llm_name: "qwen2.5:7b-instruct-q4_K_M"
  llm_ctx_size: 2048
  llm_temperature: 0.3
  tts_model: "pt_BR-faber-medium"
  yolo_model: "yolov8n.onnx"

capture:
  fps: 3
  monitor_index: 0
  resolution_width: 1920
  resolution_height: 1080
  use_dxcam: true

ocr:
  confidence_threshold: 0.6
  use_gpu: false
  roi_padding: 5
  preprocess_scale: 2.0

coach:
  event_cooldown_seconds: 5.0
  gapo_cooldown_seconds: 10.0
  max_response_sentences: 3
  enable_event_coach: true
  enable_gapo_chat: true
"""

# Extra [dev] do pyproject: (distribuicao, modulo importavel).
DEV_PACKAGES = (
    ("pytest", "pytest"),
    ("ruff", "ruff"),
    ("mypy", "mypy"),
    ("pre-commit", "pre_commit"),
)

PIP_NOISE_PREFIXES = ("Requirement already satisfied",)
PIP_INTERESTING_PREFIXES = ("Collecting", "Downloading", "Installing", "Successfully", "ERROR")


class SetupService:
    """Executa os passos do init e reporta o progresso no terminal."""

    def __init__(
        self,
        terminal: Terminal | None = None,
        llm_model: str = "qwen2.5:7b-instruct-q4_K_M",
        tts_voice: str = "pt_BR-faber-medium",
        yolo_model: str = "yolov8n.onnx",
        ollama_host: str = OLLAMA_HOST,
        cwd: Path | None = None,
    ) -> None:
        self.term = terminal or Terminal()
        self.llm_model = llm_model
        self.tts_voice = tts_voice
        self.yolo_model = yolo_model
        self.ollama_host = ollama_host
        self.cwd = cwd or Path.cwd()

    # -- estrutura local ----------------------------------------------------

    def ensure_directories(self) -> StepResult:
        for d in RUNTIME_DIRS:
            (self.cwd / d).mkdir(parents=True, exist_ok=True)
        return self._ok("Diretorios", f"{len(RUNTIME_DIRS)} diretorios prontos")

    def ensure_env_file(self) -> StepResult:
        env = self.cwd / ".env"
        if env.exists():
            return self._ok("Arquivo .env", "ja existe (mantido)")
        env.write_text(ENV_TEMPLATE, encoding="utf-8")
        return self._warn("Arquivo .env", ".env criado - cole seu DISCORD_TOKEN nele")

    def ensure_config_file(self) -> StepResult:
        config = self.cwd / "config" / "config.yaml"
        if config.exists():
            return self._ok("config.yaml", "ja existe (mantido)")
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(CONFIG_TEMPLATE, encoding="utf-8")
        return self._ok("config.yaml", f"criado em {config}")

    # -- dependencias Python -------------------------------------------------

    def install_dependencies(self, dev: bool = False) -> StepResult:
        """Instala o projeto em modo editavel, so quando falta alguma coisa.

        Rodar pip a toa nao e apenas lento: no Windows, `pip install -e .`
        reescreve o venv/Scripts/gapo.exe, e o proprio `gapo init` em execucao
        mantem esse arquivo travado.
        """
        if not (PROJECT_ROOT / "pyproject.toml").exists():
            return self._warn(
                "Dependencias Python",
                f"pyproject.toml nao encontrado em {PROJECT_ROOT} - instale na mao",
            )

        if not self._missing_packages(dev):
            return self._ok("Dependencias Python", "ja instaladas - nada a fazer")

        target = ".[dev]" if dev else "."
        self.term.print(f"   pip install -e {target}  (pode levar varios minutos)", style="dim")
        cmd = [sys.executable, "-m", "pip", "install", "-e", target]
        code, tail = self._stream(cmd, cwd=PROJECT_ROOT, echo="filtrado", timeout=3600)
        importlib.invalidate_caches()

        if code != 0:
            extra = ""
            if sys.platform == "win32" and "denied" in tail.lower():
                extra = " - feche o `gapo` e rode `python -m gapo init`"
            return self._fail("Dependencias Python", f"pip falhou (codigo {code}): {tail}{extra}")

        ainda_faltando = [
            p.dist
            for p in PY_PACKAGES
            if p.applies() and not p.optional and not _importable(p.module)
        ]
        if ainda_faltando:
            return self._warn(
                "Dependencias Python",
                f"pip terminou, mas seguem ausentes: {', '.join(ainda_faltando)}",
            )
        return self._ok("Dependencias Python", "todas instaladas")

    @staticmethod
    def _missing_packages(dev: bool) -> list[str]:
        """Distribuicoes ausentes, opcionais e dev incluidos quando pedido."""
        faltando = [p.dist for p in PY_PACKAGES if p.applies() and not _importable(p.module)]
        if dev:
            faltando += [
                dist
                for dist, modulo in DEV_PACKAGES
                if not _importable(modulo)
            ]
        return faltando

    # -- Ollama ---------------------------------------------------------------

    def ensure_ollama(self, install: bool = False) -> StepResult:
        """Garante binario instalado e servidor no ar em `self.ollama_host`."""
        if ollama_reachable(self.ollama_host):
            return self._ok("Servidor Ollama", f"ja respondendo em {self.ollama_host}")

        binario = shutil.which("ollama")
        if not binario and install:
            resultado = self._install_ollama()
            if not resultado.ok:
                return resultado
            binario = shutil.which("ollama")

        if not binario:
            return self._fail(
                "Servidor Ollama",
                "ollama nao instalado - baixe em https://ollama.com/download "
                "ou rode `gapo init --install-ollama` (Windows/winget)",
            )

        self.term.print("   subindo `ollama serve` em background...", style="dim")
        try:
            subprocess.Popen(
                [binario, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as e:
            return self._fail("Servidor Ollama", f"nao consegui iniciar: {e}")

        if self._wait_for_ollama():
            return self._ok("Servidor Ollama", f"iniciado em {self.ollama_host}")
        return self._fail(
            "Servidor Ollama",
            f"{self.ollama_host} nao respondeu a tempo - rode `ollama serve` numa outra janela",
        )

    def pull_llm_model(self) -> StepResult:
        modelos = ollama_models(self.ollama_host)
        if modelos is None:
            return self._fail("Modelo LLM", "Ollama fora do ar - passo pulado")

        alvo = self.llm_model if ":" in self.llm_model else f"{self.llm_model}:latest"
        if any(m in {self.llm_model, alvo} for m in modelos):
            return self._ok("Modelo LLM", f"{self.llm_model} ja baixado")

        self.term.print(f"   baixando {self.llm_model} (~4.2GB)...", style="dim")
        try:
            erro = self._pull_via_api()
        except (urllib.error.URLError, OSError) as e:
            return self._fail("Modelo LLM", f"download falhou: {e}")
        if erro:
            return self._fail("Modelo LLM", erro)
        return self._ok("Modelo LLM", f"{self.llm_model} pronto")

    # -- Piper / YOLO ----------------------------------------------------------

    def download_piper_voice(self) -> StepResult:
        onnx, config = piper_voice_paths(self.tts_voice)
        if onnx.exists() and config.exists():
            return self._ok("Voz Piper (TTS)", f"{self.tts_voice} ja baixada")

        try:
            url_onnx, url_config = piper_voice_urls(self.tts_voice)
        except ValueError as e:
            return self._fail("Voz Piper (TTS)", str(e))

        onnx.parent.mkdir(parents=True, exist_ok=True)
        for url, destino in ((url_onnx, onnx), (url_config, config)):
            if destino.exists():
                continue
            erro = self._download(url, destino, label=destino.name)
            if erro:
                return self._fail("Voz Piper (TTS)", erro)
        return self._ok("Voz Piper (TTS)", f"{self.tts_voice} em {onnx.parent}")

    def export_yolo_model(self) -> StepResult:
        """Exporta o yolov8n para ONNX via ultralytics (opcional: OCR roda sem)."""
        destino = self.cwd / self.yolo_model
        if destino.exists():
            return self._ok("Modelo YOLO", f"{destino.name} ja existe")

        if not _importable("ultralytics"):
            return self._warn(
                "Modelo YOLO",
                "ultralytics nao instalado - OCR segue usando so os presets de ROI",
            )

        self.term.print("   exportando yolov8n para ONNX...", style="dim")
        script = (
            "from ultralytics import YOLO; "
            "YOLO('yolov8n.pt').export(format='onnx', opset=12)"
        )
        code, tail = self._stream(
            [sys.executable, "-c", script], cwd=self.cwd, echo="tudo", timeout=900
        )
        if code != 0 or not destino.exists():
            return self._warn("Modelo YOLO", f"export falhou (codigo {code}): {tail}")
        return self._ok("Modelo YOLO", str(destino))

    # -- orquestracao -----------------------------------------------------------

    def run_all(
        self,
        skip_deps: bool = False,
        skip_ollama: bool = False,
        skip_piper: bool = False,
        skip_yolo: bool = False,
        install_ollama: bool = False,
        dev: bool = False,
    ) -> SetupReport:
        report = SetupReport()

        self.term.section("1/4 Estrutura local")
        report.add(self.ensure_directories())
        report.add(self.ensure_env_file())
        report.add(self.ensure_config_file())

        self.term.section("2/4 Dependencias Python")
        if skip_deps:
            report.add(self._skip("Dependencias Python"))
        else:
            report.add(self.install_dependencies(dev=dev))

        self.term.section("3/4 LLM local (Ollama)")
        if skip_ollama:
            report.add(self._skip("Servidor Ollama"))
            report.add(self._skip("Modelo LLM"))
        else:
            servidor = report.add(self.ensure_ollama(install=install_ollama))
            if servidor.ok:
                report.add(self.pull_llm_model())
            else:
                report.add(self._skip("Modelo LLM", "servidor indisponivel"))

        self.term.section("4/4 Modelos de voz e visao")
        report.add(self._skip("Voz Piper (TTS)") if skip_piper else self.download_piper_voice())
        report.add(self._skip("Modelo YOLO") if skip_yolo else self.export_yolo_model())

        return report

    # -- infraestrutura interna ---------------------------------------------------

    def _install_ollama(self) -> StepResult:
        if sys.platform != "win32" or not shutil.which("winget"):
            return self._fail(
                "Servidor Ollama",
                "instalacao automatica so via winget (Windows) - "
                "baixe em https://ollama.com/download",
            )
        self.term.print("   winget install Ollama.Ollama ...", style="dim")
        code, tail = self._stream(
            [
                "winget",
                "install",
                "--id",
                "Ollama.Ollama",
                "-e",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ],
            cwd=self.cwd,
            echo="tudo",
            timeout=1800,
        )
        if code != 0:
            return self._fail("Servidor Ollama", f"winget falhou (codigo {code}): {tail}")
        return self._ok("Servidor Ollama", "instalado via winget")

    def _wait_for_ollama(self, timeout: float = 30.0) -> bool:
        limite = time.monotonic() + timeout
        while time.monotonic() < limite:
            if ollama_reachable(self.ollama_host, timeout=2.0):
                return True
            time.sleep(1.0)
        return False

    def _pull_via_api(self) -> str:
        """Faz o pull via HTTP e devolve a mensagem de erro, ou "" em caso de sucesso.

        Usa a API em vez do pacote `ollama` porque o init pode rodar antes das
        dependencias existirem.
        """
        payload = json.dumps({"model": self.llm_model, "stream": True}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_host}/api/pull",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        progress = self.term.progress_line()
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw in resp:
                linha = raw.decode("utf-8", errors="replace").strip()
                if not linha:
                    continue
                try:
                    evento = json.loads(linha)
                except ValueError:
                    continue
                if evento.get("error"):
                    progress.close()
                    return str(evento["error"])
                progress.update(_pull_status(evento))
        progress.close()
        return ""

    def _download(self, url: str, destino: Path, label: str) -> str:
        """Baixa para um .part e so renomeia no fim, para nao deixar arquivo torto."""
        parcial = destino.with_suffix(destino.suffix + ".part")
        progress = self.term.progress_line()
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                baixado = 0
                with parcial.open("wb") as f:
                    while chunk := resp.read(262_144):
                        f.write(chunk)
                        baixado += len(chunk)
                        progress.update(_download_status(label, baixado, total))
            parcial.replace(destino)
            progress.close()
            return ""
        except (urllib.error.URLError, OSError) as e:
            progress.close()
            parcial.unlink(missing_ok=True)
            return f"{label}: {e}"

    def _stream(
        self,
        cmd: list[str],
        cwd: Path,
        echo: str,
        timeout: float,
    ) -> tuple[int, str]:
        """Roda o comando ecoando o progresso e guardando as ultimas linhas p/ erro."""
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as e:
            return 1, str(e)

        cauda: list[str] = []
        assert proc.stdout is not None
        for raw in proc.stdout:
            linha = raw.rstrip()
            if not linha:
                continue
            cauda.append(linha)
            del cauda[:-12]
            if self._should_echo(linha, echo):
                self.term.print(f"   {linha[:110]}", style="dim", markup=False)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            return 1, f"timeout apos {timeout:.0f}s"
        return proc.returncode, " | ".join(cauda[-3:])[:300]

    @staticmethod
    def _should_echo(linha: str, echo: str) -> bool:
        """"tudo" ecoa o comando inteiro; "filtrado" so o que mostra progresso real."""
        if echo == "tudo":
            return True
        if echo != "filtrado" or linha.startswith(PIP_NOISE_PREFIXES):
            return False
        return linha.startswith(PIP_INTERESTING_PREFIXES)

    def _ok(self, name: str, detail: str) -> StepResult:
        step = StepResult(name, CheckStatus.OK, detail)
        self.term.status(CheckStatus.OK, f"{name}: {detail}")
        return step

    def _warn(self, name: str, detail: str) -> StepResult:
        step = StepResult(name, CheckStatus.WARN, detail)
        self.term.status(CheckStatus.WARN, f"{name}: {detail}")
        return step

    def _fail(self, name: str, detail: str) -> StepResult:
        step = StepResult(name, CheckStatus.FAIL, detail)
        self.term.status(CheckStatus.FAIL, f"{name}: {detail}")
        return step

    def _skip(self, name: str, motivo: str = "pulado por opcao") -> StepResult:
        step = StepResult(name, CheckStatus.WARN, motivo)
        self.term.status(CheckStatus.WARN, f"{name}: {motivo}")
        return step


def _pull_status(evento: dict) -> str:
    status = evento.get("status", "")
    total = evento.get("total") or 0
    completed = evento.get("completed") or 0
    if total:
        pct = completed / total * 100
        return f"{status} {pct:5.1f}% ({completed / 1_048_576:.0f}/{total / 1_048_576:.0f} MB)"
    return status


def _download_status(label: str, baixado: int, total: int) -> str:
    if total:
        return f"{label} {baixado / total * 100:5.1f}% ({baixado / 1_048_576:.1f} MB)"
    return f"{label} {baixado / 1_048_576:.1f} MB"


def _importable(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False
