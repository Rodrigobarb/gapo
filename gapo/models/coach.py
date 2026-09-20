from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CoachMode(str, Enum):
    EVENT_DRIVEN = "event_driven"
    GAPO_CHAT = "gapo_chat"


@dataclass
class CoachPrompt:
    mode: CoachMode
    system_prompt: str
    user_prompt: str
    context: dict = field(default_factory=dict)
    few_shot_examples: list[dict] = field(default_factory=list)
    max_tokens: int = 150
    temperature: float = 0.3

    def to_messages(self) -> list[dict]:
        messages = [{"role": "system", "content": self.system_prompt}]
        for ex in self.few_shot_examples:
            messages.append({"role": "user", "content": ex["user"]})
            messages.append({"role": "assistant", "content": ex["assistant"]})
        messages.append({"role": "user", "content": self.user_prompt})
        return messages


@dataclass
class CoachResponse:
    text: str
    mode: CoachMode
    timestamp: datetime = field(default_factory=datetime.now)
    tokens_used: int = 0
    latency_ms: int = 0
    raw_response: str = ""

    def clean_for_tts(self) -> str:
        text = self.text.strip()
        text = text.replace("*", "").replace("#", "").replace("`", "")
        return text


EVENT_COACH_SYSTEM_PROMPT = """Você é um coach de League of Legends elo Challenger falando português brasileiro.
Sua função: dar UMA dica curta (máx 2 frases), acionável, focada no AGORA.
Tom: encorajador, direto, parceiro de duo. NÃO explique conceitos básicos.
Use o contexto da partida para ser específico: champion, level, itens, posição, timers.
Se não tiver info suficiente, dê dica genérica de macro."""


GAPO_CHAT_SYSTEM_PROMPT = """Você é "Gapo", coach de LoL elo Challenger, respondendo por voz no Discord.
Contexto: partida atual + conhecimento geral (matchups, builds, counters, powerspikes, macro).
Responda em PT-BR, direto, máx 3 frases. Use contexto da partida SE relevante.
Tom: parceiro de duo, sem formalidade, gírias de LoL ok (ex: "flash", "gank", "wave", "powerspike").
Se não souber, diga "Não tenho certeza disso" - NÃO invente.
Priorize acionável > educativo."""


EVENT_FEW_SHOT_EXAMPLES = [
    {
        "user": "Evento: gank_imminent\nPrioridade: high\nDetalhes: Inimigo Zed sumiu do minimapa há 12s. Possível gank bot.\nContexto: {'player_champ': 'Jinx', 'player_level': 6, 'enemy_jungle': 'Zed'}",
        "assistant": "Zed sumiu há 12s, provavelmente vindo bot. Você é Jinx sem flash - recue pra torre AGORA e peça pra sup wardar tribush.",
    },
    {
        "user": "Evento: objective_contested\nPrioridade: critical\nDetalhes: Dragão nascendo em 5s. 3 inimigos nas proximidades.\nContexto: {'player_champ': 'Lee Sin', 'dragon_timer': 5, 'enemies_near': 3}",
        "assistant": "Dragão nasce em 5s, 3 inimigos lá. Você é Lee Sin - smite steal é sua win condition. Entre pelo pit lateral, Q no dragão + smite + kick pra segurança.",
    },
    {
        "user": "Evento: powerspike\nPrioridade: medium\nDetalhes: Powerspike atingido: Level 6 completado.\nContexto: {'player_champ': 'Ahri', 'level': 6, 'enemy_champ': 'Syndra'}",
        "assistant": "Level 6 na Ahri vs Syndra sem flash. Charm + R + Q + W = kill garantida se acertar. Force all-in na próxima wave.",
    },
]


GAPO_FEW_SHOT_EXAMPLES = [
    {
        "user": "Gapo qual a melhor jogada agora?\nContexto: {'player_champ': 'Zed', 'level': 6, 'enemy_champ': 'Syndra', 'enemy_flash': False, 'game_time': 420}",
        "assistant": "Você é Zed 6 contra Syndra sem flash. Empurra wave com W-Q-E e roama bot ou invade jg inimigo. Cuidado com herald.",
    },
    {
        "user": "Gapo o que countera Malphite top?\nContexto: {}",
        "assistant": "Malphite fraco early. Pega Darius, Fiora, Gwen ou Quinn. Evita tanks. Build: Stridebreaker ou Divine Sunderer. Force trocas level 1-5 antes do primeiro item dele.",
    },
    {
        "user": "Gapo devo dar flash pra pegar esse kill?\nContexto: {'enemy_hp_pct': 15, 'enemy_flash': False, 'ally_jungle_nearby': True, 'game_time': 600}",
        "assistant": "Inimigo 15% HP, sem flash, seu jg vindo. Vale o flash se garante kill + torre/placa. Se só kill e você fica sem flash pra gank nos próximos 5min, não vale.",
    },
]


def build_event_prompt(event_type: str, message: str, game_state: dict) -> CoachPrompt:
    user_prompt = f"Evento: {event_type}\nDetalhes: {message}\nContexto: {game_state}"
    return CoachPrompt(
        mode=CoachMode.EVENT_DRIVEN,
        system_prompt=EVENT_COACH_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        context=game_state,
        few_shot_examples=EVENT_FEW_SHOT_EXAMPLES,
        max_tokens=100,
        temperature=0.3,
    )


def build_gapo_prompt(question: str, game_state: dict) -> CoachPrompt:
    context_summary = {
        "champ": game_state.get("player", {}).get("champion", "?"),
        "level": game_state.get("player", {}).get("level", "?"),
        "hp_pct": game_state.get("player", {}).get("hp_pct", "?"),
        "items": game_state.get("player", {}).get("items", []),
        "enemies": list(game_state.get("enemies_visible", {}).keys()),
        "game_time": game_state.get("game_time", 0),
    }
    user_prompt = f"Pergunta: {question}\nContexto partida: {context_summary}"
    return CoachPrompt(
        mode=CoachMode.GAPO_CHAT,
        system_prompt=GAPO_CHAT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        context=game_state,
        few_shot_examples=GAPO_FEW_SHOT_EXAMPLES,
        max_tokens=200,
        temperature=0.4,
    )