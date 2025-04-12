from datetime import datetime

from attr import Factory
from attrs import field, define

from enums import *
from typing import TypeVar, Optional, Generic

T = TypeVar('T')


@define
class Guild:
    guild_id: int = field(default=None)
    guild_name: str = field(default=None)


@define
class Channel:
    channel_id: int = field(default=None)
    guild_id: int = field(default=None)
    channel_type: ChannelEnum = field(default=None, converter=lambda x: ChannelEnum[x] if isinstance(x, str) else x)


@define
class ChannelMessage:
    channel_id: int = field(default=None)
    message_id: int = field(default=None)


@define
class ClanBattleBossEntry:
    guild_id: int
    clan_battle_boss_entry_id: int = field(default=None)
    message_id: int = field(default=None)
    clan_battle_period_id: int = field(default=None)
    clan_battle_boss_id: int = field(default=None)
    name: str = field(default=None)
    image_path: str = field(default=None)
    boss_round: int = field(default=None)
    current_health: int = field(default=None)
    max_health: int = field(default=None)


@define
class ClanBattleBossBook:
    guild_id: int
    clan_battle_boss_book_id: int = field(default=None)
    clan_battle_boss_entry_id: int = field(default=None)
    player_id: int = field(default=None)
    player_name: str = field(default=None)
    attack_type: AttackTypeEnum = field(converter=lambda x: AttackTypeEnum[x] if isinstance(x, str) else x, default=None)
    damage: int = field(default=None)
    clan_battle_overall_entry_id: int = field(default=None)
    leftover_time: int = field(default=None)
    entry_date: datetime = field(default=None)


@define
class ClanBattleBoss:
    clan_battle_boss_id: int = field(default=None)
    name: str = field(default=None)
    description: str = field(default=None)
    image_path: str = field(default=None)
    position: int = field(default=None)


@define
class ClanBattleBossHealth:
    clan_battle_boss_health_id: int = field(default=None)
    position: int = field(default=None)
    round_from: int = field(default=None)
    round_to: int = field(default=None)
    health: int = field(default=None)


@define
class ClanBattlePeriod:
    clan_battle_period_id: int = field(default=None)
    clan_battle_period_name: str = field(default=None)
    date_from: datetime = field(default=None)
    date_to: datetime = field(default=None)
    boss1_id: int = field(default=None)
    boss2_id: int = field(default=None)
    boss3_id: int = field(default=None)
    boss4_id: int = field(default=None)
    boss5_id: int = field(default=None)


@define
class ClanBattleOverallEntry:
    clan_battle_overall_entry_id: int = field(default=None)
    guild_id: int = field(default=None)
    clan_battle_period_id: int = field(default=None)
    clan_battle_boss_id: int = field(default=None)
    player_id: int = field(default=None)
    player_name: str = field(default=None)
    round: int = field(default=None)
    attack_type: AttackTypeEnum = field(converter=lambda x: AttackTypeEnum[x] if isinstance(x, str) else x, default=None)
    damage: int = field(default=None)
    leftover_time: int = field(default=None)
    overall_leftover_entry_id: int = field(default=None)
    entry_date: datetime = field(default=None)


@define
class ClanBattleLeftover:
    clan_battle_overall_entry_id: int = field(default=None)
    clan_battle_boss_id: int = field(default=None)
    clan_battle_boss_name: str = field(default=None)
    player_id: int = field(default=None)
    attack_type: AttackTypeEnum = field(converter=lambda x: AttackTypeEnum[x] if isinstance(x, str) else x, default=None)
    leftover_time: int = field(default=None)
    overall_leftover_entry_id: int = field(default=None)


@define
class ServiceResult(Generic[T]):
    result: T = field(default=None)
    is_success: bool = field(default=False)
    error_messages: str = field(default=None)

    def set_success(self, result: T):
        self.result = result
        self.is_success = True

    def set_error(self, err_msg: str):
        self.error_messages = err_msg
        self.is_success = False
