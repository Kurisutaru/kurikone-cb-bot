import math
import traceback
from typing import List, Optional

import discord
from discord import TextChannel, Colour, Message

from config import config
from enums import EmojiEnum
from locales import Locale
from logger import KuriLogger
from models import ClanBattleBossEntry, ClanBattleOverallEntry, ClanBattleBossBook
from ui import ButtonView

NEW_LINE = "\n"

logger = KuriLogger()
l = Locale()

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
        logger.error(e)
        logger.error(traceback.print_exc())


async def discord_resp_send_msg(interaction: discord.Interaction, message: str, ephemeral: bool = True,
                                delete_after=None):
    if delete_after is None:
        delete_after = config.MESSAGE_DEFAULT_DELETE_AFTER_SHORT

    await interaction.response.send_message(content=message, ephemeral=ephemeral,
                                            delete_after=delete_after)  # type: ignore


def create_header_embed(guild_id: int, cb_boss_entry: ClanBattleBossEntry, include_image: bool = True,
                        default_color: Colour = discord.Color.red()):
    embed = discord.Embed(
        title=f"{cb_boss_entry.name} ({l.t(guild_id, "ui.status.round", round=cb_boss_entry.boss_round)})",
        description=f"""# HP : {format_large_number(cb_boss_entry.current_health)} / {format_large_number(cb_boss_entry.max_health)}{NEW_LINE}
                        {generate_health_bar(current_health=cb_boss_entry.current_health, max_health=cb_boss_entry.max_health)}
                        """,
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

def get_button_view(guild_id:int) -> ButtonView:
    return ButtonView(guild_id)

def generate_done_attack_list(guild_id: int, datas: List[ClanBattleOverallEntry]) -> str:
    lines = [f"========== {EmojiEnum.DONE.value} {l.t(guild_id, "ui.label.done_list")} =========="]
    for data in datas:
        line = f"{NEW_LINE}{data.attack_type.value} {f"[{format_large_number(data.damage)}] " if data.damage else ''}: {data.player_name}"
        if data.leftover_time:
            line += f"{NEW_LINE} ┗━ {EmojiEnum.STAR.value} ({data.leftover_time}s)"

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
