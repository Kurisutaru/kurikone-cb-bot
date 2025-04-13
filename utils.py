import math
import traceback
from typing import List, Optional

import discord
from discord import TextChannel, Colour, Message, Embed
from discord.ui import View

from config import config
from enums import EmojiEnum
from locales import Locale
from logger import KuriLogger
from models import ClanBattleBossEntry, ClanBattleOverallEntry, ClanBattleBossBook
import ui

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

async def send_message(interaction: discord.Interaction, content: str, ephemeral: bool = False, embed: Embed = None,
                             embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view, ephemeral=ephemeral)
    await interaction.response.send_message(**param)

async def send_message_short(interaction: discord.Interaction, content: str, ephemeral: bool = False, embed: Embed = None,
                             embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view, ephemeral=ephemeral,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_SHORT)
    await interaction.response.send_message(**param)


async def send_message_medium(interaction: discord.Interaction, content: str, ephemeral: bool = False, embed: Embed = None, embeds=None,
                              view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view, ephemeral=ephemeral,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_MEDIUM)
    await interaction.response.send_message(**param)


async def send_message_long(interaction: discord.Interaction, content: str, ephemeral: bool = False, embed: Embed = None, embeds=None,
                            view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view, ephemeral=ephemeral,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_LONG)
    await interaction.response.send_message(**param)

async def send_channel_message(interaction: discord.Interaction, content: str, embed: Embed = None,
                                     embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view)
    await interaction.channel.send(**param)

async def send_channel_message_short(interaction: discord.Interaction, content: str, embed: Embed = None,
                                     embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_SHORT)
    await interaction.channel.send(**param)


async def send_channel_message_medium(interaction: discord.Interaction, content: str, embed: Embed = None,
                                      embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_MEDIUM)
    await interaction.channel.send(**param)


async def send_channel_message_long(interaction: discord.Interaction, content: str, embed: Embed = None,
                                    embeds: list[Embed] = None, view: View = None):
    param = create_message_param(content=content, embed=embed, embeds=embeds, view=view,
                                 delete_after=config.MESSAGE_DEFAULT_DELETE_AFTER_LONG)
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
                         ephemeral: bool = None, delete_after: int = None):
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

    return param


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


def create_confirmation_message_view(guild_id: int, yes_emoji: EmojiEnum = EmojiEnum.YES,
                                     no_emoji: EmojiEnum = EmojiEnum.NO, yes_callback=None) -> View:
    yes_btn = ui.ConfirmationOkDoneButton(yes_emoji, l.t(guild_id, "ui.button.yes"))
    no_btn = ui.ConfirmationNoCancelButton(no_emoji, l.t(guild_id, "ui.button.no"))

    if yes_callback:
        yes_btn.callback = yes_callback

    view = View(timeout=None)
    view.add_item(yes_btn)
    view.add_item(no_btn)

    return view


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
