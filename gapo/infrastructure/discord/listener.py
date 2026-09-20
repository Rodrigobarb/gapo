import discord
from discord.ext import commands
import re
import time
from typing import Optional
from gapo.core.logging import get_logger
from gapo.utils.async_utils import RateLimiter

logger = get_logger("message_listener")


class GapoMessageListener:
    def __init__(self, bot: commands.Bot, gapo_service, trigger: str = "Gapo", on_answer=None):
        self.bot = bot
        self.gapo_service = gapo_service
        self.trigger = trigger.lower()
        self.on_answer = on_answer
        self.pattern = re.compile(rf"^{re.escape(trigger)}\s+(.+)$", re.IGNORECASE)
        
        self.global_limiter = RateLimiter(max_calls=5, window_seconds=10)
        self.user_limiters: dict[int, RateLimiter] = {}

    def _get_user_limiter(self, user_id: int) -> RateLimiter:
        if user_id not in self.user_limiters:
            self.user_limiters[user_id] = RateLimiter(max_calls=1, window_seconds=10)
        return self.user_limiters[user_id]

    async def on_message(self, message: discord.Message) -> bool:
        if message.author.bot:
            return False

        if not message.guild:
            return False

        match = self.pattern.match(message.content.strip())
        if not match:
            return False

        question = match.group(1).strip()
        if not question:
            return False

        user_id = message.author.id
        user_limiter = self._get_user_limiter(user_id)

        if not user_limiter.acquire_sync():
            await message.reply("⏳ Calma aí! Espere um pouco antes de perguntar de novo.", delete_after=5)
            return True

        if not self.global_limiter.acquire_sync():
            await message.reply("⏳ Muitas perguntas ao mesmo tempo. Tente novamente em alguns segundos.", delete_after=5)
            return True

        logger.info(f"Gapo question from {message.author}: {question}")

        try:
            async with message.channel.typing():
                response = await self.gapo_service.answer_question(
                    user_id=user_id,
                    username=str(message.author),
                    question=question,
                    channel_id=message.channel.id,
                    guild_id=message.guild.id,
                )
        except Exception as e:
            logger.exception(f"Error processing Gapo question: {e}")
            await message.reply(f"❌ Erro ao processar pergunta: {e}", delete_after=15)
            return True

        if not response or not response.text:
            logger.warning("Gapo respondeu vazio")
            await message.reply("❌ Nao consegui gerar resposta. Veja os logs.", delete_after=15)
            return True

        # A resposta precisa sair em algum lugar: texto sempre, voz quando ha
        # canal conectado (o callback e quem sabe disso).
        await message.reply(response.text[:1900])  # limite de 2000 chars do Discord
        if self.on_answer:
            try:
                await self.on_answer(response)
            except Exception as e:
                logger.exception(f"Falha ao falar a resposta: {e}")

        return True

    def register(self) -> None:
        @self.bot.event
        async def on_message(message: discord.Message):
            handled = await self.on_message(message)
            if not handled:
                await self.bot.process_commands(message)

        logger.info(f"Gapo message listener registered (trigger: '{self.trigger}')")