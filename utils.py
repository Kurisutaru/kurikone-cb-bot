import math
import random
from datetime import datetime, timedelta

from typing import List, Optional

import discord
from dependency_injector.wiring import inject, Provide
from discord import TextChannel, Colour, Message, Embed
from discord.ui import View

from config import GlobalConfig
from enums import EmojiEnum, AttackTypeEnum, PeriodType
from globals import jst, PURIKONE_LIVE_SERVICE_DATE, NEW_LINE, TL_SHIFTER_TIME_FORMAT
from locales import Locale
from logger import KuriLogger

from models import (
    ClanBattleBossEntry,
    ClanBattleOverallEntry,
    ClanBattleBossBook,
    ClanBattleBoss,
    ClanBattlePeriod,
    ClanBattleBossEntries,
)


### DISCORD STUFF UTILS
async def discord_try_fetch_message(
    channel: TextChannel, message_id: int
) -> Optional[Message]:
    try:
        return await channel.fetch_message(message_id)
    except discord.NotFound:
        return None


@inject
async def discord_close_response(
    interaction: discord.Interaction, log: KuriLogger = Provide["logger"]
):
    try:
        await interaction.response.defer(ephemeral=True)
        await interaction.delete_original_response()
    except Exception as e:
        log.error(e)


async def send_message(
    interaction: discord.Interaction,
    content: str,
    ephemeral: bool = False,
    silent: bool = None,
    embed: Embed = None,
    embeds: list[Embed] = None,
    view: View = None,
):
    param = create_message_param(
        content=content,
        embed=embed,
        embeds=embeds,
        view=view,
        ephemeral=ephemeral,
        silent=silent,
    )
    await interaction.response.send_message(**param)


@inject
async def send_message_short(
    interaction: discord.Interaction,
    content: str,
    ephemeral: bool = False,
    silent: bool = None,
    embed: Embed = None,
    embeds: list[Embed] = None,
    view: View = None,
    config: GlobalConfig = Provide["config"],
):
    param = create_message_param(
        content=content,
        embed=embed,
        embeds=embeds,
        view=view,
        ephemeral=ephemeral,
        silent=silent,
        delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_SHORT,
    )
    await interaction.response.send_message(**param)


@inject
async def send_message_medium(
    interaction: discord.Interaction,
    content: str,
    ephemeral: bool = False,
    silent: bool = None,
    embed: Embed = None,
    embeds=None,
    view: View = None,
    config: GlobalConfig = Provide["config"],
):
    param = create_message_param(
        content=content,
        embed=embed,
        embeds=embeds,
        view=view,
        ephemeral=ephemeral,
        silent=silent,
        delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_MEDIUM,
    )
    await interaction.response.send_message(**param)


@inject
async def send_message_long(
    interaction: discord.Interaction,
    content: str,
    ephemeral: bool = False,
    silent: bool = None,
    embed: Embed = None,
    embeds=None,
    view: View = None,
    config: GlobalConfig = Provide["config"],
):
    param = create_message_param(
        content=content,
        embed=embed,
        embeds=embeds,
        view=view,
        ephemeral=ephemeral,
        silent=silent,
        delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_LONG,
    )
    await interaction.response.send_message(**param)


async def send_channel_message(
    interaction: discord.Interaction,
    content: str,
    silent: bool = None,
    embed: Embed = None,
    embeds: list[Embed] = None,
    view: View = None,
):
    param = create_message_param(
        content=content, embed=embed, embeds=embeds, view=view, silent=silent
    )
    await interaction.channel.send(**param)


@inject
async def send_channel_message_short(
    interaction: discord.Interaction,
    content: str,
    silent: bool = None,
    embed: Embed = None,
    embeds: list[Embed] = None,
    view: View = None,
    config: GlobalConfig = Provide["config"],
):
    param = create_message_param(
        content=content,
        embed=embed,
        embeds=embeds,
        view=view,
        delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_SHORT,
        silent=silent,
    )
    await interaction.channel.send(**param)


@inject
async def send_channel_message_medium(
    interaction: discord.Interaction,
    content: str,
    silent: bool = None,
    embed: Embed = None,
    embeds: list[Embed] = None,
    view: View = None,
    config: GlobalConfig = Provide["config"],
):
    param = create_message_param(
        content=content,
        embed=embed,
        embeds=embeds,
        view=view,
        delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_MEDIUM,
        silent=silent,
    )
    await interaction.channel.send(**param)


@inject
async def send_channel_message_long(
    interaction: discord.Interaction,
    content: str,
    silent: bool = None,
    embed: Embed = None,
    embeds: list[Embed] = None,
    view: View = None,
    config: GlobalConfig = Provide["config"],
):
    param = create_message_param(
        content=content,
        embed=embed,
        embeds=embeds,
        view=view,
        delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_LONG,
        silent=silent,
    )
    await interaction.channel.send(**param)


