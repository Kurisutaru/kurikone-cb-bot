from discord.ext import commands

from globals import TL_SHIFTER_CHANNEL
from locales import guild_locale, Locale
from logger import KuriLogger
from repository import *
from services import MainService

main_service = MainService()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

logger = KuriLogger()
l = Locale()

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    logger.info(f'We have logged in as {bot.user}')

    await bot.load_extension("cogs.help")
    await bot.load_extension("cogs.setup")
    await bot.load_extension("cogs.clan_battle")

    for guild in bot.guilds:
        guild_locale[guild.id] = guild.preferred_locale.value.lower()
        await setup_channel(guild)


@bot.event
async def on_guild_join(guild):
    await setup_channel(guild)


async def setup_channel(guild):
    logger.info(f'Setup for guild {guild.id} - {guild.name}')
    await main_service.setup_guild_channel_message(guild=guild, tl_shifter_channel=TL_SHIFTER_CHANNEL)


bot.run(config.DISCORD_TOKEN, log_handler=None)
