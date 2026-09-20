"""Runtime do bot: monta os services e toca o loop de captura/Discord.

Os comandos da CLI vivem em gapo/cli.py; aqui so entra o que precisa do
runtime completo carregado.
"""

import asyncio
import subprocess
import time
from collections import deque

import click
import discord

from gapo.config.settings import get_settings
from gapo.core.logging import setup_logging, get_logger
from gapo.services.model_service import ModelService
from gapo.services.capture_service import CaptureService
from gapo.services.ocr_service import OCRService
from gapo.services.game_state_service import GameStateService
from gapo.services.event_service import EventService
from gapo.services.coach_service import CoachService
from gapo.services.gapo_service import GapoService
from gapo.services.tts_service import TTSService
from gapo.services.knowledge_service import KnowledgeService
from gapo.repositories.prompt_repo import PromptRepository
from gapo.repositories.champion_repo import ChampionRepository
from gapo.repositories.roi_repo import ROIRepository
from gapo.repositories.cache_repo import CacheRepository
from gapo.infrastructure.discord import DiscordBot, create_bot, setup_commands, GapoMessageListener, DiscordVoiceManager
from gapo.infrastructure.ollama import PromptBuilder

logger = get_logger("cli")


class CLIController:
    def __init__(self):
        self.settings = get_settings()
        self.model_service = ModelService()
        self.capture_service = CaptureService()
        self.ocr_service = None
        self.game_state_service = GameStateService()
        self.event_service = EventService()
        self.coach_service = None
        self.gapo_service = None
        self.tts_service = None
        self.knowledge_service = None
        self.discord_bot = None
        self.voice_manager = None
        self._running = False
        self._event_times: deque[float] = deque()

    async def initialize(self) -> bool:
        setup_logging()
        logger.info("Initializing Gapo...")

        if not await self.model_service.initialize():
            logger.error("Failed to initialize models")
            return False

        self.ocr_service = OCRService(ROIRepository())
        self.ocr_service.set_yolo(self.model_service.get_yolo_detector())
        self.ocr_service.set_resolution(
            self.settings.capture.resolution_width,
            self.settings.capture.resolution_height,
        )

        prompt_repo = PromptRepository()
        champion_repo = ChampionRepository()
        cache_repo = CacheRepository()

        self.coach_service = CoachService(
            self.model_service.get_ollama_client(),
            PromptBuilder(prompt_repo, champion_repo),
            cache_repo,
        )
        self.coach_service.set_event_cooldown(self.settings.coach.event_cooldown_seconds)

        self.gapo_service = GapoService(self.coach_service)
        self.gapo_service.set_cooldown(self.settings.coach.gapo_cooldown_seconds)
        self.gapo_service.set_game_state_provider(self.game_state_service.get_current_state)

        self.tts_service = TTSService(
            self.model_service.get_piper_engine(),
            self.model_service.get_voice_manager(),
            cache_repo,
        )

        self.knowledge_service = KnowledgeService(champion_repo)

        self.capture_service.set_frame_callback(self._on_frame)

        return True

    async def _on_frame(self, frame) -> None:
        if self.ocr_service:
            ocr_results = await self.ocr_service.process_frame(frame)

            hud_results = []
            minimap_results = []
            chat_results = []

            for name, results in ocr_results.items():
                if "hud" in name:
                    hud_results.extend(results)
                elif "minimap" in name:
                    minimap_results.extend(results)
                elif "chat" in name:
                    chat_results.extend(results)

            if hud_results:
                hud = self.ocr_service.parse_hud(hud_results)
            else:
                from gapo.models.ocr import ParsedHUD
                hud = ParsedHUD()

            if minimap_results:
                minimap = self.ocr_service.parse_minimap(minimap_results)
            else:
                from gapo.models.ocr import ParsedMinimap
                minimap = ParsedMinimap()

            if chat_results:
                chat = self.ocr_service.parse_chat(chat_results)
            else:
                from gapo.models.ocr import ParsedChat
                chat = ParsedChat()

            game_state = self.game_state_service.update_from_ocr(hud, minimap, chat)

            if self.settings.coach.enable_event_coach:
                events = self.event_service.check_events(game_state)
                for event in events:
                    self._event_times.append(time.monotonic())
                    response = await self.coach_service.process_event(event, game_state)
                    if response and self.tts_service:
                        await self.tts_service.speak(response.clean_for_tts(), priority=10)

    async def start_discord(self) -> bool:
        if not self.settings.discord.token:
            logger.error("Discord token not configured")
            return False

        self.discord_bot = await create_bot(
            self.settings.discord.token,
            self.settings.discord.application_id or 0,
            guild_id=self.settings.discord.guild_id,
        )

        self.voice_manager = DiscordVoiceManager(self.discord_bot)

        # O TTSService faz `await self._play_chunk(chunk)`, entao o callback
        # precisa ser awaitable - um def comum aqui explodia em TypeError.
        async def tts_playback(chunk):
            if self.voice_manager and self.voice_manager.is_connected():
                await self.voice_manager.play_audio(chunk)

        self.tts_service.set_playback_callback(tts_playback)

        setup_commands(self.discord_bot, self)

        async def falar_resposta(response):
            if self.tts_service:
                # Prioridade acima do coach automatico: pergunta direta vem antes.
                await self.tts_service.speak(response.clean_for_tts(), priority=20)

        listener = GapoMessageListener(
            self.discord_bot, self.gapo_service, on_answer=falar_resposta
        )
        listener.register()

        if self.settings.discord.voice_channel_id:
            asyncio.create_task(self._autojoin_voice())

        try:
            await self.discord_bot.start(self.settings.discord.token)
        except Exception as e:
            logger.error(f"Discord bot error: {e}")
            return False

        return True

    async def _autojoin_voice(self) -> None:
        """Entra sozinho no canal fixado em DISCORD_VOICE_CHANNEL_ID, se houver."""
        await self.discord_bot.wait_until_ready()
        channel_id = self.settings.discord.voice_channel_id
        if await self.start_coaching(channel_id):
            logger.info(f"Auto-join no canal de voz {channel_id}")
        else:
            logger.warning(f"Auto-join falhou no canal {channel_id} - use /coach_start")

    async def start_coaching(self, voice_channel_id: int) -> bool:
        """Entra no canal de voz e liga a captura. Alvo do /coach_start."""
        if not self.voice_manager or not self.discord_bot:
            logger.error("Bot do Discord ainda nao inicializado")
            return False

        channel = self.discord_bot.get_channel(voice_channel_id)
        if not isinstance(channel, discord.VoiceChannel):
            logger.error(f"Canal {voice_channel_id} nao existe ou nao e canal de voz")
            return False

        if not await self.voice_manager.connect(channel):
            return False

        if not await self.capture_service.start():
            logger.error("Captura falhou - saindo do canal de voz")
            await self.voice_manager.disconnect()
            return False

        self._running = True
        return True

    async def stop_coaching(self) -> None:
        """Para a captura e sai do canal de voz. Alvo do /coach_stop."""
        self._running = False
        await self.capture_service.stop()
        if self.voice_manager:
            await self.voice_manager.disconnect()

    async def get_status(self) -> dict:
        """Snapshot para o /coach_status."""
        capture = self.capture_service.get_status()
        health = await self.model_service.health_check()
        return {
            "capturing": capture["capturing"],
            "fps": capture["fps"],
            "voice_connected": bool(self.voice_manager and self.voice_manager.is_connected()),
            "events_per_min": self._events_per_minute(),
            "vram_used_mb": _vram_used_mb(),
            "llm_status": "online" if health["ollama"] else "offline",
        }

    def set_event_cooldown(self, seconds: float) -> None:
        if self.coach_service:
            self.coach_service.set_event_cooldown(seconds)

    def set_gapo_cooldown(self, seconds: float) -> None:
        if self.gapo_service:
            self.gapo_service.set_cooldown(seconds)

    def _events_per_minute(self) -> int:
        agora = time.monotonic()
        while self._event_times and agora - self._event_times[0] > 60.0:
            self._event_times.popleft()
        return len(self._event_times)

    async def run_capture_only(self) -> None:
        logger.info("Starting capture only mode...")
        await self.capture_service.start()
        try:
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await self.capture_service.stop()

    async def shutdown(self) -> None:
        logger.info("Shutting down...")
        await self.capture_service.stop()
        if self.discord_bot:
            await self.discord_bot.close()


async def run_bot():
    controller = CLIController()
    if await controller.initialize():
        controller._running = True
        await controller.start_discord()
    else:
        click.echo("❌ Falha na inicializacao - rode `gapo doctor` para ver o que falta")
        raise SystemExit(1)


async def run_capture():
    controller = CLIController()
    if await controller.initialize():
        controller._running = True
        await controller.run_capture_only()
    else:
        click.echo("❌ Falha na inicializacao - rode `gapo doctor` para ver o que falta")
        raise SystemExit(1)


def _vram_used_mb() -> float:
    """VRAM em uso segundo o nvidia-smi; 0.0 quando nao ha GPU NVIDIA."""
    try:
        resultado = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return 0.0
    if resultado.returncode != 0:
        return 0.0
    try:
        return max(float(linha) for linha in resultado.stdout.split() if linha.strip())
    except ValueError:
        return 0.0
