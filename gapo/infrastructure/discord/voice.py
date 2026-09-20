import discord
import asyncio
from typing import Optional
from gapo.core.logging import get_logger
from gapo.utils.audio import _load_opuslib
from gapo.models.audio import AudioChunk, AudioFormat

logger = get_logger("discord_voice")


class DiscordVoiceManager:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self._voice_client: Optional[discord.VoiceClient] = None
        opuslib = _load_opuslib()
        self._encoder = opuslib.Encoder(48000, 1, opuslib.APPLICATION_AUDIO)
        self._frame_size = 960
        self._playing = False
        self._queue: asyncio.Queue = asyncio.Queue()

    async def connect(self, channel: discord.VoiceChannel) -> bool:
        try:
            if self._voice_client and self._voice_client.is_connected():
                await self._voice_client.move_to(channel)
            else:
                self._voice_client = await channel.connect()
            logger.info(f"Voice connected to {channel.name}")
            return True
        except Exception as e:
            logger.error(f"Voice connect failed: {e}")
            return False

    async def disconnect(self) -> None:
        if self._voice_client and self._voice_client.is_connected():
            await self._voice_client.disconnect()
            self._voice_client = None
            logger.info("Voice disconnected")

    def is_connected(self) -> bool:
        return self._voice_client is not None and self._voice_client.is_connected()

    async def play_audio(self, chunk: AudioChunk) -> None:
        await self._queue.put(chunk)
        if not self._playing:
            asyncio.create_task(self._playback_loop())

    async def _playback_loop(self) -> None:
        self._playing = True
        while not self._queue.empty():
            if not self.is_connected():
                break
            try:
                chunk = await self._queue.get()
                if chunk.format != AudioFormat.OPUS:
                    logger.warning("Only OPUS format supported for direct playback")
                    continue
                
                if self._voice_client.is_playing():
                    await asyncio.sleep(0.01)
                    continue

                class OpusAudio(discord.AudioSource):
                    def __init__(self, data: bytes):
                        self.data = data
                        self.pos = 0

                    def read(self) -> bytes:
                        chunk = self.data[self.pos:self.pos + 3840]
                        self.pos += 3840
                        return chunk if chunk else b""

                    def is_opus(self) -> bool:
                        return True

                source = OpusAudio(chunk.data)
                self._voice_client.play(source)
                while self._voice_client.is_playing():
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Playback error: {e}")
        self._playing = False

    async def stop_playback(self) -> None:
        if self._voice_client and self._voice_client.is_playing():
            self._voice_client.stop()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break