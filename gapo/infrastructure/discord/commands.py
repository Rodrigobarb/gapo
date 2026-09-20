import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from gapo.core.logging import get_logger

logger = get_logger("discord_commands")


def setup_commands(bot: commands.Bot, session):
    """Registra os slash commands.

    `session` e o CLIController: e ele que tem voz e captura na mao e sabe
    ligar as duas coisas (start_coaching/stop_coaching/get_status).
    """

    @bot.tree.command(name="coach_start", description="Inicia o coach e entra no canal de voz")
    @app_commands.describe(channel="Canal de voz (opcional, usa o canal atual)")
    async def coach_start(interaction: discord.Interaction, channel: Optional[discord.VoiceChannel] = None):
        await interaction.response.defer()
        voice_channel = channel or (interaction.user.voice.channel if interaction.user.voice else None)
        if not voice_channel:
            await interaction.followup.send("❌ Você precisa estar em um canal de voz ou especificar um.")
            return

        success = await session.start_coaching(voice_channel.id)
        if success:
            await interaction.followup.send(f"✅ Coach iniciado no canal **{voice_channel.name}**!")
        else:
            await interaction.followup.send("❌ Falha ao iniciar coach. Verifique logs.")

    @bot.tree.command(name="coach_stop", description="Para o coach e sai do canal de voz")
    async def coach_stop(interaction: discord.Interaction):
        await interaction.response.defer()
        await session.stop_coaching()
        await interaction.followup.send("⏹️ Coach parado e desconectado do canal de voz.")

    @bot.tree.command(name="coach_status", description="Mostra status do coach")
    async def coach_status(interaction: discord.Interaction):
        await interaction.response.defer()
        status = await session.get_status()
        embed = discord.Embed(title="📊 Status do Gapo", color=0x00ff00)
        embed.add_field(name="Capturando", value="✅ Sim" if status["capturing"] else "❌ Não", inline=True)
        embed.add_field(name="Voice Conectado", value="✅ Sim" if status["voice_connected"] else "❌ Não", inline=True)
        embed.add_field(name="FPS", value=f"{status['fps']:.1f}", inline=True)
        embed.add_field(name="Eventos/min", value=status["events_per_min"], inline=True)
        embed.add_field(name="VRAM GPU", value=f"{status['vram_used_mb']:.0f} MB", inline=True)
        embed.add_field(name="LLM Status", value=status["llm_status"], inline=True)
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="coach_config", description="Configura o coach")
    @app_commands.describe(
        event_cooldown="Cooldown entre dicas automáticas (segundos)",
        gapo_cooldown="Cooldown entre perguntas Gapo (segundos)",
    )
    async def coach_config(
        interaction: discord.Interaction,
        event_cooldown: Optional[float] = None,
        gapo_cooldown: Optional[float] = None,
    ):
        await interaction.response.defer()
        changes = []
        if event_cooldown is not None:
            session.set_event_cooldown(event_cooldown)
            changes.append(f"Event cooldown: {event_cooldown}s")
        if gapo_cooldown is not None:
            session.set_gapo_cooldown(gapo_cooldown)
            changes.append(f"Gapo cooldown: {gapo_cooldown}s")

        if changes:
            await interaction.followup.send("✅ Configurações atualizadas:\n" + "\n".join(changes))
        else:
            await interaction.followup.send("ℹ️ Nenhuma alteração feita. Use os parâmetros para configurar.")

    @bot.tree.command(name="coach_calibrate", description="Calibra ROIs para sua resolução")
    async def coach_calibrate(interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(
            "🔧 **Calibração de ROIs**\n"
            "1. Abra o LoL em modo janela sem bordas na resolução desejada\n"
            "2. Execute o script de calibração na máquina do bot\n"
            "3. Clique nos cantos de cada elemento do HUD\n"
            "4. Salve o preset\n\n"
            "Use: `python -m scripts.calibrate_roi` no terminal do bot."
        )