@inject
async def send_followup_short(
    interaction: discord.Interaction,
    content: str,
    ephemeral: bool = None,
    config: GlobalConfig = Provide["config"],
):
    param = create_message_param(content=content, ephemeral=ephemeral)
    msg = await interaction.followup.send(**param)
    if msg:
        await msg.delete(delay=config.MESSAGE_DEFAULT_DELETE_AFTER_SHORT)


@inject
async def send_followup_medium(
    interaction: discord.Interaction,
    content: str,
    ephemeral: bool = None,
    config: GlobalConfig = Provide["config"],
):
    param = create_message_param(content=content, ephemeral=ephemeral)
    msg = await interaction.followup.send(**param)
    if msg:
        await msg.delete(delay=config.MESSAGE_DEFAULT_DELETE_AFTER_MEDIUM)


@inject
async def send_followup_long(
    interaction: discord.Interaction,
    content: str,
    ephemeral: bool = None,
    config: GlobalConfig = Provide["config"],
):
    param = create_message_param(content=content, ephemeral=ephemeral)
    msg = await interaction.followup.send(**param)
    if msg:
        await msg.delete(delay=config.MESSAGE_DEFAULT_DELETE_AFTER_LONG)


def create_message_param(
    content: str,
    embed: Embed = None,
    embeds: list[Embed] = None,
    view: View = None,
    ephemeral: bool = None,
    delete_after: int = None,
    silent: bool = None,
):
    param = {}

    if embeds is None:
        embeds = []
    if embed:
        embeds.append(embed)
    if content:
        param["content"] = content
    if embeds.__len__() > 0:
        param["embeds"] = embeds
    if view:
        param["view"] = view
    if ephemeral:
        param["ephemeral"] = ephemeral
    if delete_after:
        param["delete_after"] = delete_after
    if silent:
        param["silent"] = silent

    return param


@inject
def create_header_embed(
    guild_id: int,
    cb_boss_entry: ClanBattleBossEntries,
    include_image: bool = True,
    default_color: Colour = discord.Color.red(),
    l: Locale = Provide["locale"],
) -> Embed:
    embed = discord.Embed(
        title=f"{cb_boss_entry.boss_name} ({l.t(guild_id, "ui.status.round", round=cb_boss_entry.boss_round)})",
        description=(
            f"# HP : {format_large_number(cb_boss_entry.current_health)} / {format_large_number(cb_boss_entry.max_health)}{NEW_LINE}"
            f"{generate_health_bar(current_health=cb_boss_entry.current_health, max_health=cb_boss_entry.max_health)}"
        ),
        color=default_color,
    )
    if include_image:
        embed.set_image(url=cb_boss_entry.image_path)
    return embed


def create_done_embed(
    guild_id: int,
    list_cb_overall_entry: List[ClanBattleOverallEntry],
    default_color: Colour = discord.Color.green(),
):
    embed = discord.Embed(
        title="",
        description=generate_done_attack_list(guild_id, list_cb_overall_entry),
        color=default_color,
    )
    return embed


def create_book_embed(
    guild_id: int,
    list_boss_cb_player_entries: List[ClanBattleBossBook],
    default_color: Colour = discord.Color.blue(),
):
    embed = discord.Embed(
        title="",
        description=generate_book_list(guild_id, list_boss_cb_player_entries),
        color=default_color,
    )
    return embed


@inject
def generate_done_attack_list(
    guild_id: int, datas: List[ClanBattleOverallEntry], l: Locale = Provide["locale"]
) -> str:
    lines = [
        f"========== {EmojiEnum.DONE.value} {l.t(guild_id, "ui.label.done_list")} =========="
    ]
    for data in datas:
        line = f"{NEW_LINE}{data.attack_type.value} {f"[{format_large_number(data.damage)}] " if data.damage else ''}: {data.player_name}"
        if data.attack_type != AttackTypeEnum.CARRY and not data.leftover_time is None:
            line += f"{NEW_LINE} ┗━ {EmojiEnum.STAR.value} ({data.leftover_time}s)"

        lines.append(line)

    return f"```powershell{NEW_LINE}" + "".join(lines) + "```"


@inject
def generate_book_list(
    guild_id: int, datas: List[ClanBattleBossBook], l: Locale = Provide["locale"]
) -> str:

    lines = [
        f"========== {EmojiEnum.ENTRY.value} {l.t(guild_id, "ui.label.book_list")} =========="
    ]
    for data in datas:
        line = f"{NEW_LINE}{data.attack_type.value}{f"({data.leftover_time}s)" if data.leftover_time else ''} {f"[{format_large_number(data.damage)}] " if data.damage else ''}: {data.player_name}"
        lines.append(line)

    return f"```powershell{NEW_LINE}" + "".join(lines) + "```"


def generate_health_bar(current_health: int, max_health: int):
    max_bar = 10
    green_block = math.floor(current_health / max_health * 10)
    result = f"`"
    for i in range(green_block):
        result += f"{EmojiEnum.GREEN_BLOCK.value}"
    for i in range(max_bar - green_block):
        result += f"{EmojiEnum.RED_BLOCK.value}"
    result += f"`"
    return result


