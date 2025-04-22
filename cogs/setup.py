import discord
from discord import app_commands
from discord.ext import commands

import utils
from cogs.base_cog import BaseCog
from globals import TL_SHIFTER_CHANNEL
from ui import ConfirmationButtonView


class SetupCommands(
    BaseCog, name="Setup Commands", description="Collection of Setup Commands"
):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.bot = bot

    @app_commands.command(
        name="install",
        description="This command will try to install all channel related to the bot functions",
    )
    async def sc_install(
        self,
        interaction: discord.Interaction,
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

        async def button_ok_callback(interact: discord.Interaction):
            await interact.response.defer(thinking=True, ephemeral=True)

            guild = interaction.guild
            setup_result = await self.main_service.install_bot_command(
                guild, TL_SHIFTER_CHANNEL
            )
            if not setup_result.is_success:
                await utils.send_followup_short(
                    interaction=interact,
                    content=f"{setup_result.error_messages}",
                    ephemeral=True,
                )
                return

            await utils.send_followup_short(
                interaction=interact,
                content=self.l.t(guild_id, "message.done_install"),
                ephemeral=True,
            )

        view = ConfirmationButtonView(
            guild_id=guild_id, yes_callback=button_ok_callback
        )

        await utils.send_message_medium(
            interaction=interaction,
            content=self.l.t(guild_id, "ui.prompts.install_confirmation"),
            view=view,
            ephemeral=True,
        )
        return None

    @app_commands.command(
        name="uninstall",
        description="This command will try to uninstall all channel related to the bots and removing data from database",
    )
    async def sc_uninstall(
        self,
        interaction: discord.Interaction,
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

        async def button_ok_callback(interact: discord.Interaction):
            await interact.response.defer(thinking=True, ephemeral=True)
            guild = interaction.guild
            action = await self.main_service.uninstall_bot_command(
                guild, TL_SHIFTER_CHANNEL
            )
            if not action.is_success:
                await utils.send_followup_short(
                    interaction=interact,
                    content=f"{action.error_messages}",
                    ephemeral=True,
                )
                return

            # Delete Channel
            channels = action.result
            channels.sort(reverse=True)
            for channel_id in channels:
                channel = interact.guild.get_channel(channel_id)
                if channel:
                    await channel.delete()

            await utils.send_followup_short(
                interaction=interact,
                content=self.l.t(guild_id, "message.done_uninstall"),
                ephemeral=True,
            )

        view = ConfirmationButtonView(
            guild_id=guild_id, yes_callback=button_ok_callback
        )

        await utils.send_message_medium(
            interaction=interaction,
            content=self.l.t(guild_id, "ui.prompts.uninstall_confirmation"),
            view=view,
            ephemeral=True,
        )
        return None


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCommands(bot))
