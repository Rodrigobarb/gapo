"""Garante que os prompts em data/prompts/ casam com o que o PromptBuilder passa.

Um placeholder a mais no YAML levantava KeyError dentro do `except` do coach:
o bot conectava, entrava na call e ficava mudo sem nenhum erro visivel.
"""

import re
from pathlib import Path

import pytest
import yaml

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "data" / "prompts"

# Espelha os kwargs de PromptBuilder.build_event_prompt / build_gapo_prompt.
PLACEHOLDERS_DISPONIVEIS = {
    "event_coach_v1.yaml": {"event_type", "priority", "message", "event_message", "game_state"},
    "gapo_coach_v1.yaml": {"question", "game_state"},
}


def _template(nome: str) -> str:
    data = yaml.safe_load((PROMPTS_DIR / nome).read_text(encoding="utf-8"))
    return data["user_prompt_template"]


@pytest.mark.parametrize("nome", sorted(PLACEHOLDERS_DISPONIVEIS))
class TestTemplates:
    def test_so_usa_placeholders_que_o_builder_fornece(self, nome):
        exigidos = set(re.findall(r"\{(\w+)\}", _template(nome)))
        assert exigidos <= PLACEHOLDERS_DISPONIVEIS[nome]

    def test_format_nao_levanta(self, nome):
        valores = {k: f"<{k}>" for k in PLACEHOLDERS_DISPONIVEIS[nome]}
        assert _template(nome).format(**valores)

    def test_tem_system_prompt(self, nome):
        data = yaml.safe_load((PROMPTS_DIR / nome).read_text(encoding="utf-8"))
        assert data["system_prompt"].strip()


class TestSafeFormat:
    def test_placeholder_desconhecido_cai_no_fallback(self):
        from gapo.infrastructure.ollama.prompt_builder import _safe_format

        assert _safe_format("{inexistente}", fallback="padrao", question="oi") == "padrao"

    def test_template_vazio_cai_no_fallback(self):
        from gapo.infrastructure.ollama.prompt_builder import _safe_format

        assert _safe_format("", fallback="padrao") == "padrao"

    def test_template_valido_e_usado(self):
        from gapo.infrastructure.ollama.prompt_builder import _safe_format

        assert _safe_format("P: {question}", fallback="padrao", question="oi") == "P: oi"


class TestCoachServiceExigeBuilder:
    def test_prompt_builder_none_falha_no_construtor(self):
        from gapo.services.coach_service import CoachService

        with pytest.raises(ValueError, match="PromptBuilder"):
            CoachService(object(), None, object())
