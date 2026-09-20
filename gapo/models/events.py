from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class EventType(str, Enum):
    GANK_IMMINENT = "gank_imminent"
    OBJECTIVE_CONTESTED = "objective_contested"
    FIGHT_STARTED = "fight_started"
    POSITIONING_ERROR = "positioning_error"
    WAVE_MANAGEMENT = "wave_management"
    POWERSPIKE = "powerspike"
    SUMMONER_USED = "summoner_used"
    RECALL_DETECTED = "recall_detected"
    ROAM_DETECTED = "roam_detected"
    WARD_EXPIRED = "ward_expired"


class EventPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GameEvent:
    event_type: EventType
    priority: EventPriority
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: dict = field(default_factory=dict)
    champion_involved: Optional[str] = None
    location: Optional[str] = None
    cooldown_seconds: float = 5.0

    def to_coach_prompt(self) -> str:
        return (
            f"Evento: {self.event_type.value}\n"
            f"Prioridade: {self.priority.value}\n"
            f"Detalhes: {self.message}\n"
            f"Contexto: {self.context}"
        )


@dataclass
class EventRule:
    event_type: EventType
    condition: str
    priority: EventPriority
    message_template: str
    cooldown: float = 5.0


DEFAULT_EVENT_RULES = [
    EventRule(
        event_type=EventType.GANK_IMMINENT,
        condition="enemy_missing > 10s AND enemy_proximity < 3000",
        priority=EventPriority.HIGH,
        message_template="Inimigo {champion} sumiu do minimapa há {missing_time}s. Possível gank na {lane}.",
        cooldown=15.0,
    ),
    EventRule(
        event_type=EventType.OBJECTIVE_CONTESTED,
        condition="dragon_spawning OR baron_spawning AND enemies_near_objective > 0",
        priority=EventPriority.CRITICAL,
        message_template="{objective} nascendo em {timer}s. {enemy_count} inimigos nas proximidades.",
        cooldown=10.0,
    ),
    EventRule(
        event_type=EventType.FIGHT_STARTED,
        condition="multiple_hp_dropping AND spells_used > 2",
        priority=EventPriority.HIGH,
        message_template="Teamfight iniciada em {location}. Foque {target_priority}.",
        cooldown=8.0,
    ),
    EventRule(
        event_type=EventType.POSITIONING_ERROR,
        condition="player_alone_enemy_side AND no_vision > 5s",
        priority=EventPriority.MEDIUM,
        message_template="Você está sozinho no lado inimigo sem visão. Recue ou peça cover.",
        cooldown=20.0,
    ),
    EventRule(
        event_type=EventType.WAVE_MANAGEMENT,
        condition="wave_under_turret AND player_not_in_lane > 10s",
        priority=EventPriority.MEDIUM,
        message_template="Wave sob sua torre há {time}s. Perde CS e XP. Volte para a lane.",
        cooldown=30.0,
    ),
    EventRule(
        event_type=EventType.POWERSPIKE,
        condition="level == 6 OR mythic_completed OR legendary_completed",
        priority=EventPriority.MEDIUM,
        message_template="Powerspike atingido: {detail}. Procure trocas favoráveis agora.",
        cooldown=60.0,
    ),
    EventRule(
        event_type=EventType.SUMMONER_USED,
        condition="enemy_flash_used OR enemy_ignite_used OR enemy_heal_used",
        priority=EventPriority.LOW,
        message_template="{enemy} usou {spell}. Cooldown: {cd}s. Janela de oportunidade.",
        cooldown=30.0,
    ),
]