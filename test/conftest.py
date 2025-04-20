import pytest
from unittest.mock import AsyncMock

author_id = 1
guild_id = 1
channel_id = 1
message_id = 1

@pytest.fixture
def mock_ctx():
    """Mock Discord context"""
    ctx = AsyncMock()
    ctx.author.id = author_id
    ctx.guild.id = guild_id
    return ctx

@pytest.fixture
def mock_channel():
    """Standardized mock channel for message tests"""
    channel = AsyncMock()
    channel.id = channel_id
    return channel

@pytest.fixture
def mock_message():
    """Standardized mock message tests"""
    message = AsyncMock()
    message.id = message_id  # Consistent test ID
    return message