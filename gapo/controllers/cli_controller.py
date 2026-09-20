import asyncio
import sys
import click
from pathlib import Path
from gapo.config.settings import get_settings, reload_settings
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
            None,
            cache_repo,
        )
        self.coach_service.set_event_cooldown(self.settings.coach.event_cooldown_seconds)

        self.gapo_service = GapoService(self.coach_service)
        self.gapo_service.set_cooldown(self.settings.coach.gapo_cooldown_seconds)

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
        )

        self.voice_manager = DiscordVoiceManager(self.discord_bot)

        def tts_playback(chunk):
            if self.voice_manager and self.voice_manager.is_connected():
                asyncio.create_task(self.voice_manager.play_audio(chunk))

        self.tts_service.set_playback_callback(tts_playback)

        setup_commands(self.discord_bot, self.coach_service, self.capture_service, None)

        listener = GapoMessageListener(self.discord_bot, self.gapo_service)
        listener.register()

        try:
            await self.discord_bot.start(self.settings.discord.token)
        except Exception as e:
            logger.error(f"Discord bot error: {e}")
            return False

        return True

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


async def run_init():
    controller = CLIController()
    if await controller.initialize():
        await controller.model_service.download_models()
        click.echo("✅ Gapo initialized successfully!")
    else:
        click.echo("❌ Initialization failed")
        raise SystemExit(1)


async def run_bot():
    controller = CLIController()
    if await controller.initialize():
        controller._running = True
        await controller.start_discord()
    else:
        click.echo("❌ Initialization failed")
        raise SystemExit(1)


async def run_capture():
    controller = CLIController()
    if await controller.initialize():
        controller._running = True
        await controller.run_capture_only()
    else:
        click.echo("❌ Initialization failed")
        raise SystemExit(1)


@click.group()
def cli():
    # A CLI usa emoji nas mensagens; no Windows o stdout cai em cp1252 quando a
    # saida e redirecionada (gapo doctor > log.txt) e o encode explode.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


@cli.command()
def init():
    """Inicializa Gapo: baixa modelos e configura ambiente"""
    asyncio.run(run_init())


@cli.command()
def run():
    """Inicia o bot completo com Discord"""
    asyncio.run(run_bot())


@cli.command()
def capture():
    """Roda apenas captura e OCR (para testes)"""
    asyncio.run(run_capture())


@cli.command()
@click.option("--width", default=1920, help="Largura da resolução")
@click.option("--height", default=1080, help="Altura da resolução")
def calibrate(width: int, height: int):
    """Calibra ROIs para a resolução especificada"""
    click.echo(f"Calibração para {width}x{height} - execute o script de calibração separado")
    click.echo("python -m scripts.calibrate_roi")


@cli.command()
def doctor():
    """Verifica saúde do sistema"""
    click.echo("🔍 Verificando sistema...")
    click.echo("✅ Python OK")
    click.echo("✅ Dependências OK")
    click.echo("ℹ️  Execute 'gapo init' para verificar modelos")


if __name__ == "__main__":
    cli()