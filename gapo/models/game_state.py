from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Team(str, Enum):
    BLUE = "blue"
    RED = "red"
    UNKNOWN = "unknown"


class Role(str, Enum):
    TOP = "top"
    JUNGLE = "jungle"
    MID = "mid"
    ADC = "adc"
    SUPPORT = "support"
    UNKNOWN = "unknown"


@dataclass
class PlayerState:
    champion: str = ""
    level: int = 1
    hp: int = 0
    max_hp: int = 0
    mana: int = 0
    max_mana: int = 0
    gold: int = 0
    cs: int = 0
    xp: int = 0
    items: list[str] = field(default_factory=list)
    summoner_spells: list[str] = field(default_factory=list)
    keystone_rune: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    is_visible: bool = True
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class MinimapState:
    player_position: tuple[float, float] = (0.0, 0.0)
    allies: dict[str, tuple[float, float]] = field(default_factory=dict)
    enemies: dict[str, tuple[float, float]] = field(default_factory=dict)
    wards: list[tuple[float, float]] = field(default_factory=list)
    objectives: dict[str, tuple[float, float]] = field(default_factory=dict)
    dragon_timer: Optional[float] = None
    baron_timer: Optional[float] = None
    herald_timer: Optional[float] = None


@dataclass
class GameState:
    timestamp: datetime = field(default_factory=datetime.now)
    game_time_seconds: float = 0.0
    phase: str = "loading"
    player: PlayerState = field(default_factory=PlayerState)
    allies: dict[str, PlayerState] = field(default_factory=dict)
    enemies: dict[str, PlayerState] = field(default_factory=dict)
    minimap: MinimapState = field(default_factory=MinimapState)
    chat_messages: list[dict] = field(default_factory=list)
    tab_open: bool = False
    shop_open: bool = False

    def get_ally_by_role(self, role: Role) -> Optional[PlayerState]:
        for ally in self.allies.values():
            if ally.champion.lower() in self._role_champions(role):
                return ally
        return None

    def get_enemy_by_role(self, role: Role) -> Optional[PlayerState]:
        for enemy in self.enemies.values():
            if enemy.champion.lower() in self._role_champions(role):
                return enemy
        return None

    def _role_champions(self, role: Role) -> set[str]:
        return set()

    def to_context_dict(self) -> dict:
        return {
            "game_time": self.game_time_seconds,
            "phase": self.phase,
            "player": {
                "champion": self.player.champion,
                "level": self.player.level,
                "hp_pct": round(self.player.hp / max(self.player.max_hp, 1) * 100, 1),
                "mana_pct": round(self.player.mana / max(self.player.max_mana, 1) * 100, 1),
                "gold": self.player.gold,
                "cs": self.player.cs,
                "items": self.player.items,
                "summoners": self.player.summoner_spells,
                "keystone": self.player.keystone_rune,
            },
            "allies": {
                k: {"champ": v.champion, "level": v.level, "hp_pct": round(v.hp / max(v.max_hp, 1) * 100, 1)}
                for k, v in self.allies.items()
            },
            "enemies_visible": {
                k: {"champ": v.champion, "level": v.level, "hp_pct": round(v.hp / max(v.max_hp, 1) * 100, 1)}
                for k, v in self.enemies.items() if v.is_visible
            },
            "minimap": {
                "player_pos": self.minimap.player_position,
                "enemies_known": list(self.minimap.enemies.keys()),
                "dragon_timer": self.minimap.dragon_timer,
                "baron_timer": self.minimap.baron_timer,
            },
            "recent_chat": self.chat_messages[-5:] if self.chat_messages else [],
        }


class GameStateHistory:
    def __init__(self, max_seconds: int = 30):
        self.max_seconds = max_seconds
        self._states: list[GameState] = []

    def add(self, state: GameState) -> None:
        self._states.append(state)
        self._prune()

    def _prune(self) -> None:
        if not self._states:
            return
        cutoff = self._states[-1].timestamp.timestamp() - self.max_seconds
        self._states = [s for s in self._states if s.timestamp.timestamp() > cutoff]

    def get_latest(self) -> Optional[GameState]:
        return self._states[-1] if self._states else None

    def get_context_window(self, seconds: int = 10) -> list[GameState]:
        if not self._states:
            return []
        cutoff = self._states[-1].timestamp.timestamp() - seconds
        return [s for s in self._states if s.timestamp.timestamp() > cutoff]

    def get_trend(self, attr: str, seconds: int = 5) -> list:
        window = self.get_context_window(seconds)
        return [getattr(s, attr, None) for s in window if hasattr(s, attr)]