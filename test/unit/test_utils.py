import discord
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from discord import TextChannel, Interaction, Embed
from discord.ui import View

# Patch all problematic imports before importing the module
with patch.dict(
    "sys.modules",
    {
        "config": MagicMock(),
        "globals": MagicMock(),
        "enums": MagicMock(),
        "models": MagicMock(),
    },
):
    import utils
    from utils import (
        discord_try_fetch_message,
        discord_close_response,
        send_message,
        send_message_short,
        send_message_medium,
        send_message_long,
        create_message_param,
        send_channel_message,
        send_channel_message_medium,
        send_channel_message_long,
        send_channel_message_short,
        send_followup_short,
        send_followup_medium,
        send_followup_long,
    )


@pytest.mark.asyncio
async def test_discord_try_fetch_message_success():
    mock_channel = AsyncMock()
    mock_message = AsyncMock()
    mock_channel.fetch_message.return_value = mock_message

    result = await discord_try_fetch_message(mock_channel, 123)

    mock_channel.fetch_message.assert_awaited_once_with(123)
    assert result == mock_message


@pytest.mark.asyncio
async def test_discord_try_fetch_message_not_found():
    mock_channel = AsyncMock(spec=TextChannel)
    mock_channel.fetch_message.side_effect = discord.NotFound(AsyncMock(), AsyncMock())

    result = await discord_try_fetch_message(mock_channel, 99999)

    assert result is None


@pytest.mark.asyncio
async def test_discord_close_response_success():
    mock_interaction = AsyncMock(spec=Interaction)
    mock_interaction.response.defer = AsyncMock()
    mock_interaction.delete_original_response = AsyncMock()

    utils.log = AsyncMock()

    await discord_close_response(mock_interaction)
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    mock_interaction.delete_original_response.assert_awaited_once()
    utils.log.error.assert_not_called()


@pytest.mark.asyncio
async def test_discord_close_response_failure():
    mock_interaction = AsyncMock(spec=Interaction)
    mock_interaction.response.defer = AsyncMock(side_effect=Exception("Test error"))
    mock_interaction.delete_original_response = AsyncMock()

    utils.log = AsyncMock()

    await discord_close_response(mock_interaction)
    utils.log.error.assert_called_once()
    mock_interaction.delete_original_response.assert_not_awaited()


@pytest.mark.asyncio
async def test_discord_send_messages():
    mock_interaction = AsyncMock(spec=Interaction)
    mock_interaction.response.send_message = AsyncMock()

    await send_message(mock_interaction, "", False, None, None, None, None)
    mock_interaction.response.send_message.assert_called()

    await send_message_short(mock_interaction, "", False, None, None, None, None)
    mock_interaction.response.send_message.assert_called()

    await send_message_medium(mock_interaction, "", False, None, None, None, None)
    mock_interaction.response.send_message.assert_called()

    await send_message_long(mock_interaction, "", False, None, None, None, None)
    mock_interaction.response.send_message.assert_called()


@pytest.mark.asyncio
async def test_discord_send_channel_messages():
    mock_interaction = AsyncMock(spec=Interaction)
    mock_interaction.channel.send = AsyncMock()

    await send_channel_message(mock_interaction, "", False, None, None, None)
    mock_interaction.channel.send.assert_called()

    await send_channel_message_short(mock_interaction, "", False, None, None, None)
    mock_interaction.channel.send.assert_called()

    await send_channel_message_medium(mock_interaction, "", False, None, None, None)
    mock_interaction.channel.send.assert_called()

    await send_channel_message_long(mock_interaction, "", False, None, None, None)
    mock_interaction.channel.send.assert_called()


@pytest.mark.asyncio
async def test_discord_send_followup_messages(mock_message):
    mock_interaction = AsyncMock(spec=Interaction)
    mock_interaction.followup.send = AsyncMock()
    mock_interaction.followup.send.return_value = mock_message

    await send_followup_short(mock_interaction, "", False)
    mock_interaction.followup.send.assert_called()

    await send_followup_medium(mock_interaction, "", False)
    mock_interaction.followup.send.assert_called()

    await send_followup_long(mock_interaction, "", False)
    mock_interaction.followup.send.assert_called()


def test_create_message_param():
    mock_embed = MagicMock(Embed)
    mock_embeds = MagicMock(list[Embed])
    mock_embeds.__len__.return_value = 1
    mock_view = MagicMock(View)

    param = create_message_param(content="123")
    assert param["content"] == "123"

    param = create_message_param(content="123", ephemeral=True)
    assert param["ephemeral"] is True

    param = create_message_param(content="123", embed=mock_embed)
    assert param["embeds"] is not None

    param = create_message_param(content="123", embeds=mock_embeds)
    assert param["embeds"] is not None

    param = create_message_param(content="123", view=mock_view)
    assert param["view"] is not None

    param = create_message_param(content="123", delete_after=1)
    assert param["delete_after"] == 1

    param = create_message_param(content="123", silent=True)
    assert param["silent"] is True
