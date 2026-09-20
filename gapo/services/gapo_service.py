from gapo.services.coach_service import CoachService
from gapo.models.game_state import GameState
from gapo.models.coach import CoachResponse
from gapo.core.logging import get_logger

logger = get_logger("gapo_service")


class GapoService:
    def __init__(self, coach_service: CoachService):
        self.coach_service = coach_service
        self._cooldown = 10.0
        self._last_user_question: dict[int, float] = {}

    def set_cooldown(self, seconds: float) -> None:
        self._cooldown = seconds

    async def answer_question(
        self,
        user_id: int,
        username: str,
        question: str,
        channel_id: int,
        guild_id: int,
        game_state: GameState,
    ) -> CoachResponse:
        import time
        current_time = time.time()
        last_time = self._last_user_question.get(user_id, 0)

        if current_time - last_time < self._cooldown:
            wait = int(self._cooldown - (current_time - last_time))
            return CoachResponse(
                text=f"Calma aí, {username}! Espere {wait}s antes de perguntar de novo.",
                mode=None,
            )

        self._last_user_question[user_id] = current_time
        return await self.coach_service.answer_question(question, game_state)