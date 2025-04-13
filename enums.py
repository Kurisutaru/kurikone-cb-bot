# Enum
from enum import Enum
from typing import Literal

import discord
from discord import app_commands

from config import config

NEW_LINE = "\n"

class ChannelEnum(Enum):
    CATEGORY = {"type": "CATEGORY", "name": config.CATEGORY_CHANNEL_NAME}
    REPORT = {"type": "REPORT", "name": config.REPORT_CHANNEL_NAME}
    BOSS1 = {"type": "BOSS1", "name": config.BOSS1_CHANNEL_NAME}
    BOSS2 = {"type": "BOSS2", "name": config.BOSS2_CHANNEL_NAME}
    BOSS3 = {"type": "BOSS3", "name": config.BOSS3_CHANNEL_NAME}
    BOSS4 = {"type": "BOSS4", "name": config.BOSS4_CHANNEL_NAME}
    BOSS5 = {"type": "BOSS5", "name": config.BOSS5_CHANNEL_NAME}
    TL_SHIFTER = {"type": "TL_SHIFTER", "name": config.TL_SHIFTER_CHANNEL_NAME}


class AttackTypeEnum(Enum):
    PATK = "🥊"
    MATK = "📘"
    CARRY = "💼"
    LEFTOVER = "🎯"


# Enums for better readability
class EmojiEnum(Enum):
    PATK = "🥊"
    MATK = "📘"
    CARRY = "💼"
    CANCEL = "⛔"
    DONE = "✅"
    BOOK = "⚔️"
    ENTRY = "📝"
    FINISH = "🏁"
    STAR = "🌟"
    YES = "✔"
    NO = "❌"
    GREEN_BLOCK = "🟩"
    RED_BLOCK = "🟥"


class ButtonStyle:
    PRIMARY = discord.ButtonStyle.primary
    GREEN = discord.ButtonStyle.green
    RED = discord.ButtonStyle.red
    BLURPLE = discord.ButtonStyle.blurple


class HelpTopic:
    # Static key-value pairs declared inside the class
    DATA = {
        "cb-report-symbol": (
            f"# Clan Battle Report Symbol{NEW_LINE}"
            f"```powershell{NEW_LINE}"
            f"{AttackTypeEnum.PATK.value} : Physical Attack{NEW_LINE}"
            f"{AttackTypeEnum.MATK.value} : Magical Attack{NEW_LINE}"
            f"{AttackTypeEnum.CARRY.value} : Leftover Entries{NEW_LINE}"
            f"{AttackTypeEnum.LEFTOVER.value} : Active Leftover Entries{NEW_LINE}"
            f"```"
        ),
        "bot": "Hello, Kurisutaru here from the Bot creator",
    }

    @classmethod
    def get_keys(cls):
        """Get just the keys as strings"""
        return Literal[*cls.DATA.keys()]

    @classmethod
    def get_value(cls, key: str) -> str:
        """Get the response text for a given key"""
        return cls.DATA.get(key, "Topic not found")