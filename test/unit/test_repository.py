from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

import mariadb
import pytest
from attr import dataclass
from dependency_injector import providers

from database import DatabasePool
from enums import ChannelEnum, AttackTypeEnum, PeriodType
from models import (
    Guild,
    Channel,
    ChannelMessage,
    ClanBattleBossEntry,
    ClanBattleBossBook,
    ClanBattlePeriod,
    ClanBattlePeriodDay,
    ClanBattleBoss,
    ClanBattleBossHealth,
    ClanBattleOverallEntry,
    ClanBattleLeftover,
    ClanBattleReportEntry,
    ClanBattleReportMessage,
    GuildPlayer,
)
from repository import (
    fetch_one_to_model,
    fetch_all_to_model,
    GenericRepository,
    connection_context,
    GuildRepository,
    ChannelRepository,
    ChannelMessageRepository,
    ClanBattleBossEntryRepository,
    ClanBattleBossBookRepository,
    ClanBattleBossRepository,
    ClanBattlePeriodRepository,
    ClanBattleBossHealthRepository,
    ClanBattleOverallEntryRepository,
    ClanBattleReportMessageRepository,
    GuildPlayerRepository,
    ErrorLogRepository,
)


@dataclass
class TestModel:
    id: int
    name: str


def normalize_sql(sql: str):
    return sql.replace(" ", "").replace("\n", "")


@pytest.fixture
def mock_cursor():
    return Mock()


@pytest.fixture
def mock_attrs(mocker):
    return mocker.patch("repository.attrs.asdict")


# Fixture to mock connection and cursor without hardcoding fetchone result
@pytest.fixture
def mock_db(mocker):
    # Mock the connection object
    conn = Mock()
    # Mock the cursor object
    cursor = Mock()
    cursor.execute = Mock()
    cursor.fetchone = Mock()
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)  # Explicitly do not suppress exceptions
    conn.cursor = Mock(return_value=cursor)
    # Mock connection_context and get_connection
    mocker.patch("repository.get_connection", return_value=(conn, True))
    mocker.patch(
        "repository.connection_context",
        return_value=Mock(
            __enter__=Mock(return_value=conn), __exit__=Mock(return_value=False)
        ),
    )
    return conn, cursor


def test_fetch_all_to_model_success(mock_cursor):
    mock_cursor.fetchall.return_value = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]

    result = fetch_all_to_model(mock_cursor, TestModel)

    assert len(result) == 2
    assert isinstance(result[0], TestModel)
    assert result[0].id == 1
    assert result[0].name == "Alice"
    assert result[1].id == 2
    assert result[1].name == "Bob"


def test_fetch_all_to_model_empty(mock_cursor):
    mock_cursor.fetchall.return_value = []

    result = fetch_all_to_model(mock_cursor, TestModel)

    assert result == []


def test_fetch_one_to_model_success(mock_cursor):
    mock_cursor.fetchone.return_value = {"id": 1, "name": "Alice"}

    result = fetch_one_to_model(mock_cursor, TestModel)

    assert isinstance(result, TestModel)
    assert result.id == 1
    assert result.name == "Alice"


def test_fetch_one_to_model_none(mock_cursor):
    mock_cursor.fetchone.return_value = None

    result = fetch_one_to_model(mock_cursor, TestModel)

    assert result is None


def test_context_conn_should_close(mocker):
    # Mock connection
    conn = MagicMock()
    conn.close = MagicMock()

    # Mock get_connection and reset_connection_context
    mocker.patch("repository.get_connection", return_value=(conn, True))
    mock_reset_connection_context = mocker.patch("repository.reset_connection_context")

    # Use context manager correctly
    with connection_context() as result:
        # Verify result is the mocked conn
        assert result is conn

    # Verify close and reset_connection_context were called
    conn.close.assert_called_once()
    mock_reset_connection_context.assert_called_once()


def test_context_conn_context_none(mocker):
    conn = MagicMock()
    conn.close = MagicMock()
    db_conn = MagicMock()

    mock_context_var = MagicMock()
    mock_context_var.get.return_value = db_conn
    mocker.patch("repository.db_connection_context", mock_context_var)

    mocker.patch("repository.get_connection", return_value=(conn, True))
    mock_reset_connection_context = mocker.patch("repository.reset_connection_context")
    mock_set_connection_context = mocker.patch("repository.set_connection_context")

    with connection_context() as result:
        assert result is db_conn  # Yields db_conn
        mock_set_connection_context.assert_not_called()

    conn.close.assert_not_called()
    mock_reset_connection_context.assert_not_called()
    db_conn.close.assert_not_called()


# Repo DB


