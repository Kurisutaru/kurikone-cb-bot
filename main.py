import asyncio
import os
import platform
import signal
import sys

import discord
from dependency_injector.wiring import inject, Provide
from discord.ext import commands

from config import check_env_vars, config
from database import DatabasePool
from dependency import container
from globals import GUILD_LOCALE, TL_SHIFTER_CHANNEL

from logger import KuriLogger

from services import MainService

should_restart = False


# Graceful shutdown, my mariadb complaining aborted connection
class MainBot(commands.Bot):
    container = None

    @inject
    def __init__(
        self,
        *args,
        logger: KuriLogger = Provide["logger"],
        main_service: MainService = Provide["main_service"],
        db_pool: DatabasePool = Provide["db_pool"],
        **kwargs,
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        command_prefix = "!"

        self.main_service = main_service
        self.db_pool = db_pool
        self.log = logger
        self.log.info("Starting Kurikone Clan Battle Bot...")
        super().__init__(
            command_prefix=command_prefix, intents=intents, *args, **kwargs
        )

    async def close(self) -> None:
        self.log.info("Closing bot and database pool...")
        if self.db_pool:
            self.db_pool.close()

        self.log.info("Closing bot...")
        await super().close()

    async def on_ready(self):
        await self.wait_until_ready()
        self.log.info(f"We have logged in as {self.user}")

        await self.load_extension("cogs.help")
        await self.load_extension("cogs.setup")
        await self.load_extension("cogs.clan_battle")

        await self.update_presence()
        await self.main_service.check_command_tree_sync(self)
        await self.main_service.check_clan_battle_period()

        for guild in self.guilds:
            GUILD_LOCALE[guild.id] = guild.preferred_locale.value
            await self.setup_channel(guild)

    async def on_guild_join(self, guild):
        await self.update_presence()
        await self.setup_channel(guild)

    async def on_guild_remove(self, guild):
        self.log.info(f"Leaving guild {guild.id} - {guild.name}")
        await self.update_presence()
        await self.main_service.uninstall_bot_command(guild, TL_SHIFTER_CHANNEL)

    async def setup_channel(self, guild):
        self.log.info(f"Setup for guild {guild.id} - {guild.name}")
        await self.main_service.setup_guild_channel_message(guild, TL_SHIFTER_CHANNEL)

    async def update_presence(self) -> None:
        activity = discord.Activity(
            name=f"{len(self.guilds)} Servers",
            type=discord.ActivityType.listening,
        )
        await self.change_presence(activity=activity)


async def main():
    global should_restart

    container.init_resources()
    container.wire(
        modules=[
            __name__,
            "main",
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
    check_env_vars()

    log: KuriLogger = container.logger()

    bot = MainBot()
    bot.container = container

    stop_event = asyncio.Event()

    def handle_stop_signal(*_):
        stop_event.set()

    def handle_restart_signal(*_):
        global should_restart
        should_restart = True
        stop_event.set()

    loop = asyncio.get_running_loop()

    if platform.system() != "Windows":
        loop.add_signal_handler(signal.SIGINT, lambda: stop_event.set())  # type: ignore
        loop.add_signal_handler(signal.SIGTERM, lambda: stop_event.set())  # type: ignore
        if hasattr(signal, "SIGHUP"):
            loop.add_signal_handler(signal.SIGHUP, lambda: handle_restart_signal())  # type: ignore

    bot_task = asyncio.create_task(bot.start(config.DISCORD_TOKEN))

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        # Windows only
        pass
    finally:
        log.info("Shutdown command detected...")
        await bot.close()
        # Cancel bot_task if still running
        if not bot_task.done():
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass

        if should_restart:
            log.info("Restarting bot process...")
            await asyncio.sleep(2)
            os.execv(sys.executable, [sys.executable] + sys.argv)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Windows only
        pass
