from gapo.models.game_state import GameState, GameStateHistory, PlayerState, MinimapState
from gapo.models.ocr import ParsedHUD, ParsedMinimap, ParsedChat
from gapo.core.logging import get_logger
from gapo.core.metrics import game_state_updates

logger = get_logger("game_state_service")


class GameStateService:
    def __init__(self, history_seconds: int = 30):
        self.current_state = GameState()
        self.history = GameStateHistory(max_seconds=history_seconds)
        self._last_hud: ParsedHUD | None = None
        self._last_minimap: ParsedMinimap | None = None
        self._last_chat: ParsedChat | None = None

    def update_from_ocr(self, hud: ParsedHUD, minimap: ParsedMinimap, chat: ParsedChat) -> GameState:
        self._last_hud = hud
        self._last_minimap = minimap
        self._last_chat = chat

        self.current_state.player.hp = hud.hp or self.current_state.player.hp
        self.current_state.player.max_hp = hud.max_hp or self.current_state.player.max_hp
        self.current_state.player.mana = hud.mana or self.current_state.player.mana
        self.current_state.player.max_mana = hud.max_mana or self.current_state.player.max_mana
        self.current_state.player.level = hud.level or self.current_state.player.level
        self.current_state.player.gold = hud.gold or self.current_state.player.gold
        self.current_state.player.cs = hud.cs or self.current_state.player.cs
        self.current_state.player.items = hud.items or self.current_state.player.items
        self.current_state.player.summoner_spells = hud.summoner_spells or self.current_state.player.summoner_spells
        self.current_state.player.keystone_rune = hud.keystone_rune or self.current_state.player.keystone_rune

        self.current_state.minimap = MinimapState(
            player_position=minimap.player_pos,
            allies=minimap.allies,
            enemies=minimap.enemies,
            wards=minimap.wards,
            objectives=minimap.objectives,
        )

        self.current_state.chat_messages = chat.messages
        self.current_state.timestamp = self.current_state.timestamp.__class__.now()

        self.history.add(self.current_state)
        game_state_updates.inc()

        return self.current_state

    def get_current_state(self) -> GameState:
        return self.current_state

    def get_history(self) -> GameStateHistory:
        return self.history

    def get_context_for_coach(self) -> dict:
        return self.current_state.to_context_dict()

    def update_player_champion(self, champion: str) -> None:
        self.current_state.player.champion = champion

    def update_phase(self, phase: str) -> None:
        self.current_state.phase = phase

    def update_game_time(self, seconds: float) -> None:
        self.current_state.game_time_seconds = seconds