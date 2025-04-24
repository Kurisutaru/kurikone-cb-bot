import discord
from dependency_injector.wiring import inject, Provide
from discord.ext import commands
from discord.ext.commands import Bot

from config import check_env_vars, config
from dependency import Container, container
from globals import GUILD_LOCALE, TL_SHIFTER_CHANNEL

from logger import KuriLogger

from services import MainService

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
@inject
async def on_ready(
    log: KuriLogger = Provide["logger"],
    main_service: MainService = Provide["main_service"],
):
    await bot.wait_until_ready()
    log.info(f"We have logged in as {bot.user}")

    await bot.load_extension("cogs.help")
    await bot.load_extension("cogs.setup")
    await bot.load_extension("cogs.clan_battle")

    await update_presence(bot)
    await bot.tree.sync()

    await main_service.check_clan_battle_period()

    for guild in bot.guilds:
        GUILD_LOCALE[guild.id] = guild.preferred_locale.value
        await setup_channel(guild)


@bot.event
async def on_guild_join(guild):
    await update_presence(bot)
    await setup_channel(guild)


@bot.event
@inject
async def on_guild_remove(
    guild,
    log: KuriLogger = Provide["logger"],
    main_service: MainService = Provide["main_service"],
):
    log.info(f"Leaving guild {guild.id} - {guild.name}")
    await update_presence(bot)
    await main_service.uninstall_bot_command(guild, TL_SHIFTER_CHANNEL)


async def setup_channel(
    guild,
    log: KuriLogger = Provide["logger"],
    main_service: MainService = Provide["main_service"],
):
    log.info(f"Setup for guild {guild.id} - {guild.name}")
    await main_service.setup_guild_channel_message(guild, TL_SHIFTER_CHANNEL)


async def update_presence(discord_bot: Bot) -> None:
    activity = discord.Activity(
        name=f"{len(discord_bot.guilds)} Servers", type=discord.ActivityType.listening
    )
    await discord_bot.change_presence(activity=activity)


if __name__ == "__main__":
    container.init_resources()
    bot.container = container
    container.wire(
        modules=[
            __name__,
            "config",
            "database",
            "services",
            "repository",
            "ui",
            "utils",
            "cogs.base_cog",
        ],
        packages=["cogs"],
    )
    # Check so people don't run away without .env file
    check_env_vars()
    bot.run(config.DISCORD_TOKEN, log_handler=None)
