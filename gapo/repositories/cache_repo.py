from gapo.utils.async_utils import AsyncCache
from gapo.core.logging import get_logger

logger = get_logger("cache_repo")


class CacheRepository:
    def __init__(self, ttl_seconds: float = 300, max_size: int = 1000):
        self._cache = AsyncCache(ttl_seconds, max_size)

    async def get_llm_response(self, prompt_hash: str) -> str | None:
        return await self._cache.get(f"llm:{prompt_hash}")

    async def set_llm_response(self, prompt_hash: str, response: str) -> None:
        await self._cache.set(f"llm:{prompt_hash}", response)

    async def get_ocr_result(self, roi_name: str, image_hash: str) -> dict | None:
        return await self._cache.get(f"ocr:{roi_name}:{image_hash}")

    async def set_ocr_result(self, roi_name: str, image_hash: str, result: dict) -> None:
        await self._cache.set(f"ocr:{roi_name}:{image_hash}", result)

    async def get_tts_audio(self, text_hash: str) -> bytes | None:
        return await self._cache.get(f"tts:{text_hash}")

    async def set_tts_audio(self, text_hash: str, audio: bytes) -> None:
        await self._cache.set(f"tts:{text_hash}", audio)

    async def clear(self) -> None:
        await self._cache.clear()