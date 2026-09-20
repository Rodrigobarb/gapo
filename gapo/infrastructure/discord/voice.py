import asyncio
import io
from typing import Optional

import discord

from gapo.core.logging import get_logger
from gapo.models.audio import AudioChunk, AudioFormat

logger = get_logger("discord_voice")


class DiscordVoiceManager:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self._voice_client: Optional[discord.VoiceClient] = None
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
                source = self._build_source(chunk)
                if source is None:
                    continue

                # Espera a fala anterior terminar em vez de descartar esta.
                while self._voice_client.is_playing():
                    await asyncio.sleep(0.01)

                self._voice_client.play(source)
                while self._voice_client.is_playing():
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Playback error: {e}")
        self._playing = False

    def _build_source(self, chunk: AudioChunk) -> Optional[discord.AudioSource]:
        """Converte o chunk do TTS no que o Discord aceita.

        O Piper entrega WAV mono 22kHz e o Discord exige PCM 48kHz estereo, por
        isso o ffmpeg (pre-requisito do projeto) faz a reamostragem.
        """
        if chunk.format is AudioFormat.OPUS:
            return _OpusAudio(chunk.data)
        if chunk.format is AudioFormat.WAV:
            try:
                return discord.FFmpegPCMAudio(io.BytesIO(chunk.data), pipe=True)
            except Exception as e:
                logger.error(f"ffmpeg indisponivel para tocar o TTS: {e}")
                return None
        logger.warning(f"Formato de audio nao suportado na voz: {chunk.format}")
        return None

    async def stop_playback(self) -> None:
        if self._voice_client and self._voice_client.is_playing():
            self._voice_client.stop()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break


class _OpusAudio(discord.AudioSource):
    """Chunk ja codificado em Opus: o Discord consome os frames direto."""

    FRAME_BYTES = 3840  # 20ms @ 48kHz estereo 16-bit

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read(self) -> bytes:
        frame = self.data[self.pos : self.pos + self.FRAME_BYTES]
        self.pos += self.FRAME_BYTES
        return frame

    def is_opus(self) -> bool:
        return True
