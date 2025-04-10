import re

from discord.ext import commands

import utils
from locales import Locale, guild_locale
from logger import KuriLogger
from repository import *
from services import GuildService, ChannelService, ClanBattlePeriodService, MainService

# Global Service
main_service = MainService()
guild_service = GuildService()
channel_service = ChannelService()
clan_battle_period_service = ClanBattlePeriodService()

# Global Variable
NEW_LINE = "\n"
TL_SHIFTER_CHANNEL = {}

# Precompile regex patterns for better performance
SPACE_PATTERN = re.compile(r'[ \t　]+')
NON_DIGIT = re.compile(r'\D')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

logger = KuriLogger()
l = Locale()


@bot.event
async def on_ready():
    await bot.wait_until_ready()
    logger.info(f'We have logged in as {bot.user}')
    for guild in bot.guilds:
        guild_locale[guild.id] = guild.preferred_locale.value.lower()
        await setup_channel(guild)


@bot.event
async def on_guild_join(guild):
    await setup_channel(guild)


async def setup_channel(guild):
    print(f'Setup for guild {guild.id} - {guild.name}')
    await main_service.setup_guild_channel_message(guild=guild, tl_shifter_channel=TL_SHIFTER_CHANNEL)


@bot.event
async def on_message(message):
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


bot.run(config.DISCORD_TOKEN, log_handler=None)
