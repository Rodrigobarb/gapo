import pytest
from gapo.models.game_state import GameState, PlayerState, GameStateHistory
from gapo.models.events import GameEvent, EventType, EventPriority
from gapo.models.ocr import ParsedHUD, UIRoi
from gapo.models.coach import build_event_prompt, build_gapo_prompt, CoachMode


class TestGameState:
    def test_game_state_creation(self):
        state = GameState()
        assert state.phase == "loading"
        assert state.player.level == 1

    def test_game_state_history(self):
        history = GameStateHistory(max_seconds=10)
        state = GameState()
        history.add(state)
        assert history.get_latest() is not None

    def test_context_dict(self):
        state = GameState()
        state.player.champion = "Zed"
        state.player.level = 6
        state.player.hp = 1000
        state.player.max_hp = 1500
        state.game_time_seconds = 420.0

        ctx = state.to_context_dict()
        assert ctx["player"]["champion"] == "Zed"
        assert ctx["player"]["level"] == 6
        assert ctx["player"]["hp_pct"] == 66.7


class TestEvents:
    def test_game_event_creation(self):
        event = GameEvent(
            event_type=EventType.GANK_IMMINENT,
            priority=EventPriority.HIGH,
            message="Test gank",
        )
        assert event.event_type == EventType.GANK_IMMINENT
        assert event.priority == EventPriority.HIGH

    def test_event_to_prompt(self):
        event = GameEvent(
            event_type=EventType.OBJECTIVE_CONTESTED,
            priority=EventPriority.CRITICAL,
            message="Dragon spawning",
            context={"timer": 5},
        )
        prompt = event.to_coach_prompt()
        # to_coach_prompt() serializa o .value do enum (minusculo), igual aos
        # few-shot examples em gapo/models/coach.py
        assert "objective_contested" in prompt
        assert "critical" in prompt
        assert "Dragon spawning" in prompt


class TestOCR:
    def test_roi_creation(self):
        roi = UIRoi(name="test", x=10, y=20, width=100, height=50)
        assert roi.to_tuple() == (10, 20, 110, 70)

    def test_parsed_hud(self):
        hud = ParsedHUD(hp=1000, max_hp=1500, level=6, gold=3000, cs=120)
        assert hud.hp == 1000
        assert hud.level == 6


class TestCoachPrompts:
    def test_build_event_prompt(self):
        game_state = {
            "player": {"champion": "Zed", "level": 6},
            "enemies_visible": {"Syndra": {}},
        }
        prompt = build_event_prompt("gank_imminent", "Enemy missing", game_state)
        assert prompt.mode == CoachMode.EVENT_DRIVEN
        assert "Zed" in prompt.user_prompt
        assert len(prompt.few_shot_examples) > 0

    def test_build_gapo_prompt(self):
        game_state = {"player": {"champion": "Ahri", "level": 6}}
        prompt = build_gapo_prompt("qual a melhor jogada?", game_state)
        assert prompt.mode == CoachMode.GAPO_CHAT
        assert "Ahri" in prompt.user_prompt
        assert len(prompt.few_shot_examples) > 0