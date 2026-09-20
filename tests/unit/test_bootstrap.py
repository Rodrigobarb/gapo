import json
import subprocess
import sys
from pathlib import Path

import pytest

from gapo.bootstrap.console import _strip_markup
from gapo.bootstrap.diagnostics import CheckResult, CheckStatus, DiagnosticsReport
from gapo.bootstrap.doctor import (
    DoctorService,
    _discord_token,
    _max_vram_mib,
    _model_present,
    ollama_models,
)
from gapo.bootstrap.requirements import PY_PACKAGES, piper_voice_paths, piper_voice_urls


class TestPiperVoice:
    def test_url_intercala_familia_do_idioma(self):
        onnx, config = piper_voice_urls("pt_BR-faber-medium")
        assert onnx.endswith("/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx")
        assert config == f"{onnx}.json"

    def test_nome_invalido_explode(self):
        with pytest.raises(ValueError):
            piper_voice_urls("faber")

    def test_paths_usam_o_diretorio_informado(self, tmp_path):
        onnx, config = piper_voice_paths("pt_BR-faber-medium", model_dir=tmp_path)
        assert onnx == tmp_path / "pt_BR-faber-medium.onnx"
        assert config == tmp_path / "pt_BR-faber-medium.onnx.json"


class TestOllamaHelpers:
    def test_modelo_sem_tag_casa_com_latest(self):
        assert _model_present("qwen2.5", ["qwen2.5:latest"])

    def test_modelo_com_tag_exige_tag_igual(self):
        assert _model_present("qwen2.5:7b", ["qwen2.5:7b"])
        assert not _model_present("qwen2.5:7b", ["qwen2.5:latest"])

    def test_servidor_fora_do_ar_devolve_none(self):
        assert ollama_models("http://localhost:1", timeout=0.5) is None


class TestVRAM:
    def test_le_o_maior_valor_entre_as_gpus(self):
        saida = "NVIDIA GeForce GTX 980, 4096 MiB\nNVIDIA RTX 3060, 12288 MiB"
        assert _max_vram_mib(saida) == 12288

    def test_saida_sem_mib_devolve_zero(self):
        assert _max_vram_mib("sem gpu aqui") == 0


class TestDiscordToken:
    def test_le_do_env_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DISCORD_TOKEN", raising=False)
        (tmp_path / ".env").write_text('DISCORD_TOKEN="abc123"\n', encoding="utf-8")
        assert _discord_token(tmp_path) == "abc123"

    def test_variavel_de_ambiente_ganha_do_arquivo(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DISCORD_TOKEN", "do-ambiente")
        (tmp_path / ".env").write_text("DISCORD_TOKEN=do-arquivo\n", encoding="utf-8")
        assert _discord_token(tmp_path) == "do-ambiente"

    def test_sem_env_nem_arquivo(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DISCORD_TOKEN", raising=False)
        assert _discord_token(tmp_path) == ""


class TestReport:
    def _report(self) -> DiagnosticsReport:
        report = DiagnosticsReport()
        report.add(CheckResult("Python", CheckStatus.OK, "3.11"))
        report.add(CheckResult("GPU", CheckStatus.WARN, "sem GPU"))
        report.add(CheckResult("LLM", CheckStatus.FAIL, "faltando", fixable_by_init=True))
        report.add(CheckResult("Ollama", CheckStatus.FAIL, "nao instalado"))
        return report

    def test_agrega_falhas_avisos_e_corrigiveis(self):
        report = self._report()
        assert [c.name for c in report.failures] == ["LLM", "Ollama"]
        assert [c.name for c in report.warnings] == ["GPU"]
        assert [c.name for c in report.fixable] == ["LLM"]

    def test_exit_code_reflete_falhas(self):
        assert self._report().exit_code == 1
        assert DiagnosticsReport().exit_code == 0

    def test_json_serializa(self):
        payload = json.loads(json.dumps(self._report().to_dict()))
        assert payload["healthy"] is False
        assert payload["failures"] == 2
        assert len(payload["checks"]) == 4


class TestChecks:
    def test_arquivos_de_dados_faltando_apontam_para_a_raiz(self, tmp_path):
        check = DoctorService(cwd=tmp_path).check_project_files()
        assert check.status is CheckStatus.FAIL
        assert "gapo" in check.hint

    def test_env_ausente_e_corrigivel_pelo_init(self, tmp_path):
        check = DoctorService(cwd=tmp_path).check_env_file()
        assert check.status is CheckStatus.WARN
        assert check.fixable_by_init

    def test_todo_check_tem_nome_e_detalhe(self):
        for check in DoctorService().run().checks:
            assert check.name and check.detail


class TestRequirements:
    def test_nao_ha_modulo_duplicado(self):
        modulos = [p.module for p in PY_PACKAGES]
        assert len(modulos) == len(set(modulos))


class TestImportsLeves:
    """`gapo doctor` e `gapo init` tem que carregar em ambiente sem dependencias.

    Um import pesado no topo de gapo/cli.py ou de gapo/bootstrap/ derruba
    justamente os dois comandos que existem para consertar isso.
    """

    PESADOS = ("numpy", "cv2", "loguru", "discord", "ollama", "paddleocr", "onnxruntime")

    def _sys_modules_apos_import(self, modulo: str) -> set[str]:
        script = (
            f"import {modulo}, sys, json; "
            "print(json.dumps(sorted(m for m in sys.modules if '.' not in m)))"
        )
        raiz = Path(__file__).resolve().parents[2]
        saida = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(raiz),
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        return set(json.loads(saida.stdout.strip().splitlines()[-1]))

    def test_cli_nao_puxa_runtime(self):
        carregados = self._sys_modules_apos_import("gapo.cli")
        assert not carregados & set(self.PESADOS)

    def test_bootstrap_nao_puxa_runtime(self):
        carregados = self._sys_modules_apos_import("gapo.bootstrap")
        assert not carregados & set(self.PESADOS)


class TestStripMarkup:
    def test_remove_tags_de_estilo(self):
        assert _strip_markup("[bold]oi[/bold]") == "oi"
        assert _strip_markup("[bold green]oi[/]") == "oi"

    def test_preserva_colchetes_comuns(self):
        assert _strip_markup("[OK] pronto") == "[OK] pronto"
