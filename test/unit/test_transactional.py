from unittest import result
from unittest.mock import Mock

import pytest

from database import (
    db_connection_context,
    rollback_flag_context,
    reset_connection_context,
)
from transactional import transactional, transaction_rollback, transaction_reset


# Fixture to mock database connection
@pytest.fixture
def mock_db_connection(mocker):
    conn = Mock()
    conn.autocommit = True  # Initial state
    conn.begin = Mock()
    conn.commit = Mock()
    conn.rollback = Mock()
    conn.close = Mock()
    mocker.patch("transactional.get_connection", return_value=(conn, True))
    return conn


# Fixture to reset contexts before each test
@pytest.fixture(autouse=True)
def reset_contexts():
    db_connection_context.set(None)
    rollback_flag_context.set(False)
    yield
    db_connection_context.set(None)
    rollback_flag_context.set(False)
    reset_connection_context()


# Test synchronous wrapper - successful transaction
def test_transactional_sync_success(mock_db_connection):
    @transactional
    def my_function():
        return "success"

    result = my_function()

    assert result == "success"
    mock_db_connection.begin.assert_called_once()
    mock_db_connection.commit.assert_called_once()
    mock_db_connection.rollback.assert_not_called()
    mock_db_connection.close.assert_called_once()
    assert db_connection_context.get() is None
    assert rollback_flag_context.get() is False


# Test synchronous wrapper - rollback on exception
def test_transactional_sync_exception(mock_db_connection):
    @transactional
    def my_function():
        raise ValueError("error")

    with pytest.raises(ValueError):
        my_function()

    mock_db_connection.begin.assert_called_once()
    mock_db_connection.commit.assert_not_called()
    mock_db_connection.rollback.assert_called_once()
    mock_db_connection.close.assert_called_once()
    assert db_connection_context.get() is None


# Test synchronous wrapper - rollback flag
def test_transactional_sync_rollback_flag(mock_db_connection):
    @transactional
    def my_function():
        transaction_rollback()
        return "success"

    result = my_function()

    assert result == "success"
    mock_db_connection.begin.assert_called_once()
    mock_db_connection.commit.assert_not_called()
    mock_db_connection.rollback.assert_called_once()
    mock_db_connection.close.assert_called_once()


# Test synchronous wrapper - nested transaction
def test_transactional_sync_nested(mock_db_connection, mocker):
    mocker.patch(
        "transactional.get_connection", return_value=(mock_db_connection, False)
    )

    @transactional
    def outer_function():
        return inner_function()

    @transactional
    def inner_function():
        return "nested"

    # Simulate existing connection
    db_connection_context.set(mock_db_connection)

    result = outer_function()

    assert result == "nested"
    mock_db_connection.begin.assert_not_called()  # No new transaction
    mock_db_connection.commit.assert_not_called()
    mock_db_connection.rollback.assert_not_called()
    mock_db_connection.close.assert_not_called()  # Connection not closed in nested
    assert db_connection_context.get() == mock_db_connection


# Test asynchronous wrapper - successful transaction
@pytest.mark.asyncio
async def test_transactional_async_success(mock_db_connection):
    @transactional
    async def my_async_function():
        return "success"

    result = await my_async_function()

    assert result == "success"
    mock_db_connection.begin.assert_called_once()
    mock_db_connection.commit.assert_called_once()
    mock_db_connection.rollback.assert_not_called()
    mock_db_connection.close.assert_called_once()
    assert db_connection_context.get() is None


# Test asynchronous wrapper - rollback on exception
@pytest.mark.asyncio
async def test_transactional_async_exception(mock_db_connection):
    @transactional
    async def my_async_function():
        raise ValueError("error")

    with pytest.raises(ValueError):
        await my_async_function()

    mock_db_connection.begin.assert_called_once()
    mock_db_connection.commit.assert_not_called()
    mock_db_connection.rollback.assert_called_once()
    mock_db_connection.close.assert_called_once()


# Test asynchronous wrapper - rollback on demand
@pytest.mark.asyncio
async def test_transactional_async_transaction_rollback(mock_db_connection):
    @transactional
    async def my_async_function():
        transaction_rollback()
        return "success"

    result = await my_async_function()

    assert result == "success"
    mock_db_connection.begin.assert_called_once()
    mock_db_connection.commit.assert_not_called()
    mock_db_connection.rollback.assert_called_once()
    mock_db_connection.close.assert_called_once()


# Test asynchronous wrapper - reset on demand
@pytest.mark.asyncio
async def test_transactional_async_transaction_reset(mock_db_connection):
    @transactional
    async def my_async_function():
        transaction_reset()
        return "success"

    result = await my_async_function()

    assert result == "success"
    mock_db_connection.begin.assert_called_once()
    mock_db_connection.commit.assert_called_once()
    mock_db_connection.rollback.assert_not_called()
    mock_db_connection.close.assert_called_once()


# Test asynchronous wrapper - nested transaction
@pytest.mark.asyncio
async def test_transactional_async_nested(mock_db_connection, mocker):
    mocker.patch(
        "transactional.get_connection", return_value=(mock_db_connection, False)
    )

    @transactional
    async def outer_function():
        return await inner_function()

    @transactional
    async def inner_function():
        return "nested"

    # Simulate existing connection
    db_connection_context.set(mock_db_connection)

    result = await outer_function()

    assert result == "nested"
    mock_db_connection.begin.assert_not_called()
    mock_db_connection.commit.assert_not_called()
    mock_db_connection.rollback.assert_not_called()
    mock_db_connection.close.assert_not_called()
    assert db_connection_context.get() == mock_db_connection
