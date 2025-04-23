import logging

from dependency_injector import containers, providers

from config import GlobalConfig
from database import DatabasePool
from locales import Locale
from logger import KuriLogger
from repository import (
    GuildRepository,
    ChannelRepository,
    ChannelMessageRepository,
    ClanBattleBossEntryRepository,
    ClanBattleBossBookRepository,
    ClanBattlePeriodRepository,
    ClanBattleBossRepository,
    ClanBattleBossHealthRepository,
    ClanBattleOverallEntryRepository,
    GuildPlayerRepository,
    ClanBattleReportMessageRepository,
    GenericRepository,
    ErrorLogRepository,
)
from services import MainService, ClanBattlePeriodService, Services, UiService


class Container(containers.DeclarativeContainer):
    # Singleton provider for Logger
    logger = providers.Singleton(
        KuriLogger,
        name="discord",
        log_file="discord.log",
        max_days=7,
        file_level=logging.DEBUG,
        console_level=logging.INFO,
        timezone="Asia/Tokyo",
    )
    # Singleton provider for Locale
    locale = providers.Singleton(
        Locale,
        load_path="locales",
        filename_format="{locale}.{format}",
        file_format="yaml",
    )
    # Singleton provider for Config
    config = providers.Singleton(GlobalConfig)
    # Singleton provider for db_pool
    db_pool = providers.Singleton(
        DatabasePool,
        log=logger,
        config=config,
    )

    # Repositories
    guild_repo = providers.Singleton(GuildRepository)
    channel_repo = providers.Singleton(ChannelRepository)
    channel_message_repo = providers.Singleton(ChannelMessageRepository)
    clan_battle_boss_entry_repo = providers.Singleton(ClanBattleBossEntryRepository)
    clan_battle_boss_book_repo = providers.Singleton(ClanBattleBossBookRepository)
    clan_battle_period_repo = providers.Singleton(ClanBattlePeriodRepository)
    clan_battle_boss_repo = providers.Singleton(ClanBattleBossRepository)
    clan_battle_boss_health_repo = providers.Singleton(ClanBattleBossHealthRepository)
    clan_battle_overall_entry_repo = providers.Singleton(
        ClanBattleOverallEntryRepository
    )
    guild_player_repo = providers.Singleton(GuildPlayerRepository)
    clan_battle_report_message_repo = providers.Singleton(
        ClanBattleReportMessageRepository
    )
    generic_repo = providers.Singleton(GenericRepository)
    error_log_repo = providers.Singleton(ErrorLogRepository)

    # Services (deferred import to avoid circular dependency)
    services = providers.Singleton(
        Services,  # Lazy import
        guild_repo=guild_repo,
        channel_repo=channel_repo,
        channel_message_repo=channel_message_repo,
        clan_battle_boss_entry_repo=clan_battle_boss_entry_repo,
        clan_battle_boss_book_repo=clan_battle_boss_book_repo,
        clan_battle_period_repo=clan_battle_period_repo,
        clan_battle_boss_repo=clan_battle_boss_repo,
        clan_battle_boss_health_repo=clan_battle_boss_health_repo,
        clan_battle_overall_entry_repo=clan_battle_overall_entry_repo,
        guild_player_repo=guild_player_repo,
        clan_battle_report_message_repo=clan_battle_report_message_repo,
        generic_repo=generic_repo,
        error_log_repo=error_log_repo,
    )

    main_service = providers.Singleton(MainService)
    clan_battle_period_service = providers.Singleton(ClanBattlePeriodService)
    ui_service = providers.Singleton(UiService)


container = Container()
