import time
from typing import Callable, Optional

from gapo.core.logging import get_logger
from gapo.models.coach import CoachMode, CoachResponse
from gapo.models.game_state import GameState
from gapo.services.coach_service import CoachService

logger = get_logger("gapo_service")


class GapoService:
    def __init__(self, coach_service: CoachService):
        self.coach_service = coach_service
        self._cooldown = 10.0
        self._last_user_question: dict[int, float] = {}
        self._game_state_provider: Optional[Callable[[], GameState]] = None

    def set_cooldown(self, seconds: float) -> None:
        self._cooldown = seconds

    def set_game_state_provider(self, provider: Callable[[], GameState]) -> None:
        """Quem chama pelo Discord nao tem o GameState na mao; o controller sim."""
        self._game_state_provider = provider

    async def answer_question(
        self,
        user_id: int,
        username: str,
        question: str,
        channel_id: int,
        guild_id: int,
        game_state: Optional[GameState] = None,
    ) -> CoachResponse:
        current_time = time.time()
        last_time = self._last_user_question.get(user_id, 0)

        if current_time - last_time < self._cooldown:
            wait = int(self._cooldown - (current_time - last_time))
            return CoachResponse(
                text=f"Calma aí, {username}! Espere {wait}s antes de perguntar de novo.",
                mode=CoachMode.GAPO_CHAT,
            )

        self._last_user_question[user_id] = current_time
        return await self.coach_service.answer_question(
            question, game_state or self._current_state()
        )

    def _current_state(self) -> GameState:
        """Estado atual da partida, ou um vazio quando nao ha captura rodando."""
        if self._game_state_provider is None:
            return GameState()
        return self._game_state_provider()