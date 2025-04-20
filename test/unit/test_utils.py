import discord
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from discord import TextChannel, Interaction
# Patch all problematic imports before importing the module
with patch.dict('sys.modules', {
    'config': MagicMock(),
    'globals': MagicMock(),
    'enums': MagicMock(),
    'models': MagicMock()
}):
    from utils import discord_try_fetch_message, discord_close_response, send_message, send_message_short, \
    send_message_medium, send_message_long
    from globals import logger

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

    await discord_close_response(mock_interaction)
    log = logger
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    mock_interaction.delete_original_response.assert_awaited_once()
    log.error.assert_not_called()


@pytest.mark.asyncio
async def test_discord_close_response_failure():
    mock_interaction = AsyncMock(spec=Interaction)
    mock_interaction.response.defer = AsyncMock(side_effect=Exception("Test error"))
    mock_interaction.delete_original_response = AsyncMock()

    await discord_close_response(mock_interaction)
    log = logger
    log.error.assert_called()

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
