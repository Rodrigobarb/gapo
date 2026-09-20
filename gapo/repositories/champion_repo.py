import json
from pathlib import Path
from typing import Optional
from gapo.core.logging import get_logger

logger = get_logger("champion_repo")


class ChampionRepository:
    def __init__(self, data_dir: Path = Path("data/champions")):
        self.data_dir = data_dir
        self._matchups: dict = {}
        self._builds: dict = {}
        self._counters: dict = {}
        self._powerspikes: dict = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return

        try:
            matchups_path = self.data_dir / "matchups.json"
            if matchups_path.exists():
                with open(matchups_path, "r", encoding="utf-8") as f:
                    self._matchups = json.load(f)

            builds_path = self.data_dir / "builds.json"
            if builds_path.exists():
                with open(builds_path, "r", encoding="utf-8") as f:
                    self._builds = json.load(f)

            counters_path = self.data_dir / "counters.json"
            if counters_path.exists():
                with open(counters_path, "r", encoding="utf-8") as f:
                    self._counters = json.load(f)

            powerspikes_path = self.data_dir / "powerspikes.json"
            if powerspikes_path.exists():
                with open(powerspikes_path, "r", encoding="utf-8") as f:
                    self._powerspikes = json.load(f)

            self._loaded = True
            logger.info("Champion knowledge base loaded")

        except Exception as e:
            logger.error(f"Failed to load champion data: {e}")

    def get_matchup(self, my_champ: str, enemy_champ: str, role: str = "") -> Optional[dict]:
        self.load()
        key = f"{my_champ.lower()}_vs_{enemy_champ.lower()}"
        if role:
            key = f"{role}_{key}"
        return self._matchups.get(key) or self._matchups.get(f"{my_champ.lower()}_vs_{enemy_champ.lower()}")

    def get_build(self, champion: str) -> Optional[dict]:
        self.load()
        return self._builds.get(champion.lower())

    def get_counters(self, champion: str) -> list[str]:
        self.load()
        data = self._counters.get(champion.lower())
        if isinstance(data, list):
            return data
        return []

    def get_powerspikes(self, champion: str) -> list[dict]:
        self.load()
        data = self._powerspikes.get(champion.lower())
        if isinstance(data, list):
            return data
        return []

    def search(self, query: str) -> list[dict]:
        self.load()
        query = query.lower()
        results = []
        for champ, data in self._matchups.items():
            if query in champ:
                results.append({"type": "matchup", "champion": champ, "data": data})
        for champ, data in self._builds.items():
            if query in champ:
                results.append({"type": "build", "champion": champ, "data": data})
        return results[:5]