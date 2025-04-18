from discord.ext import commands
from discord.ext.commands import Bot

from config import check_env_vars
import globals
from globals import TL_SHIFTER_CHANNEL, logger, locale
from locales import guild_locale
from repository import *
from services import MainService, ClanBattlePeriodService

_main_service = MainService()
_clan_battle_period_service = ClanBattlePeriodService()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

log = logger
l = locale


@bot.event
async def on_ready():
    await bot.wait_until_ready()
    log.info(f'We have logged in as {bot.user}')

    await bot.load_extension("cogs.help")
    await bot.load_extension("cogs.setup")
    await bot.load_extension("cogs.clan_battle")

    await update_presence(bot)
    await bot.tree.sync()

    # Get Current and store Clan Battle Period
    cb_period_result = await _clan_battle_period_service.get_current_cb_period()
    globals.CURRENT_CB_PERIOD_ID = cb_period_result.result if cb_period_result.is_success else None

    for guild in bot.guilds:
        guild_locale[guild.id] = guild.preferred_locale.value.lower()
        await setup_channel(guild)

@bot.event
async def on_guild_join(guild):
    await update_presence(bot)
    await setup_channel(guild)

@bot.event
async def on_guild_remove(guild):
    log.info(f'Leaving guild {guild.id} - {guild.name}')
    await update_presence(bot)
    await _main_service.uninstall_bot_command(guild, TL_SHIFTER_CHANNEL)

async def setup_channel(guild):
    log.info(f'Setup for guild {guild.id} - {guild.name}')
    await _main_service.setup_guild_channel_message(guild, TL_SHIFTER_CHANNEL)

async def update_presence(discord_bot: Bot) -> None:
    activity = discord.Activity(name=f"{len(discord_bot.guilds)} Servers", type=discord.ActivityType.listening)
    await discord_bot.change_presence(activity=activity)

if __name__ == "__main__":
    # Check so people don't run away without .env file
    check_env_vars()
    bot.run(config.DISCORD_TOKEN, log_handler=None)

