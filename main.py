from pathlib import Path

import discord
from discord.ext import commands

from config import check_env_vars
from globals import TL_SHIFTER_CHANNEL, logger, locale
from locales import guild_locale
from repository import *
from services import MainService

main_service = MainService()

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
    await main_service.uninstall_bot_command(guild, TL_SHIFTER_CHANNEL)

async def setup_channel(guild):
    log.info(f'Setup for guild {guild.id} - {guild.name}')
    await main_service.setup_guild_channel_message(guild, TL_SHIFTER_CHANNEL)

async def update_presence(bot):
    activity = discord.Activity(name=f"{len(bot.guilds)} Servers", type=discord.ActivityType.listening)
    await bot.change_presence(activity=activity)

if __name__ == "__main__":
    # Check so people don't run away without .env file
    check_env_vars()
    bot.run(config.DISCORD_TOKEN, log_handler=None)

