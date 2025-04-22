import discord
from dependency_injector.wiring import inject, Provider
from discord import app_commands
from discord.ext import commands

import utils
from cogs.base_cog import BaseCog
from enums import HelpTopic
from locales import Locale


class HelpCommands(
    BaseCog, name="Help Commands", description="Collection of Help Commands"
):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.bot = bot

    @app_commands.command(
        name="help", description="Show the help available from the topic"
    )
    @app_commands.describe(topic="Topic you want to check")
    async def sc_help(
        self,
        interaction: discord.Interaction,
        topic: HelpTopic().get_keys(),
    ):
        guild_id = interaction.guild_id
        if not interaction.user.guild_permissions.administrator:
            return await utils.send_message_medium(
                interaction,
                self.l.t(
                    guild_id,
                    "system.not_administrator",
                    user=interaction.user.display_name,
                ),
            )

        content = HelpTopic.get_value(topic)

        await interaction.response.send_message(
            content=content, ephemeral=True, delete_after=60
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCommands(bot))
