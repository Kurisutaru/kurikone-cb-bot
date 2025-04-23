import datetime

import discord
from dependency_injector.wiring import inject
from discord import app_commands
from discord.ext import commands, tasks

import utils
from cogs.base_cog import BaseCog
from globals import (
    TL_SHIFTER_CHANNEL,
    SPACE_PATTERN,
    NON_DIGIT,
    NEW_LINE,
    datetime_format,
    TL_SHIFTER_TIME_FORMAT,
)
from models import GuildPlayer


class ClanBattleCommands(
    BaseCog,
    name="Clan Battle Commands",
    description="Collection of Clan Battle Commands",
):
    @inject
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.bot = bot
        self.refresh_clan_battle_report_daily.start()
        self.check_clan_battle_period.start()

    def cog_unload(self) -> None:
        self.refresh_clan_battle_report_daily.cancel()
        self.check_clan_battle_period.cancel()

    @app_commands.command(name="report", description="Report generator")
    @app_commands.describe(
        year="Clan battle period year",
        month="Clan battle period month",
        day="Clan battle period day",
    )
    async def sc_report(
        self,
        interaction: discord.Interaction,
        year: int,
        month: int,
        day: int,
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

        await interaction.response.defer(thinking=True, ephemeral=True)

        msg_content = self.l.t(guild_id, "message.not_found", input="Report")
        report_result = await self.main_service.generate_report_text(
            guild_id=interaction.guild_id, year=year, month=month, day=day
        )
        if report_result.is_success:
            msg_content = report_result.result

        msg = await interaction.followup.send(content=msg_content, ephemeral=True)
        if msg:
            await msg.delete(delay=120)

        return None

    @app_commands.command(
        name="sync_user_role",
        description="Sync user with selected role for Clan Battle Report",
    )
    @app_commands.describe(role="Discord Role")
    async def sc_sync_user_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
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

        await interaction.response.defer(thinking=True, ephemeral=True)

        members = [
            GuildPlayer(
                guild_id=interaction.guild_id,
                player_id=member.id,
                player_name=member.display_name,
            )
            for member in role.members
        ]

        service_result = await self.main_service.sync_user_role(
            guild_id=guild_id, members=members
        )
        msg_content = self.l.t(guild_id, "message.done_sync")
        if not service_result.is_success:
            msg_content = service_result.error_messages

        await self.main_service.refresh_report_channel_message(interaction.guild)

        msg = await interaction.followup.send(content=msg_content, ephemeral=True)
        if msg:
            await msg.delete(delay=30)

        return None

    # TL Shifter
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        bot = self.bot
        # Early exit for bot messages
        if message.author == bot.user:
            return

        # Early exit for non-target channels
        if message.channel.id not in TL_SHIFTER_CHANNEL:
            await bot.process_commands(message)
            return

        lines = message.content.strip().splitlines()
        if not lines:
            await bot.process_commands(message)
            return

        # Get base seconds from the first line
        first_line = lines[0].strip()
        first_segment = SPACE_PATTERN.split(first_line, 1)[0]
        second_str = NON_DIGIT.sub("", first_segment)

        if not second_str.isdigit():
            await bot.process_commands(message)
            return

        base_seconds = int(second_str)
        if base_seconds > 90:
            await bot.process_commands(message)
            return

        sec_reduction = 90 - base_seconds
        result_lines = [f"TL Shift for {base_seconds}s", "```powershell"]

        # Process each subsequent line
        for line in lines[1:]:
            parts = SPACE_PATTERN.split(line.strip(), 1)
            if len(parts) < 2:
                continue

            time_str, desc = parts
            time_str = time_str.strip()

            # Convert to seconds
            match = TL_SHIFTER_TIME_FORMAT.match(time_str)
            if match:
                minutes, seconds = map(int, match.groups())
                total_seconds = minutes * 60 + seconds
            elif time_str.isdigit():
                total_seconds = int(time_str)
            else:
                continue

            # Apply the reduction
            new_seconds = total_seconds - sec_reduction
            if new_seconds <= 0:
                continue

            # Format and add
            minutes, seconds = divmod(new_seconds, 60)
            formatted_time = f"{minutes}:{seconds:02}"
            result_lines.append(
                f"{formatted_time}　 ㅤ{desc.strip()}"
            )  # Add ideographic space

        if len(result_lines) > 2:
            result_lines.append("```")
            await message.reply(NEW_LINE.join(result_lines))

        await bot.process_commands(message)

    # Background task
    everyday_cb_time = datetime.time(hour=20, minute=0)

    @tasks.loop(time=everyday_cb_time)
    async def refresh_clan_battle_report_daily(self):
        for guild in self.bot.guilds:
            self.log.info(f"Refresh Bot Daily: {guild.name} - {guild.id}")
            await self.main_service.setup_guild_channel_message(
                guild, TL_SHIFTER_CHANNEL
            )

    everyday_cb_end_time = datetime.time(hour=15, minute=0)

    @tasks.loop(time=everyday_cb_end_time, reconnect=True)
    async def check_clan_battle_period(self):
        self.log.info(
            f"Check Clan Battle Period daily @{utils.now().strftime(datetime_format)}"
        )
        await self.main_service.check_clan_battle_period()


async def setup(bot: commands.Bot):
    await bot.add_cog(ClanBattleCommands(bot))
