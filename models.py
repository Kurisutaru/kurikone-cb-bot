from datetime import datetime
from enum import Enum
from typing import TypeVar, Generic, Union

from attrs import field, define, fields

from enums import ChannelEnum, AttackTypeEnum, PeriodType

T = TypeVar("T")


class EnumSerializerMixin:
    def to_db_dict(self):
        data = {}
        for var in fields(self.__class__):
            value = getattr(self, var.name)

            # Handle Enums
            if isinstance(value, Enum):
                data[var.name] = value.name
            # Default case
            else:
                data[var.name] = value

        return data


@define
class Guild:
    guild_id: int = field(default=None)
    guild_name: str = field(default=None)


@define
class Channel(EnumSerializerMixin):
    channel_id: int = field(default=None)
    guild_id: int = field(default=None)
    channel_type: ChannelEnum = field(
        default=None, converter=lambda x: ChannelEnum[x] if isinstance(x, str) else x
    )
    message_id: int = field(default=None)


@define
class ChannelBoss(Channel):
    boss_id: int = field(default=None)


@define
class ClanBattleBossEntry:
    guild_id: int
    clan_battle_boss_entry_id: int = field(default=None)
    clan_battle_period_id: int = field(default=None)
    clan_battle_boss_id: int = field(default=None)
    boss_round: int = field(default=None)
    current_health: int = field(default=None)
    is_active: bool = field(default=None)


@define
class ClanBattleBossEntries(ClanBattleBossEntry):
    boss_name: str = field(default=None)
    image_path: str = field(default=None)
    max_health: int = field(default=None)


@define
class ClanBattleBossBook(EnumSerializerMixin):
    guild_id: int
    clan_battle_boss_book_id: int = field(default=None)
    clan_battle_boss_entry_id: int = field(default=None)
    player_id: int = field(default=None)
    player_name: str = field(default=None)
    attack_type: AttackTypeEnum = field(
        converter=lambda x: (AttackTypeEnum[x] if isinstance(x, str) else x),
        default=None,
    )
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
class ClanBattleBosses(ClanBattleBoss):
    health: int = field(default=None)


@define
class ClanBattleBossHealth:
    clan_battle_boss_health_id: int = field(default=None)
    position: int = field(default=None)
    round_from: int = field(default=None)
    round_to: int = field(default=None)
    health: int = field(default=None)


@define
class ClanBattlePeriod(EnumSerializerMixin):
    clan_battle_period_id: int = field(default=None)
    clan_battle_period_name: str = field(default=None)
    period_type: PeriodType = field(
        converter=lambda x: PeriodType[x] if isinstance(x, str) else x,
        default=None,
    )
    date_from: datetime = field(default=None)
    date_to: datetime = field(default=None)
    is_active: bool = field(default=False)
    boss1_id: int = field(default=None)
    boss2_id: int = field(default=None)
    boss3_id: int = field(default=None)
    boss4_id: int = field(default=None)
    boss5_id: int = field(default=None)

    def merge_bosses(self, source: Union[dict, object]):
        for i in range(1, 6):
            attr = f"boss{i}_id"
            if isinstance(source, dict):
                setattr(self, attr, source.get(attr))
            else:
                setattr(self, attr, getattr(source, attr, None))


@define
class ClanBattlePeriodDay(ClanBattlePeriod):
    current_day: int = field(default=None)


@define
class ClanBattleOverallEntry(EnumSerializerMixin):
    clan_battle_overall_entry_id: int = field(default=None)
    guild_id: int = field(default=None)
    clan_battle_boss_entry_id: int = field(default=None)
    clan_battle_period_id: int = field(default=None)
    clan_battle_boss_id: int = field(default=None)
    player_id: int = field(default=None)
    player_name: str = field(default=None)
    boss_round: int = field(default=None)
    day: int = field(default=None)
    damage: int = field(default=None)
    attack_type: AttackTypeEnum = field(
        converter=lambda x: AttackTypeEnum[x] if isinstance(x, str) else x, default=None
    )
    leftover_time: int = field(default=None)
    overall_leftover_entry_id: int = field(default=None)
    entry_date: datetime = field(default=None)


@define
class ClanBattleLeftover(EnumSerializerMixin):
    clan_battle_overall_entry_id: int = field(default=None)
    clan_battle_boss_id: int = field(default=None)
    clan_battle_boss_name: str = field(default=None)
    player_id: int = field(default=None)
    attack_type: AttackTypeEnum = field(
        converter=lambda x: (
            AttackTypeEnum[x] if isinstance(x, str) else AttackTypeEnum(x)
        ),
        default=None,
    )
    leftover_time: int = field(default=None)
    overall_leftover_entry_id: int = field(default=None)


@define
class ClanBattleReportMessage(EnumSerializerMixin):
    clan_battle_report_message_id: int = field(default=None)
    guild_id: int = field(default=None)
    clan_battle_period_id: int = field(default=None)
    day: int = field(default=None)
    message_id: int = field(default=None)


@define
class GuildPlayer:
    guild_id: int = field(default=None)
    player_id: int = field(default=None)
    player_name: str = field(default=None)


@define
class ClanBattleReportEntry:
    player_name: str = field(default=None)
    patk_count: int = field(default=None)
    matk_count: int = field(default=None)
    leftover_count: int = field(default=None)
    carry_count: int = field(default=None)


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
