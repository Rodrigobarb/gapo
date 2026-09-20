import yaml
from pathlib import Path
from typing import Optional
from gapo.models.coach import CoachPrompt, CoachMode
from gapo.core.logging import get_logger

logger = get_logger("prompt_repo")


class PromptRepository:
    def __init__(self, prompts_dir: Path = Path("data/prompts")):
        self.prompts_dir = prompts_dir
        self._cache: dict[str, CoachPrompt] = {}

    def load_event_prompt(self, version: str = "v1") -> CoachPrompt:
        key = f"event_{version}"
        if key in self._cache:
            return self._cache[key]

        path = self.prompts_dir / f"event_coach_{version}.yaml"
        if not path.exists():
            logger.warning(f"Prompt file not found: {path}, using defaults")
            return self._default_event_prompt()

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        prompt = CoachPrompt(
            mode=CoachMode.EVENT_DRIVEN,
            system_prompt=data.get("system_prompt", ""),
            user_prompt=data.get("user_prompt_template", ""),
            few_shot_examples=data.get("few_shot_examples", []),
            max_tokens=data.get("max_tokens", 100),
            temperature=data.get("temperature", 0.3),
        )
        self._cache[key] = prompt
        return prompt

    def load_gapo_prompt(self, version: str = "v1") -> CoachPrompt:
        key = f"gapo_{version}"
        if key in self._cache:
            return self._cache[key]

        path = self.prompts_dir / f"gapo_coach_{version}.yaml"
        if not path.exists():
            logger.warning(f"Prompt file not found: {path}, using defaults")
            return self._default_gapo_prompt()

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        prompt = CoachPrompt(
            mode=CoachMode.GAPO_CHAT,
            system_prompt=data.get("system_prompt", ""),
            user_prompt=data.get("user_prompt_template", ""),
            few_shot_examples=data.get("few_shot_examples", []),
            max_tokens=data.get("max_tokens", 200),
            temperature=data.get("temperature", 0.4),
        )
        self._cache[key] = prompt
        return prompt

    def _default_event_prompt(self) -> CoachPrompt:
        from gapo.models.coach import EVENT_COACH_SYSTEM_PROMPT, EVENT_FEW_SHOT_EXAMPLES
        return CoachPrompt(
            mode=CoachMode.EVENT_DRIVEN,
            system_prompt=EVENT_COACH_SYSTEM_PROMPT,
            user_prompt="{event_message}\nContexto: {game_state}",
            few_shot_examples=EVENT_FEW_SHOT_EXAMPLES,
        )

    def _default_gapo_prompt(self) -> CoachPrompt:
        from gapo.models.coach import GAPO_CHAT_SYSTEM_PROMPT, GAPO_FEW_SHOT_EXAMPLES
        return CoachPrompt(
            mode=CoachMode.GAPO_CHAT,
            system_prompt=GAPO_CHAT_SYSTEM_PROMPT,
            user_prompt="Pergunta: {question}\nContexto: {game_state}",
            few_shot_examples=GAPO_FEW_SHOT_EXAMPLES,
        )

    def reload(self) -> None:
        self._cache.clear()