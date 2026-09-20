import asyncio
import uuid
from gapo.infrastructure.piper import PiperEngine, VoiceManager
from gapo.models.audio import TTSRequest, VoiceConfig, AudioChunk, AudioFormat
from gapo.core.logging import get_logger
from gapo.core.metrics import tts_requests_total, tts_latency_seconds
from gapo.repositories.cache_repo import CacheRepository
import time

logger = get_logger("tts_service")


class TTSService:
    def __init__(
        self,
        piper_engine: PiperEngine,
        voice_manager: VoiceManager,
        cache_repo: CacheRepository,
    ):
        self.engine = piper_engine
        self.voice_manager = voice_manager
        self.cache = cache_repo
        self._queue: asyncio.Queue = asyncio.Queue()
        self._playing = False
        self._current_request_id = ""
        self._priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()

    async def speak(self, text: str, voice_config: VoiceConfig | None = None, priority: int = 0) -> str:
        request_id = str(uuid.uuid4())[:8]
        config = voice_config or self.voice_manager.default_config

        request = TTSRequest(
            text=text,
            voice_config=config,
            priority=priority,
            request_id=request_id,
        )

        await self._priority_queue.put((priority, request))
        if not self._playing:
            asyncio.create_task(self._process_queue())

        return request_id

    async def _process_queue(self) -> None:
        self._playing = True
        while not self._priority_queue.empty():
            try:
                _, request = await self._priority_queue.get()
                self._current_request_id = request.request_id
                await self._synthesize_and_play(request)
            except Exception as e:
                logger.error(f"TTS queue processing error: {e}")
        self._playing = False
        self._current_request_id = ""

    async def _synthesize_and_play(self, request: TTSRequest) -> None:
        cache_key = f"tts:{hash(request.clean_text())}:{request.voice_config.model}"
        cached_audio = await self.cache.get_tts_audio(cache_key)

        if cached_audio:
            chunk = AudioChunk(
                data=cached_audio,
                format=AudioFormat.WAV,
                sample_rate=request.voice_config.sample_rate,
                channels=1,
                frame_count=len(cached_audio) // 2,
                is_final=True,
                request_id=request.request_id,
            )
            await self._play_chunk(chunk)
            return

        try:
            async for chunk in self.engine.synthesize(request):
                if chunk.is_final:
                    await self.cache.set_tts_audio(cache_key, chunk.data)
                await self._play_chunk(chunk)
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")

    async def _play_chunk(self, chunk: AudioChunk) -> None:
        pass

    def set_playback_callback(self, callback) -> None:
        self._play_chunk = callback

    def stop_current(self) -> None:
        while not self._priority_queue.empty():
            try:
                self._priority_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def is_playing(self) -> bool:
        return self._playing

    def get_current_request_id(self) -> str:
        return self._current_request_id