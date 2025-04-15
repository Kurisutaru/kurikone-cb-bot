import datetime
from zoneinfo import ZoneInfo

import discord
import pytz
from discord import app_commands
from discord.ext import commands, tasks

import utils
from globals import TL_SHIFTER_CHANNEL, SPACE_PATTERN, NON_DIGIT, NEW_LINE, locale, logger
from models import GuildPlayer
from services import MainService

l = locale
log = logger
_main_service = MainService()


class ClanBattleCommands(commands.Cog, name="Clan Battle Commands", description="Collection of Clan Battle Commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="report", description="Report generator")
    @app_commands.describe(year="Clan battle period year", month="Clan battle period month",
                           day="Clan battle period day")
    async def sc_report(self, interaction: discord.Interaction, year: int, month: int, day: int):
        guild_id = interaction.guild_id
        if not interaction.user.guild_permissions.administrator:
            return await utils.send_message_medium(interaction, l.t(guild_id, "system.not_administrator",
                                                                    user=interaction.user.display_name))

        await interaction.response.defer(thinking=True, ephemeral=True)

        msg_content = l.t(guild_id, "message.not_found", input="Report")
        report_result = await _main_service.generate_report_text(guild_id=interaction.guild_id, year=year, month=month,
                                                                day=day)
        if report_result.is_success:
            msg_content = report_result.result

        msg = await interaction.followup.send(content=msg_content, ephemeral=True)
        if msg:
            await msg.delete(delay=120)

    @app_commands.command(name="sync_user_role", description="Sync user with selected role for Clan Battle Report")
    @app_commands.describe(role="Discord Role")
    async def sc_sync_user_role(self, interaction: discord.Interaction, role: discord.Role):
        guild_id = interaction.guild_id
        if not interaction.user.guild_permissions.administrator:
            return await utils.send_message_medium(interaction, l.t(guild_id, "system.not_administrator",
                                                                    user=interaction.user.display_name))

        await interaction.response.defer(thinking=True, ephemeral=True)

        members = [GuildPlayer(
            guild_id=interaction.guild_id,
            player_id=member.id,
            player_name=member.display_name
        )
            for member in role.members]

        service_result = await _main_service.sync_user_role(guild_id=guild_id, members=members)
        msg_content = l.t(guild_id, "message.done_sync")
        if not service_result.is_success:
            msg_content = service_result.error_messages

        await _main_service.refresh_report_channel_message(interaction.guild)

        msg = await interaction.followup.send(content=msg_content, ephemeral=True)
        if msg:
            await msg.delete(delay=30)

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

        content = message.content
        lines = content.split('\n', 1)  # Split only once if possible
        if not lines:
            await bot.process_commands(message)
            return

        # Process first line
        first_line, *rest = lines[0].split('\n')  # Handle potential multi-split
        first_segment = SPACE_PATTERN.split(first_line.strip(), 1)[0]
        second_str = NON_DIGIT.sub('', first_segment)

        if not second_str.isdigit():
            await bot.process_commands(message)
            return

        second = int(second_str)
        if second > 90:
            await bot.process_commands(message)
            return

        sec_reduction = 90 - second
        result_lines = [
            f"TL Shift for {second}s",
            "```powershell"
        ]

        # Process remaining lines
        for line in (lines[1].split('\n') if len(lines) > 1 else []):
            parts = SPACE_PATTERN.split(line.strip(), 1)
            if len(parts) < 2:
                continue

            time_str, desc = parts
            try:
                parsed_time = utils.time_to_seconds(time_str)
            except ValueError:
                continue

            result_time = parsed_time - sec_reduction
            if result_time <= 0:
                continue

            result_lines.append(f"{utils.format_time(result_time)}  {desc.strip()}")

        # Only send response if we have valid entries
        if len(result_lines) > 2:
            result_lines.append("```")
            await message.reply(NEW_LINE.join(result_lines))

    #Background task
    jst = pytz.timezone('Asia/Tokyo')
    everyday_cb_time = datetime.time(hour=3, minute=5, tzinfo=jst)
    @tasks.loop(time=everyday_cb_time)
    async def refresh_clan_battle_report_daily(self):
        for guild in self.bot.guilds:
            log.info(f"Refreshing Clan Battle Report Daily on {guild.name} - {guild.id}")
            await _main_service.refresh_report_channel_message(guild)

async def setup(bot: commands.Bot):
    await bot.add_cog(ClanBattleCommands(bot))