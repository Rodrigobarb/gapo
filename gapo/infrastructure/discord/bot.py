import discord
from discord.ext import commands
import asyncio
from typing import Optional
from gapo.core.logging import get_logger
from gapo.models.audio import OpusPacket

logger = get_logger("discord_bot")


class DiscordBot(commands.Bot):
    def __init__(self, token: str, application_id: int, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=application_id,
            **kwargs
        )
        self.token = token
        self._voice_client: Optional[discord.VoiceClient] = None
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._playing = False

    async def setup_hook(self):
        logger.info("Setting up Discord bot...")
        await self.tree.sync()
        logger.info("Slash commands synced")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")

    async def join_voice_channel(self, channel_id: int) -> bool:
        channel = self.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            logger.error(f"Voice channel {channel_id} not found")
            return False

        try:
            if self._voice_client and self._voice_client.is_connected():
                await self._voice_client.move_to(channel)
            else:
                self._voice_client = await channel.connect()
            logger.info(f"Connected to voice channel: {channel.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to join voice channel: {e}")
            return False

    async def leave_voice_channel(self) -> None:
        if self._voice_client and self._voice_client.is_connected():
            await self._voice_client.disconnect()
            self._voice_client = None
            logger.info("Disconnected from voice channel")

    def is_voice_connected(self) -> bool:
        return self._voice_client is not None and self._voice_client.is_connected()

    async def queue_audio(self, opus_data: bytes) -> None:
        await self._audio_queue.put(opus_data)
        if not self._playing:
            asyncio.create_task(self._play_audio_loop())

    async def _play_audio_loop(self) -> None:
        self._playing = True
        while not self._audio_queue.empty():
            if not self._voice_client or not self._voice_client.is_connected():
                break
            try:
                opus_data = await self._audio_queue.get()
                if self._voice_client.is_playing():
                    await asyncio.sleep(0.02)
                    continue
                audio_source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(
                        pipe=True,
                        input=opus_data,
                        before_options="-f s16le -ar 48000 -ac 1",
                    )
                )
                self._voice_client.play(audio_source)
                while self._voice_client.is_playing():
                    await asyncio.sleep(0.02)
            except Exception as e:
                logger.error(f"Error playing audio: {e}")
        self._playing = False

    async def close(self):
        await self.leave_voice_channel()
        await super().close()


async def create_bot(token: str, application_id: int) -> DiscordBot:
    bot = DiscordBot(token, application_id)
    return bot