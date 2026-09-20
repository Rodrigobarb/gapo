import asyncio
import time
from gapo.infrastructure.ollama import OllamaClient, PromptBuilder
from gapo.models.coach import CoachPrompt, CoachResponse, CoachMode, build_event_prompt, build_gapo_prompt
from gapo.models.game_state import GameState
from gapo.models.events import GameEvent
from gapo.core.logging import get_logger
from gapo.core.metrics import llm_requests_total, llm_latency_seconds
from gapo.repositories.cache_repo import CacheRepository

logger = get_logger("coach_service")


class CoachService:
    def __init__(
        self,
        ollama_client: OllamaClient,
        prompt_builder: PromptBuilder,
        cache_repo: CacheRepository,
    ):
        self.ollama = ollama_client
        self.prompt_builder = prompt_builder
        self.cache = cache_repo
        self._event_cooldown = 5.0
        self._last_event_time = 0.0
        self._enabled = True

    def set_event_cooldown(self, seconds: float) -> None:
        self._event_cooldown = seconds

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    async def process_event(self, event: GameEvent, game_state: GameState) -> CoachResponse | None:
        if not self._enabled:
            return None

        current_time = time.time()
        if current_time - self._last_event_time < self._event_cooldown:
            return None

        prompt = self.prompt_builder.build_event_prompt(
            event.event_type.value,
            event.message,
            game_state,
        )

        response = await self._generate_with_cache(prompt)
        if response:
            self._last_event_time = current_time
            logger.info(f"Event coach response: {response.text[:100]}...")

        return response

    async def answer_question(self, question: str, game_state: GameState) -> CoachResponse:
        prompt = self.prompt_builder.build_gapo_prompt(question, game_state)
        response = await self._generate_with_cache(prompt)
        logger.info(f"Gapo Q&A response: {response.text[:100]}...")
        return response

    async def _generate_with_cache(self, prompt: CoachPrompt) -> CoachResponse:
        cache_key = f"{prompt.mode.value}:{hash(prompt.user_prompt)}"
        cached = await self.cache.get_llm_response(cache_key)
        if cached:
            logger.debug("Using cached LLM response")
            return CoachResponse(
                text=cached,
                mode=prompt.mode,
                latency_ms=0,
            )

        response = await self.ollama.generate(prompt)

        if response.text and len(response.text) > 10:
            await self.cache.set_llm_response(cache_key, response.text)

        return response