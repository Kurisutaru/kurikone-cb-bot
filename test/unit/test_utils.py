from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import discord
import pytest
from dependency_injector import providers
from discord import TextChannel, Interaction, Embed
from discord.ui import View
from freezegun import freeze_time

from enums import EmojiEnum, PeriodType, AttackTypeEnum
from locales import Locale
from logger import KuriLogger
from models import (
    ClanBattleBossEntry,
    ClanBattleBoss,
    ClanBattleOverallEntry,
    ClanBattleBossBook,
    ClanBattleBossEntries,
)

# Patch all problematic imports before importing the module
with patch.dict(
    "sys.modules",
    {
        "config": MagicMock(),
        "logger": MagicMock(),
        "locales": MagicMock(),
    },
):
    import utils


@pytest.mark.asyncio
async def test_discord_try_fetch_message_success():
    mock_channel = AsyncMock()
    mock_message = AsyncMock()
    mock_channel.fetch_message.return_value = mock_message

    result = await utils.discord_try_fetch_message(mock_channel, 123)

    mock_channel.fetch_message.assert_awaited_once_with(123)
    assert result == mock_message


@pytest.mark.asyncio
async def test_discord_try_fetch_message_not_found():
    mock_channel = AsyncMock(spec=TextChannel)
    mock_channel.fetch_message.side_effect = discord.NotFound(AsyncMock(), AsyncMock())

    result = await utils.discord_try_fetch_message(mock_channel, 99999)

    assert result is None


@pytest.mark.asyncio
async def test_discord_close_response_success(mock_container):
    mock_interaction = AsyncMock(spec=Interaction)
    mock_interaction.response.defer = AsyncMock()
    mock_interaction.delete_original_response = AsyncMock()

    mock_logger = MagicMock()
    mock_container.logger.override(providers.Object(mock_logger))

    await utils.discord_close_response(mock_interaction)
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    mock_interaction.delete_original_response.assert_awaited_once()
    mock_logger.error.assert_not_called()


@pytest.mark.asyncio
async def test_discord_close_response_failure(mock_container):
    mock_interaction = AsyncMock(spec=Interaction)
    mock_interaction.response.defer = AsyncMock(side_effect=Exception("Test error"))
    mock_interaction.delete_original_response = AsyncMock()

    mock_logger = MagicMock(spec=KuriLogger)
    mock_container.logger.override(providers.Object(mock_logger))

    await utils.discord_close_response(mock_interaction)
    mock_logger.error.assert_called()
    mock_interaction.delete_original_response.assert_not_awaited()


@pytest.mark.asyncio
async def test_discord_send_messages(mock_container):
    mock_interaction = AsyncMock(spec=Interaction)
    mock_interaction.response.send_message = AsyncMock()

    await utils.send_message(mock_interaction, "", False, None, None, None, None)
    mock_interaction.response.send_message.assert_called()

    await utils.send_message_short(mock_interaction, "", False, None, None, None, None)
    mock_interaction.response.send_message.assert_called()

    await utils.send_message_medium(mock_interaction, "", False, None, None, None, None)
    mock_interaction.response.send_message.assert_called()

    await utils.send_message_long(mock_interaction, "", False, None, None, None, None)
    mock_interaction.response.send_message.assert_called()


@pytest.mark.asyncio
async def test_discord_send_channel_messages(mock_container):
    mock_interaction = AsyncMock(spec=Interaction)
    mock_interaction.channel.send = AsyncMock()

    mock_config = MagicMock()
    mock_container.config.override(mock_config)

    await utils.send_channel_message(mock_interaction, "", False, None, None, None)
    mock_interaction.channel.send.assert_called()

    await utils.send_channel_message_short(
        mock_interaction, "", False, None, None, None
    )
    mock_interaction.channel.send.assert_called()

    await utils.send_channel_message_medium(
        mock_interaction, "", False, None, None, None
    )
    mock_interaction.channel.send.assert_called()

    await utils.send_channel_message_long(mock_interaction, "", False, None, None, None)
    mock_interaction.channel.send.assert_called()


@pytest.mark.asyncio
async def test_discord_send_followup_messages(mock_container, mock_message):
    mock_interaction = AsyncMock(spec=Interaction)
    mock_interaction.followup.send = AsyncMock()
    mock_interaction.followup.send.return_value = mock_message

    await utils.send_followup_short(mock_interaction, "", False)
    mock_interaction.followup.send.assert_called()

    await utils.send_followup_medium(mock_interaction, "", False)
    mock_interaction.followup.send.assert_called()

    await utils.send_followup_long(mock_interaction, "", False)
    mock_interaction.followup.send.assert_called()


