import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_game_state():
    from gapo.models.game_state import GameState, PlayerState
    state = GameState()
    state.player.champion = "Zed"
    state.player.level = 6
    state.player.hp = 1200
    state.player.max_hp = 1800
    state.player.mana = 200
    state.player.max_mana = 200
    state.player.gold = 5000
    state.player.cs = 140
    state.player.items = ["youmuu", "divine sunderer", "ionian boots"]
    state.player.summoner_spells = ["flash", "ignite"]
    state.player.keystone_rune = "electrocute"
    state.game_time_seconds = 720.0
    state.phase = "mid_game"
    return state


@pytest.fixture
def sample_event():
    from gapo.models.events import GameEvent, EventType, EventPriority
    return GameEvent(
        event_type=EventType.GANK_IMMINENT,
        priority=EventPriority.HIGH,
        message="Enemy Zed missing for 12s, possible gank bot",
        context={"enemy_champion": "Zed", "missing_time": 12},
    )