from gapo.repositories.champion_repo import ChampionRepository
from gapo.models.game_state import GameState
from gapo.core.logging import get_logger

logger = get_logger("knowledge_service")


class KnowledgeService:
    def __init__(self, champion_repo: ChampionRepository):
        self.champion_repo = champion_repo

    def get_context_for_champion(self, champion: str) -> dict:
        build = self.champion_repo.get_build(champion)
        counters = self.champion_repo.get_counters(champion)
        powerspikes = self.champion_repo.get_powerspikes(champion)

        return {
            "build": build,
            "counters": counters[:5],
            "powerspikes": powerspikes[:5],
        }

    def get_matchup_advice(self, my_champ: str, enemy_champ: str, role: str = "") -> str | None:
        matchup = self.champion_repo.get_matchup(my_champ, enemy_champ, role)
        if matchup:
            return matchup.get("advice")
        return None

    def search_knowledge(self, query: str) -> list[dict]:
        return self.champion_repo.search(query)