def test_create_message_param():
    mock_embed = MagicMock(Embed)
    mock_embeds = MagicMock(list[Embed])
    mock_embeds.__len__.return_value = 1
    mock_view = MagicMock(View)

    param = utils.create_message_param(content="123")
    assert param["content"] == "123"

    param = utils.create_message_param(content="123", ephemeral=True)
    assert param["ephemeral"] is True

    param = utils.create_message_param(content="123", embed=mock_embed)
    assert param["embeds"] is not None

    param = utils.create_message_param(content="123", embeds=mock_embeds)
    assert param["embeds"] is not None

    param = utils.create_message_param(content="123", view=mock_view)
    assert param["view"] is not None

    param = utils.create_message_param(content="123", delete_after=1)
    assert param["delete_after"] == 1

    param = utils.create_message_param(content="123", silent=True)
    assert param["silent"] is True


def test_create_header_embed(mock_container):

    mock_container.locale.override(MagicMock(spec=Locale))

    mock_clan_battle_boss_entry = ClanBattleBossEntries(
        guild_id=1,
        clan_battle_boss_entry_id=1,
        clan_battle_period_id=1,
        clan_battle_boss_id=1,
        boss_name="Boss",
        image_path="Image",
        boss_round=1,
        current_health=1,
        max_health=10,
    )

    embed = utils.create_header_embed(
        1,
        mock_clan_battle_boss_entry,
        True,
    )

    assert embed is not None


def test_generate_health_bar():

    cur_health = 1
    max_health = 10

    result = utils.generate_health_bar(cur_health, max_health)

    assert (
        result
        == "`"
        + f"{EmojiEnum.GREEN_BLOCK.value}" * cur_health
        + f"{EmojiEnum.RED_BLOCK.value}" * (max_health - cur_health)
        + "`"
    )

    cur_health = 5
    max_health = 10

    result = utils.generate_health_bar(cur_health, max_health)

    assert (
        result
        == "`"
        + f"{EmojiEnum.GREEN_BLOCK.value}" * cur_health
        + f"{EmojiEnum.RED_BLOCK.value}" * (max_health - cur_health)
        + "`"
    )


def test_format_large_number():
    assert utils.format_large_number(123456789) == "123.5M"
    assert utils.format_large_number(123456) == "123.5k"
    assert utils.format_large_number(123) == "123"


def test_reduce_int_ab_non_zero():
    assert utils.reduce_int_ab_non_zero(1, 3) == 0
    assert utils.reduce_int_ab_non_zero(3, 1) == 2


@freeze_time("2022-01-01 12:00:00+09:00")
def test_now():
    with patch.dict(
        "sys.modules",
        {
            "config": MagicMock(),
            "logger": MagicMock(),
            "locales": MagicMock(),
        },
    ):
        from utils import now
        from globals import jst
    assert now() == jst.localize(datetime(2022, 1, 1, 12, 0))


@freeze_time("2022-01-01 12:00:00+00:00")
def test_utc():
    with patch.dict(
        "sys.modules",
        {
            "config": MagicMock(),
            "logger": MagicMock(),
            "locales": MagicMock(),
        },
    ):
        from utils import utc
    assert utc() == datetime(2022, 1, 1, 12, 0)


def test_time_to_seconds():
    assert utils.time_to_seconds("123:456:789") == 0
    assert utils.time_to_seconds("123:456") == 0
    assert utils.time_to_seconds("123:45") == 0
    assert utils.time_to_seconds("12:34") == 754
    assert utils.time_to_seconds("1:23") == 83
    assert utils.time_to_seconds("1:2") == 62
    assert utils.time_to_seconds("0:2") == 2
    assert utils.time_to_seconds("0:0") == 0


def test_format_time():
    assert utils.format_time(60) == "1:00"
    assert utils.format_time(90) == "1:30"
    assert utils.format_time(30) == "0:30"
    assert utils.format_time(0) == "0:00"


@freeze_time("2022-01-01 12:00:00+00:00")
def test_calc_cb_num():
    with patch.dict(
        "sys.modules",
        {
            "config": MagicMock(),
            "logger": MagicMock(),
            "locales": MagicMock(),
        },
    ):
        from utils import calc_cb_num
    assert calc_cb_num() == 46


