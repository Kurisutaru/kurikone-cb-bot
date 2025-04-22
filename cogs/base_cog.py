from typing import Optional

from dependency_injector.wiring import inject, Provide
from discord.ext import commands

from locales import Locale
from logger import KuriLogger
from services import MainService, ClanBattlePeriodService


class BaseCog(commands.Cog):
    """Base cog class with dependency injection support"""

    @inject
    def __init__(
        self,
        bot: commands.Bot,
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
        main_service: MainService = Provide["main_service"],
        clan_battle_period_service: ClanBattlePeriodService = Provide[
            "clan_battle_period_service"
        ],
    ):
        self.bot = bot
        self.l = l
        self.log = log
        self.main_service = main_service
        self.clan_battle_period_service = clan_battle_period_service