# GenericRepository
# Test case: fetching connection ID
def test_get_connection_id_success(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {"CONNECTION_ID": 42}
    repo = GenericRepository()

    result = repo.get_connection_id()

    assert result == 42
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_connection_id_none_result(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = None
    repo = GenericRepository()

    with pytest.raises(ValueError, match="Failed to retrieve connection ID"):
        repo.get_connection_id()

    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_connection_id_empty_dict(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {}
    repo = GenericRepository()

    with pytest.raises(KeyError, match="CONNECTION_ID"):
        repo.get_connection_id()

    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_set_session_read_uncommited(mock_db):
    conn, cursor = mock_db
    repo = GenericRepository()

    repo.set_session_read_uncommited()

    cursor.execute.assert_called_once()


def test_get_session_transaction_isolation_success(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {"TI": "REPEATABLE READ"}
    repo = GenericRepository()

    result = repo.get_session_transaction_isolation()

    assert result == "REPEATABLE READ"
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_session_transaction_isolation_none_result(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = None
    repo = GenericRepository()

    with pytest.raises(ValueError, match="Failed to retrieve transaction Isolation"):
        repo.get_session_transaction_isolation()

    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_session_transaction_isolation_empty_dict(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {}
    repo = GenericRepository()

    with pytest.raises(KeyError, match="TI"):
        repo.get_session_transaction_isolation()

    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_session_autocommit_success(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {"AC": True}
    repo = GenericRepository()

    result = repo.get_session_autocommit()

    assert result is True
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_session_autocommit_none_result(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = None
    repo = GenericRepository()

    with pytest.raises(ValueError, match="Failed to retrieve session auto commit"):
        repo.get_session_autocommit()

    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_session_autocommit_empty_dict(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {}
    repo = GenericRepository()

    with pytest.raises(KeyError, match="AC"):
        repo.get_session_autocommit()

    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_session_transaction_id_success(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {"trx_id": 1}
    repo = GenericRepository()

    result = repo.get_session_transaction_id()

    assert result == 1
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_session_transaction_id_none_result(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = None
    repo = GenericRepository()

    result = repo.get_session_transaction_id()

    assert result == "None"
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_session_transaction_id_empty_dict(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {}
    repo = GenericRepository()

    with pytest.raises(KeyError, match="trx_id"):
        repo.get_session_transaction_id()

    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


# GuildRepository
def test_get_by_guild_id_return_value(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {"guild_id": 1}
    repo = GuildRepository()

    result = repo.get_by_guild_id(1)

    assert result.guild_id == 1
    assert result.guild_name is None
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_by_guild_id_return_none(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {}
    repo = GuildRepository()

    result = repo.get_by_guild_id(1)

    assert result is None
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_insert_guild(mock_db):
    conn, cursor = mock_db
    repo = GuildRepository()

    result = repo.insert_guild(Guild(1, "test"))

    assert result.guild_id == 1
    assert result.guild_name == "test"
    cursor.execute.assert_called_once()


def test_delete_by_guild_id(mock_db):
    conn, cursor = mock_db
    repo = GuildRepository()

    result = repo.delete_by_guild_id(1)

    assert result == True
    cursor.execute.assert_called_once()


# Channel Repo
def test_get_all_by_guild_id_success(mock_db):
    conn, cursor = mock_db
    cursor.fetchall.return_value = [
        {"channel_id": 1, "guild_id": 1, "channel_type": "CATEGORY"},
        {"channel_id": 2, "guild_id": 1, "channel_type": "BOSS1"},
    ]
    repo = ChannelRepository()

    result = repo.get_all_by_guild_id(1)

    assert len(result) == 2
    cursor.execute.assert_called_once()
    cursor.fetchall.assert_called_once()


def test_get_all_by_guild_id_none_result(mock_db):
    conn, cursor = mock_db
    cursor.fetchall.return_value = None
    repo = ChannelRepository()

    result = repo.get_all_by_guild_id(1)

    assert len(result) == 0
    cursor.execute.assert_called_once()
    cursor.fetchall.assert_called_once()


def test_get_boss_channel_by_guild_id_success(mock_db):
    conn, cursor = mock_db
    cursor.fetchall.return_value = [
        {"channel_id": 2, "guild_id": 1, "channel_type": "BOSS1"},
    ]
    repo = ChannelRepository()

    result = repo.get_boss_channel_by_guild_id(1)

    assert len(result) == 1
    cursor.execute.assert_called_once()
    cursor.fetchall.assert_called_once()


def test_get_boss_channel_by_guild_id_none_result(mock_db):
    conn, cursor = mock_db
    cursor.fetchall.return_value = None
    repo = ChannelRepository()

    result = repo.get_boss_channel_by_guild_id(1)

    assert len(result) == 0
    cursor.execute.assert_called_once()
    cursor.fetchall.assert_called_once()


def test_get_by_guild_id_and_type_success(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {
        "channel_id": 1,
        "guild_id": 1,
        "channel_type": "BOSS1",
    }
    repo = ChannelRepository()

    result = repo.get_by_guild_id_and_type(1, ChannelEnum.BOSS1.name)

    assert result.channel_type == ChannelEnum.BOSS1
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_by_guild_id_and_type_none_result(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = None
    repo = ChannelRepository()

    result = repo.get_by_guild_id_and_type(1, ChannelEnum.BOSS1.name)

    assert result is None
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_insert_channel(mock_db):
    conn, cursor = mock_db
    repo = ChannelRepository()

    channel = Channel(1, 1, ChannelEnum.BOSS1)
    repo.insert_channel(channel)

    cursor.execute.assert_called_once()


def test_insert_channel_failed(mock_db):
    conn, cursor = mock_db
    cursor.execute.side_effect = AttributeError("Invalid")
    repo = ChannelRepository()

    with pytest.raises(AttributeError, match="Invalid"):
        channel = Channel(1)
        repo.insert_channel(channel)

    cursor.execute.assert_called_once()


def test_update_channel(mock_db):
    conn, cursor = mock_db
    repo = ChannelRepository()

    channel = Channel(1, 1, ChannelEnum.BOSS1)
    repo.update_channel(channel)

    cursor.execute.assert_called_once()


def test_update_channel_failed(mock_db):
    conn, cursor = mock_db
    cursor.execute.side_effect = AttributeError("Invalid")
    repo = ChannelRepository()

    with pytest.raises(AttributeError):
        channel = Channel(1)
        repo.update_channel(channel)

    cursor.execute.assert_called_once()


def test_delete_channel_by_guild_id_success(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = None
    repo = ChannelRepository()

    result = repo.delete_channel_by_guild_id(1)

    assert result == True
    cursor.execute.assert_called_once()


def test_delete_channel_by_guild_id_failed(mock_db):
    conn, cursor = mock_db
    cursor.execute.side_effect = AttributeError("Invalid")
    repo = ChannelRepository()

    with pytest.raises(AttributeError):
        repo.delete_channel_by_guild_id(1)

    cursor.execute.assert_called_once()


# ChannelMessageRepository
def test_insert_channel_message_success(mock_db):
    conn, cursor = mock_db
    cursor.execute.return_result = None
    repo = ChannelMessageRepository()

    repo.insert_channel_message(ChannelMessage(1, 1))

    cursor.execute.assert_called_once()


def test_insert_channel_message_failed(mock_db):
    conn, cursor = mock_db
    cursor.execute.side_effect = mariadb.Error("Invalid")
    repo = ChannelMessageRepository()

    with pytest.raises(mariadb.Error):
        repo.insert_channel_message(ChannelMessage(1, 1))

    cursor.execute.assert_called_once()


def test_update_channel_message_success(mock_db):
    conn, cursor = mock_db
    cursor.execute.return_result = None
    repo = ChannelMessageRepository()

    channel_message = ChannelMessage(1, 1)
    result = repo.update_channel_message(channel_message)

    assert result.message_id == channel_message.message_id
    assert result.channel_id == channel_message.channel_id
    cursor.execute.assert_called_once()


def test_get_all_by_guild_id_success(mock_db):
    conn, cursor = mock_db
    # Mock the fetchall result to return some sample channel_message objects
    cursor.fetchall.return_value = [
        {"channel_id": 1, "message_id": 2},
        {"channel_id": 3, "message_id": 4},
    ]

    repo = ChannelMessageRepository()
    guild_id = 1

    result = repo.get_all_by_guild_id(guild_id)

    assert len(result) == 2
    assert isinstance(result[0], ChannelMessage)
    assert result[0].channel_id == 1
    assert result[0].message_id == 2
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CM.channel_id,
               CM.message_id
        FROM channel_message CM 
            JOIN channel C ON C.channel_id = CM.channel_id
            JOIN guild G ON G.guild_id = C.guild_id
        WHERE G.guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_all_by_guild_id_no_results(mock_db):
    conn, cursor = mock_db
    # Mock the fetchall result to return an empty list
    cursor.fetchall.return_value = []

    repo = ChannelMessageRepository()
    guild_id = 1

    result = repo.get_all_by_guild_id(guild_id)

    assert len(result) == 0
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CM.channel_id,
               CM.message_id
        FROM channel_message CM 
            JOIN channel C ON C.channel_id = CM.channel_id
            JOIN guild G ON G.guild_id = C.guild_id
        WHERE G.guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_delete_by_guild_id_success(mock_db):
    conn, cursor = mock_db

    repo = ChannelMessageRepository()

    guild_id = 1
    result = repo.delete_by_guild_id(guild_id)

    assert result == True

    expected_query = """
        DELETE FROM channel_message 
        WHERE channel_id IN (SELECT channel_id from channel WHERE guild_id = %(guild_id)s)
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_delete_by_guild_id_no_channels(mock_db):
    conn, cursor = mock_db
    cursor.fetchall.return_value = []

    repo = ChannelMessageRepository()

    guild_id = 1
    result = repo.delete_by_guild_id(guild_id)

    assert result == True

    expected_query = """
        DELETE FROM channel_message 
        WHERE channel_id IN (SELECT channel_id from channel WHERE guild_id = %(guild_id)s)
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_update_self_channel_message_success(mock_db):
    conn, cursor = mock_db

    repo = ChannelMessageRepository()

    old_channel_id = 1
    new_channel_id = 2

    result = repo.update_self_channel_message(old_channel_id, new_channel_id)

    assert result == True

    expected_query = """
        UPDATE channel_message 
            SET channel_id = %(new_channel_id)s
        WHERE channel_id = %(old_channel_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_update_self_channel_message_failure(mock_db):
    conn, cursor = mock_db
    cursor.rowcount = -1
    repo = ChannelMessageRepository()

    old_channel_id = 1
    new_channel_id = 2

    result = repo.update_self_channel_message(old_channel_id, new_channel_id)

    assert (
        result == True
    )  # Assuming the function returns True even if nothing was updated


def test_get_channel_message_by_channel_id_success(mock_db):
    conn, cursor = mock_db

    repo = ChannelMessageRepository()

    channel_id = 1

    cursor.fetchone.return_value = {
        "channel_id": channel_id,
        "message_id": 2,
    }

    expected_query = """
        SELECT channel_id,
               message_id 
        FROM channel_message 
        WHERE channel_id = %(channel_id)s
        """

    result = repo.get_channel_message_by_channel_id(channel_id)

    assert isinstance(result, ChannelMessage)
    assert result.channel_id == channel_id
    assert result.message_id == 2

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_channel_message_by_channel_id_no_message(mock_db):
    conn, cursor = mock_db

    repo = ChannelMessageRepository()

    channel_id = 1
    expected_query = """
        SELECT channel_id,
               message_id 
        FROM channel_message 
        WHERE channel_id = %(channel_id)s
        """
    cursor.fetchone.return_value = None

    result = repo.get_channel_message_by_channel_id(channel_id)

    assert result is None

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_message_by_guild_id_and_channel_type_success(mock_db):
    conn, cursor = mock_db

    repo = ChannelMessageRepository()
    guild_id = 1
    channel_type = "voice"

    # Mock the fetch_one_to_model result to return a sample ChannelMessage object
    expected_result = {
        "channel_id": 1,
        "message_id": 2,
    }
    cursor.fetchone.return_value = expected_result

    result = repo.get_message_by_guild_id_and_channel_type(guild_id, channel_type)

    assert isinstance(result, ChannelMessage)
    assert result.channel_id == 1
    assert result.message_id == 2
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CM.channel_id,
               CM.message_id
        FROM channel_message CM
             JOIN channel C on CM.channel_id = C.channel_id
        WHERE C.guild_id = %(guild_id)s AND C.channel_type = %(channel_type)s
        """

    actual_query_args, _ = cursor.execute.call_args
    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_message_by_guild_id_and_channel_type_no_results(mock_db):
    conn, cursor = mock_db

    repo = ChannelMessageRepository()
    guild_id = 1
    channel_type = "voice"

    # Mock the fetch_one_to_model result to return None when no results are found
    cursor.fetchone.return_value = None

    result = repo.get_message_by_guild_id_and_channel_type(guild_id, channel_type)

    assert result is None
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CM.channel_id,
               CM.message_id
        FROM channel_message CM
             JOIN channel C on CM.channel_id = C.channel_id
        WHERE C.guild_id = %(guild_id)s AND C.channel_type = %(channel_type)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


# Clan Battle Boss Repository
def test_insert_clan_battle_boss_entry_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry = ClanBattleBossEntry(
        guild_id=1,
        message_id=2,
        clan_battle_period_id=3,
        clan_battle_boss_id=4,
        name="Example Boss",
        image_path="/path/to/image.png",
        boss_round=5,
        current_health=6000,
        max_health=8000,
    )

    # Mock the lastrowid attribute of the cursor to return a sample ID
    expected_insert_id = 12345
    cursor.lastrowid = expected_insert_id

    result = repo.insert_clan_battle_boss_entry(clan_battle_boss_entry)

    assert isinstance(result, ClanBattleBossEntry)
    assert result.clan_battle_boss_entry_id == expected_insert_id

    cursor.execute.assert_called_once()

    expected_query = """
        INSERT INTO clan_battle_boss_entry (
            guild_id,
            message_id, 
            clan_battle_period_id, 
            clan_battle_boss_id, 
            name, 
            image_path, 
            boss_round, 
            current_health, 
            max_health
        ) VALUES (%(guild_id)s, %(message_id)s, %(clan_battle_period_id)s,
                  %(clan_battle_boss_id)s,%(name)s,%(image_path)s,
                  %(boss_round)s,%(current_health)s,%(max_health)s)
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_insert_clan_battle_boss_entry_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()

    cursor.execute.side_effect = Exception("Insert operation failed")

    clan_battle_boss_entry = ClanBattleBossEntry(
        guild_id=1,
        message_id=2,
        clan_battle_period_id=3,
        clan_battle_boss_id=4,
        name="Example Boss",
        image_path="/path/to/image.png",
        boss_round=5,
        current_health=6000,
        max_health=8000,
    )

    with pytest.raises(Exception, match="Insert operation failed"):
        repo.insert_clan_battle_boss_entry(clan_battle_boss_entry)

    cursor.execute.assert_called_once()

    expected_query = """
        INSERT INTO clan_battle_boss_entry (
            guild_id,
            message_id, 
            clan_battle_period_id, 
            clan_battle_boss_id, 
            name, 
            image_path, 
            boss_round, 
            current_health, 
            max_health
        ) VALUES (%(guild_id)s,%(message_id)s,%(clan_battle_period_id)s,
                  %(clan_battle_boss_id)s,%(name)s,%(image_path)s,
                  %(boss_round)s,%(current_health)s,%(max_health)s)
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_last_by_message_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    message_id = 100

    # Mock the fetch_one_to_model result to return some sample clan_battle_boss_entry objects
    expected_result_dict = {
        "clan_battle_boss_entry_id": 1,
        "guild_id": 2,
        "message_id": 3,
        "clan_battle_period_id": 4,
        "clan_battle_boss_id": 5,
        "name": "Boss",
        "image_path": "/path/to/image.png",
        "boss_round": 10,
        "current_health": 500,
        "max_health": 1000,
    }

    cursor.fetchone.return_value = expected_result_dict

    result = repo.get_last_by_message_id(message_id)

    assert isinstance(result, ClanBattleBossEntry)
    assert (
        result.clan_battle_boss_entry_id
        == expected_result_dict["clan_battle_boss_entry_id"]
    )
    assert result.guild_id == expected_result_dict["guild_id"]
    assert result.message_id == expected_result_dict["message_id"]
    assert result.clan_battle_period_id == expected_result_dict["clan_battle_period_id"]
    assert result.clan_battle_boss_id == expected_result_dict["clan_battle_boss_id"]
    assert result.name == expected_result_dict["name"]
    assert result.image_path == expected_result_dict["image_path"]
    assert result.boss_round == expected_result_dict["boss_round"]
    assert result.current_health == expected_result_dict["current_health"]
    assert result.max_health == expected_result_dict["max_health"]

    expected_query = """
        SELECT clan_battle_boss_entry_id,
               guild_id,
               message_id,
               clan_battle_period_id,
               clan_battle_boss_id,
               name,
               image_path,
               boss_round,
               current_health,
               max_health
        FROM clan_battle_boss_entry
        WHERE message_id = %(message_id)s
        ORDER BY boss_round, clan_battle_boss_entry_id DESC
        LIMIT 1
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_expected_query == normalized_actual_query
    ), f"Expected: {normalized_expected_query}, Actual: {normalized_actual_query}"


def test_get_last_by_message_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    message_id = 0

    # Mock the fetch_one_to_model result to return None when no results are found
    cursor.fetchone.return_value = None

    result = repo.get_last_by_message_id(message_id)

    assert result is None


def test_get_boss_entry_by_param_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()

    guild_id = 1
    clan_battle_period_id = 2
    clan_battle_boss_id = 3

    # Mock the fetch_one_to_model result to return some sample data
    expected_data = {
        "clan_battle_boss_entry_id": 4,
        "guild_id": guild_id,
        "message_id": 5,
        "clan_battle_period_id": clan_battle_period_id,
        "clan_battle_boss_id": clan_battle_boss_id,
        "name": "BossName",
        "image_path": "/path/to/boss/image.png",
        "boss_round": 1,
        "current_health": 100,
        "max_health": 200,
    }

    cursor.fetchone.return_value = expected_data

    result = repo.get_boss_entry_by_param(
        guild_id, clan_battle_period_id, clan_battle_boss_id
    )

    assert isinstance(result, ClanBattleBossEntry)
    assert result.clan_battle_boss_entry_id == 4
    assert result.guild_id == guild_id
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT clan_battle_boss_entry_id,
               guild_id,
               message_id,
               clan_battle_period_id,
               clan_battle_boss_id,
               name,
               image_path,
               boss_round,
               current_health,
               max_health
        FROM clan_battle_boss_entry
        WHERE guild_id = %(guild_id)s
        AND clan_battle_period_id = %(clan_battle_period_id)s
        AND clan_battle_boss_id = %(clan_battle_boss_id)s
        ORDER BY boss_round, clan_battle_boss_entry_id DESC
        LIMIT 1
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert normalized_expected_query == normalized_actual_query


def test_get_boss_entry_by_param_no_result(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()

    guild_id = 1
    clan_battle_period_id = 2
    clan_battle_boss_id = 3

    # Mock the fetch_one_to_model result to return None
    cursor.fetchone.return_value = None

    result = repo.get_boss_entry_by_param(
        guild_id, clan_battle_period_id, clan_battle_boss_id
    )

    assert result is None


def test_get_last_active_period_by_message_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    message_id = 1

    # Mock the fetch_all_to_model result to return some sample clan_battle_boss_entry objects
    cursor.fetchone.return_value = {
        "clan_battle_boss_entry_id": 1,
        "guild_id": 2,
        "message_id": 3,
        "clan_battle_period_id": 4,
        "clan_battle_boss_id": 5,
        "name": "Boss",
        "image_path": "/path/to/image.jpg",
        "boss_round": 10,
        "current_health": 100,
        "max_health": 200,
    }

    result = repo.get_last_active_period_by_message_id(message_id)

    assert isinstance(result, ClanBattleBossEntry)
    assert result.clan_battle_boss_entry_id == 1
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CBBE.clan_battle_boss_entry_id,
               CBBE.guild_id,
               CBBE.message_id,
               CBBE.clan_battle_period_id,
               CBBE.clan_battle_boss_id,
               CBBE.name,
               CBBE.image_path,
               CBBE.boss_round,
               CBBE.current_health,
               CBBE.max_health
        FROM clan_battle_boss_entry AS CBBE 
            JOIN clan_battle_period CBR ON CBBE.clan_battle_period_id = CBR.clan_battle_period_id
        WHERE message_id = %(message_id)s
        AND CBR.is_active = 1
        ORDER BY boss_round, clan_battle_boss_entry_id DESC
        LIMIT 1
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_last_active_period_by_message_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    message_id = 1

    # Mock the fetch_one_to_model result to return None
    cursor.fetchone.return_value = None

    result = repo.get_last_active_period_by_message_id(message_id)

    assert result is None
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CBBE.clan_battle_boss_entry_id,
               CBBE.guild_id,
               CBBE.message_id,
               CBBE.clan_battle_period_id,
               CBBE.clan_battle_boss_id,
               CBBE.name,
               CBBE.image_path,
               CBBE.boss_round,
               CBBE.current_health,
               CBBE.max_health
        FROM clan_battle_boss_entry AS CBBE 
            JOIN clan_battle_period CBR ON CBBE.clan_battle_period_id = CBR.clan_battle_period_id
        WHERE message_id = %(message_id)s
        AND CBR.is_active = 1
        ORDER BY boss_round, clan_battle_boss_entry_id DESC
        LIMIT 1
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_update_on_attack_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry_id = 1
    current_health = 50

    result = repo.update_on_attack(clan_battle_boss_entry_id, current_health)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        UPDATE clan_battle_boss_entry 
        SET current_health = %(current_health)s
        WHERE clan_battle_boss_entry_id = %(clan_battle_boss_entry_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_update_on_attack_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry_id = 1
    current_health = -10
    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid") as e:
        repo.update_on_attack(clan_battle_boss_entry_id, current_health)

    cursor.execute.assert_called_once()

    expected_query = """
        UPDATE clan_battle_boss_entry 
        SET current_health = %(current_health)s
        WHERE clan_battle_boss_entry_id = %(clan_battle_boss_entry_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_update_message_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry_id = 1
    message_id = 2

    result = repo.update_message_id(clan_battle_boss_entry_id, message_id)

    assert result == True
    cursor.execute.assert_called_once()

    expected_query = """
        UPDATE clan_battle_boss_entry 
        SET message_id = %(message_id)s
        WHERE clan_battle_boss_entry_id = %(clan_battle_boss_entry_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_update_message_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry_id = 1
    message_id = None

    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid") as e:
        repo.update_message_id(clan_battle_boss_entry_id, message_id)

    cursor.execute.assert_called_once()

    expected_query = """
        UPDATE clan_battle_boss_entry 
        SET message_id = %(message_id)s
        WHERE clan_battle_boss_entry_id = %(clan_battle_boss_entry_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_cb_entry_delete_by_guild_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM clan_battle_boss_entry 
        WHERE guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_cb_entry_delete_by_guild_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    guild_id = 1

    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid") as e:
        repo.delete_by_guild_id(guild_id)

    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM clan_battle_boss_entry 
        WHERE guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


# Clan Battle Boss Book


def test_get_all_by_message_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    message_id = 100

    # Mock the fetch_all_to_model result to return some sample clan_battle_boss_book objects
    cursor.fetchall.return_value = [
        {
            "clan_battle_boss_book_id": 1,
            "clan_battle_boss_entry_id": 2,
            "guild_id": 3,
            "player_id": 4,
            "player_name": "John",
            "attack_type": "PATK",
            "damage": 500,
            "clan_battle_overall_entry_id": 6,
            "leftover_time": 120,
            "entry_date": datetime(2023, 4, 1, 12, 0),
        },
        {
            "clan_battle_boss_book_id": 7,
            "clan_battle_boss_entry_id": 8,
            "guild_id": 9,
            "player_id": 10,
            "player_name": "Jane",
            "attack_type": "MATK",
            "damage": 450,
            "clan_battle_overall_entry_id": 11,
            "leftover_time": 60,
            "entry_date": datetime(2023, 4, 2, 10, 30),
        },
    ]

    result = repo.get_all_by_message_id(message_id)

    assert len(result) == 2
    assert isinstance(result[0], ClanBattleBossBook)
    assert result[0].clan_battle_boss_book_id == 1
    assert result[0].player_name == "John"
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CBBB.clan_battle_boss_book_id,
               CBBB.clan_battle_boss_entry_id,
               CBBB.guild_id,
               CBBB.player_id,
               CBBB.player_name,
               CBBB.attack_type,
               CBBB.damage,
               CBBB.clan_battle_overall_entry_id,
               CBBB.leftover_time,
               CBBB.entry_date
        FROM clan_battle_boss_book CBBB
            JOIN clan_battle_boss_entry CBE ON CBBB.clan_battle_boss_entry_id = CBE.clan_battle_boss_entry_id
        WHERE CBE.message_id = %(message_id)s
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_all_by_message_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    message_id = 1

    # Mock fetch_all_to_model result to return an empty list (no results)
    cursor.fetchall.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid") as e:
        repo.get_all_by_message_id(message_id)

    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CBBB.clan_battle_boss_book_id,
               CBBB.clan_battle_boss_entry_id,
               CBBB.guild_id,
               CBBB.player_id,
               CBBB.player_name,
               CBBB.attack_type,
               CBBB.damage,
               CBBB.clan_battle_overall_entry_id,
               CBBB.leftover_time,
               CBBB.entry_date
        FROM clan_battle_boss_book CBBB 
            JOIN clan_battle_boss_entry CBE ON CBBB.clan_battle_boss_entry_id = CBE.clan_battle_boss_entry_id
        WHERE CBE.message_id = %(message_id)s
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_player_book_entry_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    message_id = 12345
    player_id = 67890

    # Mock the fetch_one_to_model result to return a sample clan_battle_boss_book object
    cursor.fetchone.return_value = {
        "clan_battle_boss_book_id": 1,
        "clan_battle_boss_entry_id": 2,
        "guild_id": 3,
        "player_id": player_id,
        "player_name": "PlayerName",
        "attack_type": "PATK",
        "damage": 1000,
        "clan_battle_overall_entry_id": 456789,
        "leftover_time": None,
        "entry_date": datetime.now(),
    }

    result = repo.get_player_book_entry(message_id, player_id)

    assert isinstance(result, ClanBattleBossBook)
    assert result.clan_battle_boss_book_id == 1
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CBBB.clan_battle_boss_book_id,
               CBBB.clan_battle_boss_entry_id,
               CBBB.guild_id,
               CBBB.player_id,
               CBBB.player_name,
               CBBB.attack_type,
               CBBB.damage,
               CBBB.clan_battle_overall_entry_id,
               CBBB.leftover_time,
               CBBB.entry_date
            FROM clan_battle_boss_book AS CBBB
                                 INNER JOIN clan_battle_boss_entry AS CBBE ON CBBB.clan_battle_boss_entry_id = CBBE.clan_battle_boss_entry_id
                        WHERE CBBB.player_id = %(player_id)s
                          AND CBBE.message_id = %(message_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_player_book_entry_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    message_id = 12345
    player_id = 67890

    # Mock the fetch_one_to_model result to return None
    cursor.fetchone.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.get_player_book_entry(message_id, player_id)

    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CBBB.clan_battle_boss_book_id,
               CBBB.clan_battle_boss_entry_id,
               CBBB.guild_id,
               CBBB.player_id,
               CBBB.player_name,
               CBBB.attack_type,
               CBBB.damage,
               CBBB.clan_battle_overall_entry_id,
               CBBB.leftover_time,
               CBBB.entry_date
            FROM clan_battle_boss_book AS CBBB
                                 INNER JOIN clan_battle_boss_entry AS CBBE ON CBBB.clan_battle_boss_entry_id = CBBE.clan_battle_boss_entry_id
                        WHERE CBBB.player_id = %(player_id)s
                          AND CBBE.message_id = %(message_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_player_book_count_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    guild_id = 1
    player_id = 2

    # Mock the fetchone result to return some sample data
    cursor.fetchone.return_value = {"Book_Count": 3}

    result = repo.get_player_book_count(guild_id, player_id)

    assert result == 3
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT COUNT(CBBB.clan_battle_boss_book_id) AS Book_Count
            FROM clan_battle_boss_book AS CBBB
                     INNER JOIN clan_battle_boss_entry AS CBBE ON CBBB.clan_battle_boss_entry_id = CBBE.clan_battle_boss_entry_id
                     INNER JOIN channel_message AS CM ON CBBE.message_id = CM.message_id
                     INNER JOIN channel AS C ON CM.channel_id = C.channel_id
                     INNER JOIN guild AS G ON C.guild_id = G.guild_id
            WHERE G.guild_id = %(guild_id)s
                AND CBBB.player_id = %(player_id)s
                AND CBBB.entry_date >= IF(CURRENT_TIME() < '05:00:00',
                        CONCAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'),
                        CONCAT(CURDATE(), '05:00:00'))
                AND CBBB.entry_date < IF(CURRENT_TIME() < '05:00:00',
                           CONCAT(CURDATE(), '05:00:00'),
                           CONCAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'))
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert normalized_expected_query == normalized_actual_query


def test_get_player_book_count_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    guild_id = 1
    player_id = 2

    # Mock the fetchone result to return None
    cursor.fetchone.return_value = None

    result = repo.get_player_book_count(guild_id, player_id)

    assert result == 0
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT COUNT(CBBB.clan_battle_boss_book_id) AS Book_Count
            FROM clan_battle_boss_book AS CBBB
                     INNER JOIN clan_battle_boss_entry AS CBBE ON CBBB.clan_battle_boss_entry_id = CBBE.clan_battle_boss_entry_id
                     INNER JOIN channel_message AS CM ON CBBE.message_id = CM.message_id
                     INNER JOIN channel AS C ON CM.channel_id = C.channel_id
                     INNER JOIN guild AS G ON C.guild_id = G.guild_id
            WHERE G.guild_id = %(guild_id)s
                AND CBBB.player_id = %(player_id)s
                AND CBBB.entry_date >= IF(CURRENT_TIME() < '05:00:00',
                        CONCAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'),
                        CONCAT(CURDATE(), '05:00:00'))
                AND CBBB.entry_date < IF(CURRENT_TIME() < '05:00:00',
                           CONCAT(CURDATE(), '05:00:00'),
                           CONCAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'))
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert normalized_expected_query == normalized_actual_query


def test_delete_book_by_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    clan_battle_boss_book_id = 1

    result = repo.delete_book_by_id(clan_battle_boss_book_id)

    assert result == True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM clan_battle_boss_book WHERE clan_battle_boss_book_id = %(clan_battle_boss_book_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = expected_query.replace(" ", "").replace("\n", "")
    normalized_actual_query = (
        str(actual_query_args[0]).replace(" ", "").replace("\n", "")
    )

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_delete_book_by_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    clan_battle_boss_book_id = 1

    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.delete_book_by_id(clan_battle_boss_book_id)

    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM clan_battle_boss_book WHERE clan_battle_boss_book_id = %(clan_battle_boss_book_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_delete_book_by_entry_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    entry_id = 1

    result = repo.delete_book_by_entry_id(entry_id)

    assert result == True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE
        FROM clan_battle_boss_book
        WHERE clan_battle_boss_entry_id = %(clan_battle_boss_entry_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_delete_book_by_entry_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    entry_id = 1

    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.delete_book_by_entry_id(entry_id)

    cursor.execute.assert_called_once()

    expected_query = """
        DELETE
        FROM clan_battle_boss_book
        WHERE clan_battle_boss_entry_id = %(clan_battle_boss_entry_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_insert_boss_book_entry_success(mock_db):
    conn, cursor = mock_db
    cursor.lastrowid = 1

    repo = ClanBattleBossBookRepository()
    clan_battle_boss_book = ClanBattleBossBook(
        clan_battle_boss_book_id=1,
        clan_battle_boss_entry_id=2,
        guild_id=3,
        player_id=4,
        player_name="Player 1",
        attack_type=AttackTypeEnum.PATK,
        damage=100,
        clan_battle_overall_entry_id=5,
    )

    result = repo.insert_boss_book_entry(clan_battle_boss_book)

    assert result.clan_battle_boss_book_id == 1
    cursor.execute.assert_called_once()


def test_insert_boss_book_entry_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()

    clan_battle_boss_book = None

    with pytest.raises(AttributeError) as exc_info:
        result = repo.insert_boss_book_entry(clan_battle_boss_book)

    assert "'NoneType' object has no attribute 'to_db_dict'" in str(exc_info.value)


def test_update_damage_boss_book_by_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    clan_battle_boss_book_id = 1
    damage = 50

    result = repo.update_damage_boss_book_by_id(clan_battle_boss_book_id, damage)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        UPDATE clan_battle_boss_book 
            SET damage = %(damage)s
        WHERE clan_battle_boss_book_id = %(clan_battle_boss_book_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_update_damage_boss_book_by_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    clan_battle_boss_book_id = 1
    damage = None

    result = repo.update_damage_boss_book_by_id(clan_battle_boss_book_id, damage)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        UPDATE clan_battle_boss_book 
            SET damage = %(damage)s
        WHERE clan_battle_boss_book_id = %(clan_battle_boss_book_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_cb_repo_delete_by_guild_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM clan_battle_boss_book 
        WHERE guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_cb_repo_delete_by_guild_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM clan_battle_boss_book 
        WHERE guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_insert_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattlePeriodRepository()

    new_clan_battle_period = ClanBattlePeriod(
        clan_battle_period_name="Test Battle",
        period_type=PeriodType.LIVE,
        date_from=datetime.now(),
        date_to=datetime.now() + timedelta(days=7),
        is_active=True,
        boss1_id=1,
        boss2_id=2,
        boss3_id=3,
        boss4_id=4,
        boss5_id=5,
    )

    expected_insert_id = 12345
    cursor.lastrowid = expected_insert_id

    result = repo.insert(new_clan_battle_period)

    assert isinstance(result, ClanBattlePeriod)
    assert new_clan_battle_period.clan_battle_period_id == expected_insert_id
    cursor.execute.assert_called_once()

    expected_query = """
        INSERT INTO clan_battle_period(
            clan_battle_period_name,
            period_type,
            date_from,
            date_to,
            is_active,
            boss1_id,
            boss2_id,
            boss3_id,
            boss4_id,
            boss5_id
        ) 
        VALUES (
            %(clan_battle_period_name)s,%(period_type)s,%(date_from)s,%(date_to)s,%(is_active)s,%(boss1_id)s,%(boss2_id)s,%(boss3_id)s,%(boss4_id)s,%(boss5_id)s
        )
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_insert_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattlePeriodRepository()
    new_clan_battle_period = ClanBattlePeriod(
        clan_battle_period_name="Test Battle",
        period_type=PeriodType.LIVE,
        date_from=datetime.now(),
        date_to=datetime.now() + timedelta(days=7),
        is_active=True,
        boss1_id=1,
        boss2_id=2,
        boss3_id=None,
        boss4_id=None,
        boss5_id=None,
    )

    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.insert(new_clan_battle_period)

    cursor.execute.assert_called_once()

    expected_query = """
            INSERT INTO clan_battle_period(
                clan_battle_period_name,
                period_type,
                date_from,
                date_to,
                is_active,
                boss1_id,
                boss2_id,
                boss3_id,
                boss4_id,
                boss5_id
            ) 
            VALUES (
                %(clan_battle_period_name)s,%(period_type)s,%(date_from)s,%(date_to)s,%(is_active)s,%(boss1_id)s,%(boss2_id)s,%(boss3_id)s,%(boss4_id)s,%(boss5_id)s
            )
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_latest_cb_period_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattlePeriodRepository()

    # Mock the fetch_one_to_model result to return a sample clan_battle_period object
    cursor.fetchone.return_value = {
        "clan_battle_period_id": 1,
        "clan_battle_period_name": "Clan Battle Period 1",
        "period_type": "LIVE",
        "date_to": datetime(2023, 4, 15),
        "date_from": datetime(2023, 4, 10),
        "is_active": True,
        "boss1_id": 1,
        "boss2_id": None,
        "boss3_id": None,
        "boss4_id": None,
        "boss5_id": None,
    }

    result = repo.get_latest_cb_period()

    assert isinstance(result, ClanBattlePeriod)
    cursor.execute.assert_called_once()
    expected_query = """
        SELECT clan_battle_period_id,
               clan_battle_period_name,
               period_type,
               date_to,
               date_from,
               is_active,
               boss1_id,
               boss2_id,
               boss3_id,
               boss4_id,
               boss5_id
        FROM clan_battle_period
        WHERE DATE_ADD(SYSDATE(), INTERVAL 5 HOUR) BETWEEN date_from AND date_to
        ORDER BY clan_battle_period_id DESC
        LIMIT 1
    """
    actual_query_args, _ = cursor.execute.call_args

    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_latest_cb_period_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattlePeriodRepository()

    # Mock the fetch_one_to_model result to return None (no results)
    cursor.fetchone.return_value = None

    result = repo.get_latest_cb_period()

    assert result is None
    cursor.execute.assert_called_once()

    expected_query = """
            SELECT clan_battle_period_id,
                   clan_battle_period_name,
                   period_type,
                   date_to,
                   date_from,
                   is_active,
                   boss1_id,
                   boss2_id,
                   boss3_id,
                   boss4_id,
                   boss5_id
            FROM clan_battle_period
            WHERE DATE_ADD(SYSDATE(), INTERVAL 5 HOUR) BETWEEN date_from AND date_to
            ORDER BY clan_battle_period_id DESC
            LIMIT 1
        """
    actual_query_args, _ = cursor.execute.call_args

    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_current_active_cb_period_success(mock_db):
    conn, cursor = mock_db

    # Mock the fetch_one_to_model result to return a sample ClanBattlePeriod object
    cursor.fetchone.return_value = {
        "clan_battle_period_id": 1,
        "clan_battle_period_name": "Test Period",
        "period_type": "OFFSEASON",
        "date_to": datetime.now(),
        "date_from": datetime.now() - timedelta(days=7),
        "is_active": True,
        "boss1_id": None,
        "boss2_id": None,
        "boss3_id": None,
        "boss4_id": None,
        "boss5_id": None,
    }

    repo = ClanBattlePeriodRepository()
    result = repo.get_current_active_cb_period()

    assert isinstance(result, ClanBattlePeriod)
    assert result.clan_battle_period_id == 1
    cursor.execute.assert_called_once()


def test_get_current_active_cb_period_no_results(mock_db):
    conn, cursor = mock_db

    # Mock the fetch_one_to_model result to return None (no results)
    cursor.fetchone.return_value = None

    repo = ClanBattlePeriodRepository()
    result = repo.get_current_active_cb_period()

    assert result is None
    cursor.execute.assert_called_once()


def test_get_by_id_success(mock_db):
    conn, cursor = mock_db

    # Mock the connection object and set up a sample result from fetchone
    cursor.fetchone.return_value = {
        "clan_battle_period_id": 1,
        "clan_battle_period_name": "Battle Period 1",
        "period_type": "OFFSEASON",
        "date_to": datetime.now(),
        "date_from": datetime.now() - timedelta(days=7),
        "is_active": True,
        "boss1_id": 101,
        "boss2_id": 102,
        "boss3_id": None,
        "boss4_id": None,
        "boss5_id": None,
    }

    # Create an instance of ClanBattlePeriodRepository
    repo = ClanBattlePeriodRepository()

    # Call the get_by_id method with a sample clan_battle_period_id
    result = repo.get_by_id(1)

    # Assertions to verify the correctness of the result
    assert isinstance(result, ClanBattlePeriod)
    assert result.clan_battle_period_id == 1
    assert result.clan_battle_period_name == "Battle Period 1"
    cursor.execute.assert_called_once()
    expected_query = """
        SELECT clan_battle_period_id,
               clan_battle_period_name,
               period_type,
               date_to,
               date_from,
               is_active,
               boss1_id,
               boss2_id,
               boss3_id,
               boss4_id,
               boss5_id
        FROM clan_battle_period
        WHERE clan_battle_period_id = %(clan_battle_period_id)s
        ORDER BY clan_battle_period_id DESC
        LIMIT 1
    """
    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = (
        str(actual_query_args[0]).replace(" ", "").replace("\n", "")
    )

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_by_id_no_results(mock_db):
    conn, cursor = mock_db

    # Mock the connection object and set up a sample result from fetchone to return None
    cursor.fetchone.return_value = None

    # Create an instance of ClanBattlePeriodRepository
    repo = ClanBattlePeriodRepository()

    # Call the get_by_id method with a sample clan_battle_period_id
    result = repo.get_by_id(1)

    # Assertions to verify the correctness of the result
    assert result is None
    cursor.execute.assert_called_once()


def test_get_by_param_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattlePeriodRepository()
    year = 2023
    month = 10

    # Mock the fetch_one_to_model result to return a sample ClanBattlePeriod object
    clan_battle_period_data = {
        "clan_battle_period_id": 1,
        "clan_battle_period_name": "Month 10",
        "period_type": "OFFSEASON",
        "date_to": datetime(2023, 10, 31),
        "date_from": datetime(2023, 10, 1),
        "is_active": True,
        "boss1_id": None,
        "boss2_id": None,
        "boss3_id": None,
        "boss4_id": None,
        "boss5_id": None,
    }
    cursor.fetchone.return_value = clan_battle_period_data

    result = repo.get_by_param(year, month)

    assert isinstance(result, ClanBattlePeriod)
    assert result.clan_battle_period_id == 1
    assert result.date_from == datetime(2023, 10, 1)
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT clan_battle_period_id,
               clan_battle_period_name,
               period_type,
               date_to,
               date_from,
               is_active,
               boss1_id,
               boss2_id,
               boss3_id,
               boss4_id,
               boss5_id
        FROM clan_battle_period
        WHERE date_from <= LAST_DAY(CONCAT(%(year)s, '-', LPAD(%(month)s, 2, '0'), '-01'))
          AND date_to >= CONCAT(%(year)s, '-', LPAD(%(month)s, 2, '0'), '-01')
        ORDER BY clan_battle_period_id DESC
        LIMIT 1
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(str(actual_query_args[0]))

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_by_param_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattlePeriodRepository()
    year = 2023
    month = 12

    # Mock the fetch_one_to_model result to return None (no results)
    cursor.fetchone.return_value = None

    result = repo.get_by_param(year, month)

    assert result is None
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT clan_battle_period_id,
               clan_battle_period_name,
               period_type,
               date_to,
               date_from,
               is_active,
               boss1_id,
               boss2_id,
               boss3_id,
               boss4_id,
               boss5_id
        FROM clan_battle_period
        WHERE date_from <= LAST_DAY(CONCAT(%(year)s, '-', LPAD(%(month)s, 2, '0'), '-01'))
          AND date_to >= CONCAT(%(year)s, '-', LPAD(%(month)s, 2, '0'), '-01')
        ORDER BY clan_battle_period_id DESC
        LIMIT 1
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(str(actual_query_args[0]))

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_by_id_day_success(mock_db):
    conn, cursor = mock_db

    # Mock the fetchone_to_model result to return a sample clanbattleperiod object
    cursor.fetchone.return_value = {
        "clan_battle_period_id": 1,
        "clan_battle_period_name": "Test Battle",
        "period_type": "OFFSEASON",
        "date_to": datetime(2023, 4, 15),
        "date_from": datetime(2023, 4, 1),
        "is_active": True,
        "boss1_id": None,
        "boss2_id": None,
        "boss3_id": None,
        "boss4_id": None,
        "boss5_id": None,
    }

    repo = ClanBattlePeriodRepository()
    result = repo.get_by_id_day(1)

    assert isinstance(result, ClanBattlePeriodDay)
    assert result.clan_battle_period_id == 1
    cursor.execute.assert_called_once()


def test_get_by_id_day_no_results(mock_db):
    conn, cursor = mock_db

    # Mock the fetchone_to_model result to return None (no results found)
    cursor.fetchone.return_value = None

    repo = ClanBattlePeriodRepository()
    result = repo.get_by_id_day(1)

    assert result is None
    cursor.execute.assert_called_once()


def test_get_by_id_day_query_error(mock_db):
    conn, cursor = mock_db

    # Mock the fetchone_to_model to raise an exception (simulating a query error)
    cursor.fetchone.side_effect = Exception("Database Error")

    repo = ClanBattlePeriodRepository()

    with pytest.raises(Exception) as exc_info:
        result = repo.get_by_id_day(1)

    assert "Database Error" in str(exc_info.value)


def test_get_current_active_cb_period_day_success(mock_db):
    conn, cursor = mock_db

    # Mock the connection object to return a sample clan_battle_period Day result
    cursor.fetchone.return_value = {
        "clan_battle_period_id": 1,
        "clan_battle_period_name": "Test Period",
        "period_type": "OFFSEASON",
        "date_to": datetime(2023, 4, 15),
        "date_from": datetime(2023, 4, 14),
        "is_active": True,
        "boss1_id": None,
        "boss2_id": None,
        "boss3_id": None,
        "boss4_id": None,
        "boss5_id": None,
    }

    repo = ClanBattlePeriodRepository()

    result = repo.get_current_active_cb_period_day()

    assert isinstance(result, ClanBattlePeriodDay)
    assert result.clan_battle_period_id == 1
    cursor.execute.assert_called_once()


def test_get_current_active_cb_period_day_no_results(mock_db):
    conn, cursor = mock_db

    # Mock the connection object to return no results
    cursor.fetchone.return_value = None

    repo = ClanBattlePeriodRepository()

    result = repo.get_current_active_cb_period_day()

    assert result is None
    cursor.execute.assert_called_once()


def test_set_all_inactive_success(mock_db):
    conn, cursor = mock_db

    # Mock the execute result to simulate successful update
    cursor.execute.return_value.rowcount = 3

    repo = ClanBattlePeriodRepository()
    result = repo.set_all_inactive()

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
            UPDATE clan_battle_period
                    SET is_active = 0
                    WHERE is_active = 1
            """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_set_all_inactive_no_changes(mock_db):
    conn, cursor = mock_db

    # Mock the execute result to simulate no changes made
    cursor.execute.return_value.rowcount = 0

    repo = ClanBattlePeriodRepository()
    result = repo.set_all_inactive()

    assert result is True
    cursor.execute.assert_called_once()
    expected_query = """
            UPDATE clan_battle_period
                    SET is_active = 0
                    WHERE is_active = 1
            """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_set_active_by_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattlePeriodRepository()
    clan_battle_period_id = 1

    result = repo.set_active_by_id(clan_battle_period_id)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        UPDATE clan_battle_period
        SET is_active = 1
        WHERE clan_battle_period_id = %(clan_battle_period_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_set_active_by_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattlePeriodRepository()
    clan_battle_period_id = 1

    # Mock the fetch_all_to_model result to return some sample channel_message objects
    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.set_active_by_id(clan_battle_period_id)

    cursor.execute.assert_called_once()


# ClanBattleBossRepository
def test_fetch_clan_battle_boss_by_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossRepository()
    clan_battle_boss_id = 1

    # Mock the fetch_one_to_model result to return a sample clan battle boss object
    cursor.fetchone.return_value = {
        "clan_battle_boss_id": 1,
        "name": "Test Boss",
        "description": "A test boss for testing purposes.",
        "image_path": "/path/to/test/boss/image.png",
        "position": 0,
    }

    result = repo.fetch_clan_battle_boss_by_id(clan_battle_boss_id)

    assert isinstance(result, ClanBattleBoss)
    assert result.clan_battle_boss_id == 1
    assert result.name == "Test Boss"
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT clan_battle_boss_id,
               name,
               description,
               image_path,
               position
        FROM clan_battle_boss
        WHERE clan_battle_boss_id = %(clan_battle_boss_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_fetch_clan_battle_boss_by_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossRepository()
    clan_battle_boss_id = 1

    # Mock the fetch_one_to_model result to return None
    cursor.fetchone.return_value = None

    result = repo.fetch_clan_battle_boss_by_id(clan_battle_boss_id)

    assert result is None
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT clan_battle_boss_id,
               name,
               description,
               image_path,
               position
        FROM clan_battle_boss
        WHERE clan_battle_boss_id = %(clan_battle_boss_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_all_success(mock_db):
    conn, cursor = mock_db

    # Mock the fetch_all_to_model result to return some sample clan battle boss objects
    cursor.fetchall.return_value = [
        {
            "clan_battle_boss_id": 1,
            "name": "Boss A",
            "description": "Description A",
            "image_path": "/path/to/image_a.jpg",
            "position": 0,
        },
        {
            "clan_battle_boss_id": 2,
            "name": "Boss B",
            "description": "Description B",
            "image_path": "/path/to/image_b.jpg",
            "position": 1,
        },
    ]

    repo = ClanBattleBossRepository()
    result = repo.get_all()

    assert len(result) == 2
    assert isinstance(result[0], ClanBattleBoss)
    assert result[0].clan_battle_boss_id == 1
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT clan_battle_boss_id,
               name,
               description,
               image_path,
               position
        FROM clan_battle_boss
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_all_no_results(mock_db):
    conn, cursor = mock_db

    # Mock the fetch_all_to_model result to return no results
    cursor.fetchall.return_value = []

    repo = ClanBattleBossRepository()
    result = repo.get_all()

    assert len(result) == 0
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT clan_battle_boss_id,
               name,
               description,
               image_path,
               position
        FROM clan_battle_boss
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_one_by_position_and_round_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossHealthRepository()
    position = 1
    boss_round = 2

    # Mock the fetch_one_to_model result to return a sample ClanBattleBossHealth object
    mock_clan_battle_boss_health = {
        "clan_battle_boss_health_id": 1,
        "position": 1,
        "round_from": 1,
        "round_to": 3,
        "health": 5000,
    }
    cursor.fetchone.return_value = mock_clan_battle_boss_health

    result = repo.get_one_by_position_and_round(position, boss_round)

    assert isinstance(result, ClanBattleBossHealth)
    assert result.clan_battle_boss_health_id == 1
    assert result.position == position
    assert result.round_from == 1
    assert result.round_to == 3
    assert result.health == 5000


def test_get_one_by_position_and_round_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossHealthRepository()
    position = 1
    boss_round = 2

    # Mock the fetch_one_to_model result to return None (no results)
    cursor.fetchone.return_value = None

    result = repo.get_one_by_position_and_round(position, boss_round)

    assert result is None


# ClanBattleOverallEntryRepository
def test_get_all_by_param_and_round_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    clan_battle_period_id = 2
    clan_battle_boss_id = 3
    boss_round = 4

    # Mock the fetch_all_to_model result to return some sample clan_battle_overall_entry objects
    cursor.fetchall.return_value = [
        {
            "clan_battle_overall_entry_id": 1,
            "guild_id": guild_id,
            "clan_battle_period_id": clan_battle_period_id,
            "clan_battle_boss_id": clan_battle_boss_id,
            "player_id": 5,
            "player_name": "PlayerA",
            "boss_round": boss_round,
            "day": "2023-10-01",
            "attack_type": "CARRY",
            "damage": 100,
            "leftover_time": 90,
            "overall_leftover_entry_id": 6,
            "entry_date": "2023-10-01T14:59:59",
        },
        {
            "clan_battle_overall_entry_id": 7,
            "guild_id": guild_id,
            "clan_battle_period_id": clan_battle_period_id,
            "clan_battle_boss_id": clan_battle_boss_id,
            "player_id": 8,
            "player_name": "PlayerB",
            "boss_round": boss_round,
            "day": "2023-10-01",
            "attack_type": "PATK",
            "damage": 200,
            "leftover_time": 66,
            "overall_leftover_entry_id": 9,
            "entry_date": "2023-10-01T15:59:59",
        },
    ]

    result = repo.get_all_by_param_and_round(
        guild_id, clan_battle_period_id, clan_battle_boss_id, boss_round
    )

    assert len(result) == 2
    assert isinstance(result[0], ClanBattleOverallEntry)
    assert result[0].clan_battle_overall_entry_id == 1
    assert result[0].guild_id == guild_id
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT clan_battle_overall_entry_id,
                guild_id,
                clan_battle_period_id,
                clan_battle_boss_id,
                player_id,
                player_name,
                boss_round,
                day,
                attack_type,
                damage,
                leftover_time,
                overall_leftover_entry_id,
                entry_date
        FROM clan_battle_overall_entry
        WHERE guild_id = %(guild_id)s
        AND clan_battle_period_id = %(clan_battle_period_id)s
        AND clan_battle_boss_id = %(clan_battle_boss_id)s
        AND boss_round = %(boss_round)s
        ORDER BY entry_date
    """

    cursor.execute.assert_called_once()
    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_get_all_by_param_and_round_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    clan_battle_period_id = 2
    clan_battle_boss_id = 3
    boss_round = 4

    # Mock the fetch_all_to_model result to return an empty list
    cursor.fetchall.return_value = []

    result = repo.get_all_by_param_and_round(
        guild_id, clan_battle_period_id, clan_battle_boss_id, boss_round
    )

    assert len(result) == 0
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT clan_battle_overall_entry_id,
                guild_id,
                clan_battle_period_id,
                clan_battle_boss_id,
                player_id,
                player_name,
                boss_round,
                day,
                attack_type,
                damage,
                leftover_time,
                overall_leftover_entry_id,
                entry_date
        FROM clan_battle_overall_entry
        WHERE guild_id = %(guild_id)s
        AND clan_battle_period_id = %(clan_battle_period_id)s
        AND clan_battle_boss_id = %(clan_battle_boss_id)s
        AND boss_round = %(boss_round)s
        ORDER BY entry_date
    """

    cursor.execute.assert_called_once()

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_cb_entry_insert_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    entry = ClanBattleOverallEntry(
        guild_id=1,
        clan_battle_period_id=2,
        clan_battle_boss_id=3,
        player_id=4,
        player_name="Player",
        boss_round=5,
        day=1,
        damage=600,
        attack_type=AttackTypeEnum.PATK,
        leftover_time=66,
        overall_leftover_entry_id=7,
    )
    cursor.lastrowid = 8
    result = repo.insert(entry)

    assert isinstance(result, ClanBattleOverallEntry)
    assert result.clan_battle_overall_entry_id == 8
    cursor.execute.assert_called_once()

    expected_query = """
        INSERT INTO clan_battle_overall_entry (
            guild_id,
            clan_battle_period_id,
            clan_battle_boss_id,
            player_id,
            player_name,
            boss_round,
            day,
            damage,
            attack_type,
            leftover_time, 
            overall_leftover_entry_id, 
            entry_date
        )
        VALUES (
            %(guild_id)s,
            %(clan_battle_period_id)s, 
            %(clan_battle_boss_id)s, 
            %(player_id)s, 
            %(player_name)s,
            %(boss_round)s, 
            %(day)s,
            %(damage)s, 
            %(attack_type)s, 
            %(leftover_time)s,
            %(overall_leftover_entry_id)s,
            SYSDATE()
        )
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(str(actual_query_args[0]))

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_cb_entry_insert_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()

    cursor.execute.side_effect = mariadb.Error("Invalid")
    entry = ClanBattleOverallEntry(
        guild_id=1,
        clan_battle_period_id=2,
        clan_battle_boss_id=3,
        player_id=4,
        player_name="Player",
        boss_round=5,
        day=1,
        damage=600,
        attack_type=AttackTypeEnum.PATK,
        leftover_time=66,
        overall_leftover_entry_id=7,
    )

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.insert(entry)

    cursor.execute.assert_called_once()


def test_update_overall_link_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    cb_overall_entry_id = 1
    overall_leftover_entry_id = 2

    result = repo.update_overall_link(cb_overall_entry_id, overall_leftover_entry_id)

    assert result == True
    cursor.execute.assert_called_once()

    expected_query = """
        UPDATE clan_battle_overall_entry
        SET overall_leftover_entry_id = %(overall_leftover_entry_id)s
        WHERE clan_battle_overall_entry_id = %(cb_overall_entry_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_update_overall_link_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    cb_overall_entry_id = 1
    overall_leftover_entry_id = None
    cursor.execute.side_effect = mariadb.Error("Invalid")
    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.update_overall_link(cb_overall_entry_id, overall_leftover_entry_id)

    cursor.execute.assert_called_once()


def test_get_player_overall_entry_count_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    player_id = 2

    # Mock the fetch_one_to_model result to return some sample data
    cursor.fetchone.return_value = {"entry_count": 5}

    result = repo.get_player_overall_entry_count(guild_id, player_id)

    assert result == 5
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT COUNT(CBOE.clan_battle_overall_entry_id) AS entry_count
        FROM clan_battle_overall_entry CBOE 
            JOIN clan_battle_period CBP ON CBP.clan_battle_period_id = CBOE.clan_battle_period_id
            JOIN clan_battle_boss CBB ON CBOE.clan_battle_boss_id = CBB.clan_battle_boss_id
        WHERE CBOE.guild_id = %(guild_id)s
          AND CBOE.player_id = %(player_id)s
          AND CBOE.attack_type <> 'CARRY'
          AND CBP.is_active = 1
          AND CBOE.entry_date >= IF(CURRENT_TIME() < '05:00:00',
                                        CONCAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'),
                                        CONCAT(CURDATE(), ' 05:00:00'))
          AND CBOE.entry_date < IF(CURRENT_TIME() < '05:00:00',
                                       CONCAT(CURDATE(), ' 05:00:00'),
                                       CONCAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'))
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert normalized_actual_query == normalized_expected_query


def test_get_player_overall_entry_count_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    player_id = 2

    # Mock the fetch_one_to_model result to return no data
    cursor.fetchone.return_value = None

    result = repo.get_player_overall_entry_count(guild_id, player_id)

    assert result == 0
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT COUNT(CBOE.clan_battle_overall_entry_id) AS entry_count
        FROM clan_battle_overall_entry CBOE 
            JOIN clan_battle_period CBP ON CBP.clan_battle_period_id = CBOE.clan_battle_period_id
            JOIN clan_battle_boss CBB ON CBOE.clan_battle_boss_id = CBB.clan_battle_boss_id
        WHERE CBOE.guild_id = %(guild_id)s
          AND CBOE.player_id = %(player_id)s
          AND CBOE.attack_type <> 'CARRY'
          AND CBP.is_active = 1
          AND CBOE.entry_date >= IF(CURRENT_TIME() < '05:00:00',
                                        CONCAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'),
                                        CONCAT(CURDATE(), ' 05:00:00'))
          AND CBOE.entry_date < IF(CURRENT_TIME() < '05:00:00',
                                       CONCAT(CURDATE(), ' 05:00:00'),
                                       CONCAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'))
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert normalized_actual_query == normalized_expected_query


def test_get_leftover_by_guild_id_and_player_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    player_id = 2

    # Mock the fetch_all_to_model result to return some sample clan_battle_overall_entry objects
    cursor.fetchall.return_value = [
        {
            "guild_id": 1,
            "clan_battle_overall_entry_id": 1,
            "clan_battle_boss_id": 3,
            "player_id": 2,
            "attack_type": "PATK",
        },
        {
            "guild_id": 1,
            "clan_battle_overall_entry_id": 2,
            "clan_battle_boss_id": 5,
            "player_id": 6,
            "attack_type": "CARRY",
        },
    ]

    result = repo.get_leftover_by_guild_id_and_player_id(guild_id, player_id)

    assert len(result) == 2
    assert isinstance(result[0], ClanBattleLeftover)
    assert result[0].clan_battle_overall_entry_id == 1
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CBOE.clan_battle_overall_entry_id,
               CBOE.clan_battle_boss_id,
               CBB.name AS clan_battle_boss_name,
               CBOE.player_id,
               CBOE.attack_type,
               CBOE.leftover_time
        FROM clan_battle_overall_entry CBOE
                             JOIN clan_battle_period CBP ON CBP.clan_battle_period_id = CBOE.clan_battle_period_id
                             JOIN clan_battle_boss CBB ON CBOE.clan_battle_boss_id = CBB.clan_battle_boss_id
        WHERE CBOE.guild_id = %(guild_id)s
            AND CBOE.player_id = %(player_id)s
            AND CBOE.leftover_time IS NOT NULL
            AND CBOE.overall_leftover_entry_id IS NULL
            AND CBP.is_active = 1
            AND CONVERT_TZ(CBOE.entry_date, @@session.time_zone, 'Asia/Tokyo') >= IF(CURRENT_TIME() < '05:00:00',
                                        CONCAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'),
                                        CONCAT(CURDATE(), ' 05:00:00'))
            AND CONVERT_TZ(CBOE.entry_date, @@session.time_zone, 'Asia/Tokyo') < IF(CURRENT_TIME() < '05:00:00',
                                       CONCAT(CURDATE(), ' 05:00:00'),
                                       CONCAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'));
        """

    cursor.execute.assert_called_once()
    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert normalized_actual_query == normalized_expected_query


def test_get_leftover_by_guild_id_and_player_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    player_id = 2

    # Mock the fetch_all_to_model result to return an empty list
    cursor.fetchall.return_value = []

    result = repo.get_leftover_by_guild_id_and_player_id(guild_id, player_id)

    assert len(result) == 0
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT CBOE.clan_battle_overall_entry_id,
               CBOE.clan_battle_boss_id,
               CBB.name AS clan_battle_boss_name,
               CBOE.player_id,
               CBOE.attack_type,
               CBOE.leftover_time
        FROM clan_battle_overall_entry CBOE
                             JOIN clan_battle_period CBP ON CBP.clan_battle_period_id = CBOE.clan_battle_period_id
                             JOIN clan_battle_boss CBB ON CBOE.clan_battle_boss_id = CBB.clan_battle_boss_id
        WHERE CBOE.guild_id = %(guild_id)s
            AND CBOE.player_id = %(player_id)s
            AND CBOE.leftover_time IS NOT NULL
            AND CBOE.overall_leftover_entry_id IS NULL
            AND CBP.is_active = 1
            AND CONVERT_TZ(CBOE.entry_date, @@session.time_zone, 'Asia/Tokyo') >= IF(CURRENT_TIME() < '05:00:00',
                                        CONCAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'),
                                        CONCAT(CURDATE(), ' 05:00:00'))
            AND CONVERT_TZ(CBOE.entry_date, @@session.time_zone, 'Asia/Tokyo') < IF(CURRENT_TIME() < '05:00:00',
                                       CONCAT(CURDATE(), ' 05:00:00'),
                                       CONCAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'));
        """

    cursor.execute.assert_called_once()
    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert normalized_actual_query == normalized_expected_query


def test_delete_by_guild_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM clan_battle_overall_entry
        WHERE guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert normalized_actual_query == normalized_expected_query


def test_delete_by_guild_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM clan_battle_overall_entry
        WHERE guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert normalized_actual_query == normalized_expected_query


def test_get_report_entry_by_param_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    year = 2023
    month = 4
    day = 15

    # Mock the fetch_all_to_model result to return some sample clan_battle_report_entry objects
    cursor.fetchall.return_value = [
        {
            "player_name": "Player1",
            "patk_count": 3,
            "matk_count": 2,
            "leftover_count": 0,
            "carry_count": 1,
        },
        {
            "player_name": "Player2",
            "patk_count": 1,
            "matk_count": 4,
            "leftover_count": 2,
            "carry_count": 0,
        },
    ]

    result = repo.get_report_entry_by_param(guild_id, year, month, day)

    assert len(result) == 2
    assert isinstance(result[0], ClanBattleReportEntry)
    assert result[0].player_name == "Player1"
    assert result[0].patk_count == 3
    assert result[0].matk_count == 2
    assert result[0].leftover_count == 0
    assert result[0].carry_count == 1


def test_get_report_entry_by_param_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    year = 2023
    month = 4
    day = 15

    # Mock the fetch_all_to_model result to return an empty list
    cursor.fetchall.return_value = []

    result = repo.get_report_entry_by_param(guild_id, year, month, day)

    assert len(result) == 0


def test_get_report_entry_by_guild_and_period_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    period_id = 2
    day = 3

    # Mock the fetch_all_to_model result to return some sample clan_battle_report_entries objects
    cursor.fetchall.return_value = [
        {
            "player_name": "Player1",
            "patk_count": 5,
            "matk_count": 0,
            "leftover_count": 2,
            "carry_count": 3,
        },
        {
            "player_name": "Player2",
            "patk_count": 0,
            "matk_count": 4,
            "leftover_count": 1,
            "carry_count": 2,
        },
    ]

    result = repo.get_report_entry_by_guild_and_period_id(guild_id, period_id, day)

    assert len(result) == 2
    assert isinstance(result[0], ClanBattleReportEntry)
    assert result[0].player_name == "Player1"
    assert result[0].patk_count == 5
    cursor.execute.assert_called_once()


def test_get_report_entry_by_guild_and_period_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    period_id = 2
    day = 3

    # Mock the fetch_all_to_model result to return no entries
    cursor.fetchall.return_value = []

    result = repo.get_report_entry_by_guild_and_period_id(guild_id, period_id, day)

    assert len(result) == 0


# ClanBattleReportMessageRepository
def test_get_by_guild_period_and_days_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleReportMessageRepository()
    guild_id = 1
    clan_battle_period_id = 2
    day = 3

    # Mock the fetch_one_to_model result to return a sample ClanBattleReportMessage object
    expected_message = ClanBattleReportMessage(
        clan_battle_report_message_id=4,
        guild_id=guild_id,
        clan_battle_period_id=clan_battle_period_id,
        day=day,
        message_id=5,
    )
    cursor.fetchone.return_value = {
        "clan_battle_report_message_id": 4,
        "guild_id": guild_id,
        "clan_battle_period_id": clan_battle_period_id,
        "day": day,
        "message_id": 5,
    }

    result = repo.get_by_guild_period_and_days(guild_id, clan_battle_period_id, day)

    assert result == expected_message
    cursor.execute.assert_called_once()
    assert isinstance(result, ClanBattleReportMessage)


def test_get_by_guild_period_and_days_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleReportMessageRepository()
    guild_id = 1
    clan_battle_period_id = 2
    day = 3

    # Mock the fetch_one_to_model result to return None (no results)
    cursor.fetchone.return_value = None

    result = repo.get_by_guild_period_and_days(guild_id, clan_battle_period_id, day)

    assert result is None
    cursor.execute.assert_called_once()


def test_get_last_by_guild_period_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleReportMessageRepository()
    guild_id = 1
    clan_battle_period_id = 2
    day = 3

    # Mock the fetch_one_to_model result to return a sample ClanBattleReportMessage object
    sample_message = {
        "clan_battle_report_message_id": 4,
        "guild_id": guild_id,
        "clan_battle_period_id": clan_battle_period_id,
        "day": day,
        "message_id": 5,
    }
    cursor.fetchone.return_value = sample_message

    result = repo.get_last_by_guild_period(guild_id, clan_battle_period_id, day)

    assert isinstance(result, ClanBattleReportMessage)
    assert (
        result.clan_battle_report_message_id
        == sample_message["clan_battle_report_message_id"]
    )
    assert result.guild_id == guild_id
    assert result.clan_battle_period_id == clan_battle_period_id
    assert result.day == day
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT clan_battle_report_message_id,
               guild_id,
               clan_battle_period_id,
               day,
               message_id
        FROM clan_battle_report_message
        WHERE guild_id = %(guild_id)s
          AND clan_battle_period_id = %(clan_battle_period_id)s
          AND day = %(day)s
        ORDER BY clan_battle_report_message_id DESC
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert normalized_actual_query == normalized_expected_query


def test_get_last_by_guild_period_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleReportMessageRepository()
    guild_id = 1
    clan_battle_period_id = 2
    day = 3

    # Mock the fetch_one_to_model result to return None
    cursor.fetchone.return_value = None

    result = repo.get_last_by_guild_period(guild_id, clan_battle_period_id, day)

    assert result is None
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT clan_battle_report_message_id,
               guild_id,
               clan_battle_period_id,
               day,
               message_id
        FROM clan_battle_report_message
        WHERE guild_id = %(guild_id)s
          AND clan_battle_period_id = %(clan_battle_period_id)s
          AND day = %(day)s
        ORDER BY clan_battle_report_message_id DESC
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert normalized_actual_query == normalized_expected_query


def test_cb_report_message_insert_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleReportMessageRepository()
    clan_battle_report_message = ClanBattleReportMessage(
        guild_id=1,
        clan_battle_period_id=2,
        day=1,
        message_id=3,
    )
    cursor.lastrowid = 1
    result = repo.insert(clan_battle_report_message)

    assert isinstance(result, ClanBattleReportMessage)
    assert result.clan_battle_report_message_id == 1
    cursor.execute.assert_called_once()

    expected_query = """
        INSERT INTO clan_battle_report_message 
        (
            guild_id,
            clan_battle_period_id,
            day,
            message_id
        )
        VALUES 
        (
            %(guild_id)s,
            %(clan_battle_period_id)s,
            %(day)s,
            %(message_id)s
        )
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_cb_report_message_insert_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleReportMessageRepository()
    clan_battle_report_message = ClanBattleReportMessage(
        guild_id=None,
        clan_battle_period_id=2,
        day=2,
        message_id=3,
    )

    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.insert(clan_battle_report_message)


def test_delete_by_guild_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleReportMessageRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM clan_battle_report_message
        WHERE guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {normalized_expected_query}, Actual: {normalized_actual_query}"


def test_delete_by_guild_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleReportMessageRepository()
    guild_id = 1

    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.delete_by_guild_id(guild_id)

    cursor.execute.assert_called_once()


# GuildPlayerRepository
def test_batch_insert_success(mock_db):
    conn, cursor = mock_db

    repo = GuildPlayerRepository()
    data = [(1, 2, "John"), (3, 4, "Jane")]

    result = repo.batch_insert(data)

    assert result is True


def test_batch_insert_failure(mock_db):
    conn, cursor = mock_db

    repo = GuildPlayerRepository()
    data = [(1, 2, "John"), None]

    cursor.executemany.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.batch_insert(data)

    cursor.executemany.assert_called_once()


def test_guild_player_delete_by_guild_id_success(mock_db):
    conn, cursor = mock_db

    repo = GuildPlayerRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM guild_player
        WHERE guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {normalized_expected_query}"


def test_guild_player_delete_by_guild_id_no_rows(mock_db):
    conn, cursor = mock_db

    repo = GuildPlayerRepository()
    guild_id = 1

    # Mock the fetch_all_to_model result to return an empty list
    cursor.fetchone.return_value = None

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM guild_player
        WHERE guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {normalized_expected_query}"


def test_guild_player_get_all_by_guild_id_success(mock_db):
    conn, cursor = mock_db

    # Mock the fetch_all_to_model result to return some sample GuildPlayer objects
    cursor.fetchall.return_value = [
        {"guild_id": 1, "player_id": 2, "player_name": "Alice"},
        {"guild_id": 1, "player_id": 3, "player_name": "Bob"},
    ]

    repo = GuildPlayerRepository()
    guild_id = 1

    result = repo.get_all_by_guild_id(guild_id)

    assert len(result) == 2
    assert isinstance(result[0], GuildPlayer)
    assert result[0].guild_id == 1
    assert result[0].player_id == 2
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT guild_id, player_id, player_name 
        FROM guild_player
        WHERE guild_id = %(guild_id)s
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_guild_player_get_all_by_guild_id_no_results(mock_db):
    conn, cursor = mock_db

    # Mock the fetch_all_to_model result to return an empty list of GuildPlayer objects
    cursor.fetchall.return_value = []

    repo = GuildPlayerRepository()
    guild_id = 1

    result = repo.get_all_by_guild_id(guild_id)

    assert len(result) == 0
    cursor.execute.assert_called_once()

    expected_query = """
        SELECT guild_id, player_id, player_name 
        FROM guild_player
        WHERE guild_id = %(guild_id)s
    """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {str(actual_query_args[0])}"


def test_error_log_insert_success(mock_container, mock_db):
    conn, cursor = mock_db
    mock_db_pool = MagicMock(spec=DatabasePool)
    mock_db_pool.__enter__.return_value = conn
    mock_db_pool.__exit__.return_value = None
    mock_container.db_pool.override(providers.Object(mock_db_pool))
    repo = ErrorLogRepository()
    guild_id = 1
    identifier = "test_identifier"
    exception = "test_exception"
    stacktrace = "test_stacktrace"
    result = repo.insert(guild_id, identifier, exception, stacktrace)
    assert result is True
    cursor.execute.assert_called_once()
    expected_query = """
        INSERT INTO error_log (guild_id, identifier, exception, stacktrace) VALUES 
        (%(guild_id)s, %(identifier)s, %(exception)s, %(stacktrace)s)
    """
    expected_params = {
        "guild_id": guild_id,
        "identifier": identifier,
        "exception": exception,
        "stacktrace": stacktrace,
    }
    actual_query, actual_params = cursor.execute.call_args[0]
    assert normalize_sql(actual_query) == normalize_sql(expected_query)
    assert actual_params == expected_params
    conn.commit.assert_called_once()


def test_error_log_insert_failure(mock_container, mock_db):
    conn, cursor = mock_db
    mock_db_pool = MagicMock(spec=DatabasePool)
    mock_db_pool.__enter__.return_value = conn
    mock_db_pool.__exit__.return_value = None
    mock_container.db_pool.override(providers.Object(mock_db_pool))
    repo = ErrorLogRepository()
    guild_id = 1
    identifier = "test_identifier"
    exception = "test_exception"
    stacktrace = "test_stacktrace"
    cursor.execute.side_effect = mariadb.Error("Invalid")
    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.insert(guild_id, identifier, exception, stacktrace)
    cursor.execute.assert_called_once()
    expected_query = """
        INSERT INTO error_log (guild_id, identifier, exception, stacktrace) VALUES 
        (%(guild_id)s, %(identifier)s, %(exception)s, %(stacktrace)s)
    """
    expected_params = {
        "guild_id": guild_id,
        "identifier": identifier,
        "exception": exception,
        "stacktrace": stacktrace,
    }
    actual_query, actual_params = cursor.execute.call_args[0]
    assert normalize_sql(actual_query) == normalize_sql(expected_query)
    assert actual_params == expected_params
    conn.commit.assert_not_called()


def test_error_log_delete_by_guild_id_success(mock_db):
    conn, cursor = mock_db

    repo = ErrorLogRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM error_log
        WHERE guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {normalized_expected_query}"


def test_error_log_delete_by_guild_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ErrorLogRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()

    expected_query = """
        DELETE FROM error_log
        WHERE guild_id = %(guild_id)s
        """

    actual_query_args, _ = cursor.execute.call_args

    # Normalize the expected and actual queries to remove whitespace for comparison
    normalized_expected_query = normalize_sql(expected_query)
    normalized_actual_query = normalize_sql(actual_query_args[0])

    assert (
        normalized_actual_query == normalized_expected_query
    ), f"Expected: {expected_query}, Actual: {normalized_expected_query}"