def test_ordinal():
    assert utils.ordinal(1) == "1st"
    assert utils.ordinal(2) == "2nd"
    assert utils.ordinal(3) == "3rd"
    assert utils.ordinal(4) == "4th"
    assert utils.ordinal(11) == "11th"
    assert utils.ordinal(21) == "21st"
    assert utils.ordinal(31) == "31st"


@freeze_time("2022-01-01 12:00:00+00:00")
def test_check_season_status():
    with patch.dict(
        "sys.modules",
        {
            "config": MagicMock(),
            "logger": MagicMock(),
            "locales": MagicMock(),
        },
    ):
        from utils import check_season_status
    current = check_season_status()
    assert current["period_type"] == PeriodType.OFFSEASON
    current = check_season_status(datetime(2025, 3, 26, hour=5))
    assert current["period_type"] == PeriodType.LIVE
    current = check_season_status(datetime(2025, 3, 26))
    assert current["period_type"] == PeriodType.OFFSEASON
    current = check_season_status(datetime(2025, 3, 31, hour=5))
    assert current["period_type"] == PeriodType.OFFSEASON


@freeze_time("2022-12-01 12:00:00+00:00")
def test_generate_current_cb_period():
    with patch.dict(
        "sys.modules",
        {
            "config": MagicMock(),
            "logger": MagicMock(),
            "locales": MagicMock(),
        },
    ):
        from utils import generate_current_cb_period

    gen = generate_current_cb_period()

    assert gen.period_type == PeriodType.OFFSEASON


def test_generate_random_boss_period():

    boss1 = ClanBattleBoss(
        clan_battle_boss_id=1,
        name="boss1",
        description="boss1",
        image_path="boss1",
        position=1,
    )

    boss2 = ClanBattleBoss(
        clan_battle_boss_id=2,
        name="boss2",
        description="boss2",
        image_path="boss2",
        position=2,
    )

    boss3 = ClanBattleBoss(
        clan_battle_boss_id=3,
        name="boss1",
        description="boss1",
        image_path="boss1",
        position=3,
    )

    boss4 = ClanBattleBoss(
        clan_battle_boss_id=4,
        name="boss1",
        description="boss1",
        image_path="boss1",
        position=4,
    )

    boss5 = ClanBattleBoss(
        clan_battle_boss_id=5,
        name="boss1",
        description="boss1",
        image_path="boss1",
        position=5,
    )

    bosses = [boss1, boss2, boss3, boss4, boss5]

    random = utils.generate_random_boss_period(bosses)

    assert random["boss1_id"] == 1
    assert random["boss2_id"] == 2
    assert random["boss3_id"] == 3
    assert random["boss4_id"] == 4
    assert random["boss5_id"] == 5


def test_create_done_embed(mock_container):

    mock_container.locale.override(MagicMock(spec=Locale))

    list_cb_overall_entry = [
        ClanBattleOverallEntry(
            clan_battle_overall_entry_id=1,
            guild_id=1,
            clan_battle_period_id=1,
            clan_battle_boss_id=1,
            player_id=1,
            player_name="Test",
            boss_round=1,
            attack_type=AttackTypeEnum.PATK,
            damage=1,
            leftover_time=1,
            overall_leftover_entry_id=1,
            entry_date=utils.now(),
        )
    ]

    embeds = utils.create_done_embed(1, list_cb_overall_entry)
    assert embeds is not None

    embeds = utils.create_done_embed(1, list_cb_overall_entry, discord.Color.random())
    assert embeds is not None


def test_create_book_embed(mock_container):
    mock_container.locale.override(MagicMock(spec=Locale))

    list_boss_cb_player_entries = [
        ClanBattleBossBook(
            clan_battle_overall_entry_id=1,
            guild_id=1,
            player_id=1,
            player_name="Test",
            attack_type=AttackTypeEnum.PATK,
            damage=1,
            leftover_time=1,
            entry_date=utils.now(),
        )
    ]
    embeds = utils.create_book_embed(1, list_boss_cb_player_entries)
    assert embeds is not None

    embeds = utils.create_book_embed(
        1, list_boss_cb_player_entries, discord.Color.random()
    )
    assert embeds is not None


def test_date_between():
    assert (
        utils.date_between(
            datetime(2025, 4, 15), datetime(2025, 4, 1), datetime(2025, 4, 30)
        )
        == True
    )
    assert (
        utils.date_between(
            datetime(2025, 3, 1), datetime(2025, 4, 1), datetime(2025, 4, 30)
        )
        == False
    )
    assert (
        utils.date_between(
            datetime(2025, 5, 1), datetime(2025, 4, 1), datetime(2025, 4, 30)
        )
        == False
    )