def format_large_number(num):
    if abs(num) >= 1_000_000:
        return f"{num / 1_000_000:,.1f}M"
    elif abs(num) >= 1_000:
        return f"{num / 1_000:,.1f}k"
    else:
        return str(num)


def reduce_int_ab_non_zero(a: int, b: int):
    return max(a - b, 0)


# TL Shifter
def time_to_seconds(time_str: str) -> int:
    match = TL_SHIFTER_TIME_FORMAT.match(time_str)
    if match:
        return int(match[1]) * 60 + int(match[2])
    else:
        return 0


def format_time(seconds: int) -> str:
    """Convert total seconds to MM:SS format."""
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


# DateTime with Timezone
def now():
    return datetime.now(jst)


def utc():
    return datetime.now()


def date_between(date: datetime, from_date: datetime, to_date: datetime) -> bool:
    return from_date <= date.replace(tzinfo=None) <= to_date


# Period thingy
def ordinal(n):
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    return f"{n}{suffix}"


def check_season_status(
    current_date: datetime = None,
) -> dict:
    if current_date is None:
        current_date = datetime.now()

        # Get the end of the current month
    if current_date.month == 12:
        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
    else:
        next_month = current_date.replace(month=current_date.month + 1, day=1)
    end_of_month = next_month - timedelta(days=1)
    end_of_month = end_of_month.replace(hour=0, minute=0, second=0, microsecond=0)

    # Calculate LIVE period dates
    end_minus_5 = end_of_month - timedelta(days=5)
    end_minus_5 = end_minus_5.replace(
        hour=5, minute=0, second=0, microsecond=0
    )  # 05:00
    end_minus_1 = end_of_month - timedelta(days=1)
    end_minus_1 = end_minus_1.replace(
        hour=0, minute=0, second=0, microsecond=0
    )  # 00:00

    # Determine if current date is in LIVE period
    is_live = end_minus_5 <= current_date <= end_minus_1

    # Calculate cycle number
    base_months = ((current_date.year - PURIKONE_LIVE_SERVICE_DATE.year) * 12) + (
        current_date.month - (PURIKONE_LIVE_SERVICE_DATE.month + 1)
    )
    if is_live or current_date.date() == end_of_month.date():
        season_count = base_months + 2
    else:
        season_count = base_months + 1

    # Determine period type and date range
    if is_live:
        period_type = PeriodType.LIVE
        date_from = end_minus_5
        date_to = end_of_month
    else:
        if current_date.date() == end_of_month.date():
            # OFFSEASON: end of current month to end of next month -5
            next_month_end = (
                end_of_month.replace(
                    month=end_of_month.month % 12 + 1,
                    year=end_of_month.year + (1 if end_of_month.month == 12 else 0),
                    day=1,
                )
                + timedelta(days=31)
            ).replace(day=1) - timedelta(days=1)
            next_month_end_minus_5 = next_month_end - timedelta(days=5)
            next_month_end_minus_5 = next_month_end_minus_5.replace(
                hour=5, minute=0, second=0, microsecond=0
            )
            date_from = end_of_month
            date_to = next_month_end_minus_5
        else:
            # OFFSEASON: end of previous month to end of current month -5
            prev_month_end = current_date.replace(day=1) - timedelta(days=1)
            prev_month_end = prev_month_end.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            date_from = prev_month_end
            date_to = end_minus_5
        period_type = PeriodType.OFFSEASON

    # Compute season name
    season_name = f"{ordinal(season_count)} {'Purikone CB' if period_type == PeriodType.LIVE else period_type.value}"

    return {
        "period_type": period_type,
        "date_from": date_from,
        "date_to": date_to,
        "season_name": season_name,
        "season_count": season_count,
    }


def generate_current_cb_period() -> ClanBattlePeriod:
    season_status = check_season_status()

    return ClanBattlePeriod(
        clan_battle_period_name=season_status["season_name"],
        is_active=True,
        date_from=season_status["date_from"],
        date_to=season_status["date_to"],
        period_type=season_status["period_type"],
    )


def generate_random_boss_period(bosses: list[ClanBattleBoss]) -> dict:
    bosses_1 = [boss.clan_battle_boss_id for boss in bosses if boss.position == 1]
    bosses_2 = [boss.clan_battle_boss_id for boss in bosses if boss.position == 2]
    bosses_3 = [boss.clan_battle_boss_id for boss in bosses if boss.position == 3]
    bosses_4 = [boss.clan_battle_boss_id for boss in bosses if boss.position == 4]
    bosses_5 = [boss.clan_battle_boss_id for boss in bosses if boss.position == 5]

    return {
        "boss1_id": random.choice(bosses_1),
        "boss2_id": random.choice(bosses_2),
        "boss3_id": random.choice(bosses_3),
        "boss4_id": random.choice(bosses_4),
        "boss5_id": random.choice(bosses_5),
    }
