from gapo.models.coach import CoachPrompt, CoachMode
from gapo.models.game_state import GameState
from gapo.repositories.champion_repo import ChampionRepository
from gapo.repositories.prompt_repo import PromptRepository
from gapo.core.logging import get_logger

logger = get_logger("prompt_builder")


class PromptBuilder:
    def __init__(
        self,
        prompt_repo: PromptRepository,
        champion_repo: ChampionRepository,
    ):
        self.prompt_repo = prompt_repo
        self.champion_repo = champion_repo

    def build_event_prompt(self, event_type: str, message: str, game_state: GameState) -> CoachPrompt:
        base_prompt = self.prompt_repo.load_event_prompt()
        context = game_state.to_context_dict()
        
        champion = context.get("player", {}).get("champion", "")
        enemy_champ = ""
        if context.get("enemies_visible"):
            enemy_champ = list(context["enemies_visible"].keys())[0]

        if champion and enemy_champ:
            matchup = self.champion_repo.get_matchup(champion, enemy_champ)
            if matchup:
                context["matchup_advice"] = matchup.get("advice", "")

        user_prompt = base_prompt.user_prompt.format(
            event_message=f"Evento: {event_type}\nDetalhes: {message}",
            game_state=context,
        )

        return CoachPrompt(
            mode=CoachMode.EVENT_DRIVEN,
            system_prompt=base_prompt.system_prompt,
            user_prompt=user_prompt,
            context=context,
            few_shot_examples=base_prompt.few_shot_examples,
            max_tokens=base_prompt.max_tokens,
            temperature=base_prompt.temperature,
        )

    def build_gapo_prompt(self, question: str, game_state: GameState) -> CoachPrompt:
        base_prompt = self.prompt_repo.load_gapo_prompt()
        context = game_state.to_context_dict()

        champion = context.get("player", {}).get("champion", "")
        if champion:
            build = self.champion_repo.get_build(champion)
            counters = self.champion_repo.get_counters(champion)
            powerspikes = self.champion_repo.get_powerspikes(champion)
            if build:
                context["recommended_build"] = build
            if counters:
                context["counters"] = counters[:3]
            if powerspikes:
                context["powerspikes"] = powerspikes[:3]

        user_prompt = base_prompt.user_prompt.format(
            question=question,
            game_state=context,
        )

        return CoachPrompt(
            mode=CoachMode.GAPO_CHAT,
            system_prompt=base_prompt.system_prompt,
            user_prompt=user_prompt,
            context=context,
            few_shot_examples=base_prompt.few_shot_examples,
            max_tokens=base_prompt.max_tokens,
            temperature=base_prompt.temperature,
        )