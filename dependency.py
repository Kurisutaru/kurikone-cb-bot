from dependency_injector import containers, providers
from config import GlobalConfig
from services import MainService, ClanBattlePeriodService, Services, UiService
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


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=["main", "services", "database"],
    )
    logger = providers.Singleton(KuriLogger, timezone="Asia/Tokyo")
    locale = providers.Singleton(Locale)
    config = providers.Singleton(GlobalConfig)
    db_pool = providers.Singleton(DatabasePool)

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
