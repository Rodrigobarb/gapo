from dataclasses import dataclass, field
from typing import Optional
from pydantic import BaseModel, Field


@dataclass
class UIRoi:
    name: str
    x: int
    y: int
    width: int
    height: int
    scale: float = 1.0
    preprocess: str = "default"

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class OCRResult:
    text: str
    confidence: float
    bbox: tuple[int, int, int, int]
    roi_name: str


@dataclass
class ParsedHUD:
    hp: Optional[int] = None
    max_hp: Optional[int] = None
    mana: Optional[int] = None
    max_mana: Optional[int] = None
    level: Optional[int] = None
    gold: Optional[int] = None
    cs: Optional[int] = None
    xp: Optional[int] = None
    items: list[str] = field(default_factory=list)
    summoner_spells: list[str] = field(default_factory=list)
    keystone_rune: str = ""

    def to_dict(self) -> dict:
        return {
            "hp": self.hp,
            "max_hp": self.max_hp,
            "mana": self.mana,
            "max_mana": self.max_mana,
            "level": self.level,
            "gold": self.gold,
            "cs": self.cs,
            "xp": self.xp,
            "items": self.items,
            "summoner_spells": self.summoner_spells,
            "keystone_rune": self.keystone_rune,
        }


@dataclass
class ParsedMinimap:
    player_pos: tuple[float, float] = (0.0, 0.0)
    allies: dict[str, tuple[float, float]] = field(default_factory=dict)
    enemies: dict[str, tuple[float, float]] = field(default_factory=dict)
    wards: list[tuple[float, float]] = field(default_factory=list)
    objectives: dict[str, tuple[float, float]] = field(default_factory=dict)


@dataclass
class ParsedChat:
    messages: list[dict] = field(default_factory=list)


DEFAULT_ROI_PRESETS = {
    "1920x1080": {
        "hud_hp": UIRoi("hud_hp", 15, 15, 180, 35),
        "hud_mana": UIRoi("hud_mana", 15, 50, 180, 25),
        "hud_level": UIRoi("hud_level", 15, 80, 60, 35),
        "hud_gold": UIRoi("hud_gold", 15, 120, 100, 30),
        "hud_cs": UIRoi("hud_cs", 15, 150, 80, 30),
        "hud_items": UIRoi("hud_items", 100, 1020, 480, 60),
        "hud_spells": UIRoi("hud_spells", 600, 1020, 120, 60),
        "minimap": UIRoi("minimap", 1600, 15, 300, 300),
        "chat": UIRoi("chat", 15, 700, 400, 300),
    },
    "2560x1440": {
        "hud_hp": UIRoi("hud_hp", 20, 20, 240, 45),
        "hud_mana": UIRoi("hud_mana", 20, 65, 240, 35),
        "hud_level": UIRoi("hud_level", 20, 105, 80, 45),
        "hud_gold": UIRoi("hud_gold", 20, 155, 130, 40),
        "hud_cs": UIRoi("hud_cs", 20, 195, 100, 40),
        "hud_items": UIRoi("hud_items", 130, 1360, 640, 80),
        "hud_spells": UIRoi("hud_spells", 800, 1360, 160, 80),
        "minimap": UIRoi("minimap", 2140, 20, 400, 400),
        "chat": UIRoi("chat", 20, 930, 530, 400),
    },
    "3840x2160": {
        "hud_hp": UIRoi("hud_hp", 30, 30, 360, 70),
        "hud_mana": UIRoi("hud_mana", 30, 100, 360, 50),
        "hud_level": UIRoi("hud_level", 30, 155, 120, 70),
        "hud_gold": UIRoi("hud_gold", 30, 230, 200, 60),
        "hud_cs": UIRoi("hud_cs", 30, 290, 150, 60),
        "hud_items": UIRoi("hud_items", 195, 2040, 960, 120),
        "hud_spells": UIRoi("hud_spells", 1200, 2040, 240, 120),
        "minimap": UIRoi("minimap", 3210, 30, 600, 600),
        "chat": UIRoi("chat", 30, 1400, 800, 600),
    },
}


def get_roi_preset(resolution: str) -> dict[str, UIRoi]:
    return DEFAULT_ROI_PRESETS.get(resolution, DEFAULT_ROI_PRESETS["1920x1080"])