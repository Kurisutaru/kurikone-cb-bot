import math
import random
import traceback
from datetime import datetime, timedelta

from typing import List, Optional

import discord
from discord import TextChannel, Colour, Message, Embed
from discord.ui import View

from config import config
from enums import EmojiEnum, AttackTypeEnum, PeriodType
from globals import NEW_LINE, locale, logger, jst, PURIKONE_LIVE_SERVICE_DATE

from models import ClanBattleBossEntry, ClanBattleOverallEntry, ClanBattleBossBook, ClanBattleBoss, ClanBattlePeriod

l = locale
log = logger


### DISCORD STUFF UTILS

async def discord_try_fetch_message(channel: TextChannel, message_id: int) -> Optional[Message]:
    try:
        return await channel.fetch_message(message_id)
    except discord.NotFound:
        return None


async def discord_close_response(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
        await interaction.delete_original_response()
    except Exception as e:
        log.error(e)

async def send_message(interaction: discord.Interaction, content: str, ephemeral: bool = False, silent: bool = None, embed: Embed = None,
                             embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view, ephemeral=ephemeral, silent=silent)
    await interaction.response.send_message(**param)

async def send_message_short(interaction: discord.Interaction, content: str, ephemeral: bool = False, silent: bool = None, embed: Embed = None,
                             embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view, ephemeral=ephemeral, silent=silent,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_SHORT)
    await interaction.response.send_message(**param)


async def send_message_medium(interaction: discord.Interaction, content: str, ephemeral: bool = False, silent: bool = None, embed: Embed = None, embeds=None,
                              view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view, ephemeral=ephemeral, silent=silent,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_MEDIUM)
    await interaction.response.send_message(**param)


async def send_message_long(interaction: discord.Interaction, content: str, ephemeral: bool = False, silent: bool = None, embed: Embed = None, embeds=None,
                            view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view, ephemeral=ephemeral, silent=silent,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_LONG)
    await interaction.response.send_message(**param)

async def send_channel_message(interaction: discord.Interaction, content: str, silent: bool = None, embed: Embed = None,
                                     embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view, silent=silent)
    await interaction.channel.send(**param)

async def send_channel_message_short(interaction: discord.Interaction, content: str, silent: bool = None, embed: Embed = None,
                                     embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_SHORT, silent=silent)
    await interaction.channel.send(**param)


async def send_channel_message_medium(interaction: discord.Interaction, content: str, silent: bool = None, embed: Embed = None,
                                      embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_MEDIUM, silent=silent)
    await interaction.channel.send(**param)


async def send_channel_message_long(interaction: discord.Interaction, content: str, silent: bool = None, embed: Embed = None,
                                    embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_LONG, silent=silent)
    await interaction.channel.send(**param)


async def send_followup_short(interaction: discord.Interaction, content: str, ephemeral: bool = None):
    param = create_message_param(content=content, ephemeral=ephemeral)
    msg = await interaction.followup.send(**param)
    if msg:
        await msg.delete(delay=config.MESSAGE_DEFAULT_DELETE_AFTER_SHORT)


async def send_followup_medium(interaction: discord.Interaction, content: str, ephemeral: bool = None):
    param = create_message_param(content=content, ephemeral=ephemeral)
    msg = await interaction.followup.send(**param)
    if msg:
        await msg.delete(delay=config.MESSAGE_DEFAULT_DELETE_AFTER_MEDIUM)


async def send_followup_long(interaction: discord.Interaction, content: str, ephemeral: bool = None):
    param = create_message_param(content=content, ephemeral=ephemeral)
    msg = await interaction.followup.send(**param)
    if msg:
        await msg.delete(delay=config.MESSAGE_DEFAULT_DELETE_AFTER_LONG)


def create_message_param(content: str, embed: Embed = None, embeds: list[Embed] = None, view: View = None,
                         ephemeral: bool = None, delete_after: int = None, silent: bool = None):
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


def create_header_embed(guild_id: int, cb_boss_entry: ClanBattleBossEntry, include_image: bool = True,
                        default_color: Colour = discord.Color.red()):
    embed = discord.Embed(
        title=f"{cb_boss_entry.name} ({l.t(guild_id, "ui.status.round", round=cb_boss_entry.boss_round)})",
        description=(
            f"# HP : {format_large_number(cb_boss_entry.current_health)} / {format_large_number(cb_boss_entry.max_health)}{NEW_LINE}"
            f"{generate_health_bar(current_health=cb_boss_entry.current_health, max_health=cb_boss_entry.max_health)}"
            ),
        color=default_color
    )
    if include_image:
        embed.set_image(url=cb_boss_entry.image_path)
    return embed


def create_done_embed(guild_id: int, list_cb_overall_entry: List[ClanBattleOverallEntry],
                      default_color: Colour = discord.Color.green()):
    embed = discord.Embed(
        title="",
        description=generate_done_attack_list(guild_id, list_cb_overall_entry),
        color=default_color,
    )
    return embed


def create_book_embed(guild_id: int, list_boss_cb_player_entries: List[ClanBattleBossBook],
                      default_color: Colour = discord.Color.blue()):
    embed = discord.Embed(
        title="",
        description=generate_book_list(guild_id, list_boss_cb_player_entries),
        color=default_color,
    )
    return embed


def generate_done_attack_list(guild_id: int, datas: List[ClanBattleOverallEntry]) -> str:
    lines = [f"========== {EmojiEnum.DONE.value} {l.t(guild_id, "ui.label.done_list")} =========="]
    for data in datas:
        line = f"{NEW_LINE}{data.attack_type.value} {f"[{format_large_number(data.damage)}] " if data.damage else ''}: {data.player_name}"
        if data.attack_type == AttackTypeEnum.CARRY or data.leftover_time:
            line += f"{NEW_LINE} ┗━ {EmojiEnum.STAR.value} ({data.leftover_time if data.leftover_time else 0 }s)"

        lines.append(line)

    return f"```powershell{NEW_LINE}" + "".join(lines) + "```"


def generate_book_list(guild_id: int, datas: List[ClanBattleBossBook]) -> str:
    lines = [f"========== {EmojiEnum.ENTRY.value} {l.t(guild_id, "ui.label.book_list")} =========="]
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
    """Convert time string (MM:SS or SS) to total seconds."""
    if ':' in time_str:
        m, s = map(int, time_str.split(':', 1))
        return m * 60 + s
    return int(time_str)


def format_time(seconds: int) -> str:
    """Convert total seconds to MM:SS format."""
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


# DateTime with Timezone
def now():
    return datetime.now(jst)

def utc():
    return datetime.now()


# Period thingy
def calc_cb_num():
    cur_date = now()
    count = ((cur_date.year - PURIKONE_LIVE_SERVICE_DATE.year) * 12) + (cur_date.month - PURIKONE_LIVE_SERVICE_DATE.month)
    return abs(count - 1)

def ordinal(n):
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return f"{n}{suffix}"


def check_season_status(current_date=None):
    if current_date is None:
        current_date = now()

    # Get the end of current month
    if current_date.month == 12:
        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
    else:
        next_month = current_date.replace(month=current_date.month + 1, day=1)

    end_of_month = next_month - timedelta(days=1)
    end_of_month = end_of_month.replace(hour=0, minute=0, second=0, microsecond=0)

    # Calculate important dates
    end_minus_5 = end_of_month - timedelta(days=5)
    end_minus_5 = end_minus_5.replace(hour=5, minute=0, second=0, microsecond=0)  # Set to 05:00

    end_minus_1 = end_of_month - timedelta(days=1)
    end_minus_1 = end_minus_1.replace(hour=0, minute=0, second=0, microsecond=0)  # Set to 00:00

    # Check if current date is in LIVE period
    if end_minus_5 <= current_date <= end_minus_1:
        return {
            "period_type": PeriodType.LIVE,
            "date_from": end_minus_5,
            "date_to": end_of_month
        }
    else:
        # For OFFSEASON, we need dates from previous month's end-1 to current month's end-5
        prev_month_end = (current_date.replace(day=1) - timedelta(days=1))
        prev_month_end = prev_month_end.replace(hour=0, minute=0, second=0, microsecond=0)

        prev_month_end_minus_1 = prev_month_end - timedelta(days=1)
        prev_month_end_minus_1 = prev_month_end_minus_1.replace(hour=0, minute=0, second=0, microsecond=0)

        current_month_end_minus_5 = end_of_month - timedelta(days=5)
        current_month_end_minus_5 = current_month_end_minus_5.replace(hour=5, minute=0, second=0, microsecond=0)

        return {
            "period_type": PeriodType.OFFSEASON,
            "date_from": prev_month_end_minus_1,
            "date_to": current_month_end_minus_5
        }

def generate_current_cb_period() -> ClanBattlePeriod:
    season_status = check_season_status()

    return ClanBattlePeriod(
        clan_battle_period_name=f"{ordinal(calc_cb_num())} {"Purikone CB" if season_status['period_type'] == PeriodType.LIVE else season_status['period_type'].value}",
        is_active = True,
        **season_status
    )


def generate_random_boss_period(bosses: list[ClanBattleBoss]) -> dict:
    bosses_1 = [boss.clan_battle_boss_id for boss in bosses if boss.position == 1]
    bosses_2 = [boss.clan_battle_boss_id for boss in bosses if boss.position == 2]
    bosses_3 = [boss.clan_battle_boss_id for boss in bosses if boss.position == 3]
    bosses_4 = [boss.clan_battle_boss_id for boss in bosses if boss.position == 4]
    bosses_5 = [boss.clan_battle_boss_id for boss in bosses if boss.position == 5]

    return {
        "boss1_id" : random.choice(bosses_1),
        "boss2_id" : random.choice(bosses_2),
        "boss3_id" : random.choice(bosses_3),
        "boss4_id" : random.choice(bosses_4),
        "boss5_id" : random.choice(bosses_5),
    }
