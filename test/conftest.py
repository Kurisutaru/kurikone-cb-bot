import pytest
from unittest.mock import AsyncMock, MagicMock

from discord import Message, TextChannel, Guild

from logger import KuriLogger

author_id = 1
guild_id = 1
channel_id = 1
message_id = 1


@pytest.fixture
def mock_ctx():
    """Mock Discord context"""
    ctx = AsyncMock(spec=Guild)
    ctx.author.id = author_id
    ctx.guild.id = guild_id
    return ctx


@pytest.fixture
def mock_channel():
    """Standardized mock channel for message tests"""
    channel = AsyncMock(spec=TextChannel)
    channel.id = channel_id
    return channel


@pytest.fixture
def mock_message():
    """Standardized mock message tests"""
    message = AsyncMock(spec=Message)
    message.id = message_id  # Consistent test ID
    return message
