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
    ClanBattleBossEntries,
)
from repository import (
    fetch_one_to_model,
    fetch_all_to_model,
    connection_context,
    GuildRepository,
    ChannelRepository,
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


def test_get_by_channel_id_success(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = {
        "channel_id": 1,
        "guild_id": 1,
        "channel_type": "BOSS1",
        "message_id": 1,
    }
    repo = ChannelRepository()

    result = repo.get_by_channel_id(1)

    assert result.channel_id == 1
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_by_channel_id_none_result(mock_db):
    conn, cursor = mock_db
    cursor.fetchone.return_value = None
    repo = ChannelRepository()

    result = repo.get_by_channel_id(1)

    assert result is None
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_by_channel_id_with_boss_success(mock_db):
    conn, cursor = mock_db
    channel_id = 1
    cursor.fetchone.return_value = {
        "channel_id": channel_id,
        "guild_id": 456,
        "channel_type": "BOSS1",
        "message_id": 789,
        "boss_id": 1,
    }
    repo = ChannelRepository()

    result = repo.get_by_channel_id_with_boss(channel_id)

    assert result.channel_id == channel_id
    cursor.execute.assert_called_once()
    cursor.fetchone.assert_called_once()


def test_get_by_channel_id_with_boss_result(mock_db):
    conn, cursor = mock_db
    channel_id = 1
    cursor.fetchone.return_value = None
    repo = ChannelRepository()

    result = repo.get_by_channel_id(channel_id)

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


def test_update_channel_message_success(mock_db):
    conn, cursor = mock_db
    repo = ChannelRepository()

    repo.update_channel_message(1, 1)

    cursor.execute.assert_called_once()


def test_update_channel_message_failed(mock_db):
    conn, cursor = mock_db
    cursor.execute.side_effect = AttributeError("Invalid")
    repo = ChannelRepository()

    with pytest.raises(AttributeError):
        repo.update_channel_message(1, 1)

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


# Clan Battle Boss Repository
def test_insert_clan_battle_boss_entry_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry = ClanBattleBossEntries(
        guild_id=1,
        clan_battle_period_id=3,
        clan_battle_boss_id=4,
        boss_name="Example Boss",
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


def test_insert_clan_battle_boss_entry_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()

    cursor.execute.side_effect = Exception("Insert operation failed")

    clan_battle_boss_entry = ClanBattleBossEntries(
        guild_id=1,
        clan_battle_period_id=3,
        clan_battle_boss_id=4,
        boss_name="Example Boss",
        image_path="/path/to/image.png",
        boss_round=5,
        current_health=6000,
        max_health=8000,
    )

    with pytest.raises(Exception, match="Insert operation failed"):
        repo.insert_clan_battle_boss_entry(clan_battle_boss_entry)

    cursor.execute.assert_called_once()


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


def test_get_boss_entry_by_param_round_success(mock_db):
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

    result = repo.get_boss_entry_by_param_round(
        guild_id, clan_battle_period_id, clan_battle_boss_id, 1
    )

    assert isinstance(result, ClanBattleBossEntry)
    assert result.clan_battle_boss_entry_id == 4
    assert result.guild_id == guild_id
    cursor.execute.assert_called_once()


def test_get_boss_entry_by_param_round_no_result(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()

    guild_id = 1
    clan_battle_period_id = 2
    clan_battle_boss_id = 3

    # Mock the fetch_one_to_model result to return None
    cursor.fetchone.return_value = None

    result = repo.get_boss_entry_by_param_round(
        guild_id, clan_battle_period_id, clan_battle_boss_id, 1
    )

    assert result is None


def test_get_boss_entry_active_cb_by_param_success(mock_db):
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

    result = repo.get_boss_entry_active_cb_by_param(guild_id, clan_battle_boss_id)

    assert isinstance(result, ClanBattleBossEntry)
    assert result.clan_battle_boss_entry_id == 4
    assert result.guild_id == guild_id
    cursor.execute.assert_called_once()


def test_get_boss_entry_active_cb_by_param_no_result(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()

    guild_id = 1
    clan_battle_period_id = 2
    clan_battle_boss_id = 3

    # Mock the fetch_one_to_model result to return None
    cursor.fetchone.return_value = None

    result = repo.get_boss_entry_active_cb_by_param(guild_id, clan_battle_boss_id)

    assert result is None


def test_get_boss_entry_active_cb_by_channel_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()

    guild_id = 1
    clan_battle_period_id = 2
    clan_battle_boss_id = 3
    channel_id = 4

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

    result = repo.get_boss_entry_active_cb_by_channel_id(channel_id)

    assert isinstance(result, ClanBattleBossEntry)
    assert result.clan_battle_boss_entry_id == 4
    assert result.guild_id == guild_id
    cursor.execute.assert_called_once()


def test_get_boss_entry_active_cb_by_channel_id_no_result(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    channel_id = 1

    # Mock the fetch_one_to_model result to return None
    cursor.fetchone.return_value = None

    result = repo.get_boss_entry_active_cb_by_channel_id(channel_id)

    assert result is None


def test_update_on_attack_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry_id = 1
    current_health = 50

    result = repo.update_on_attack(clan_battle_boss_entry_id, current_health)

    assert result is True
    cursor.execute.assert_called_once()


def test_update_on_attack_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry_id = 1
    current_health = -10
    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid") as e:
        repo.update_on_attack(clan_battle_boss_entry_id, current_health)

    cursor.execute.assert_called_once()


def test_set_inactive_by_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry_id = 1

    result = repo.set_active_by_id(clan_battle_boss_entry_id, True)

    assert result is True
    cursor.execute.assert_called_once()


def test_set_inactive_by_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry_id = 1
    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid") as e:
        repo.set_active_by_id(clan_battle_boss_entry_id, False)

    cursor.execute.assert_called_once()


def test_set_boss_entry_all_inactive_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry_id = 1

    result = repo.set_boss_entry_all_inactive()

    assert result is True
    cursor.execute.assert_called_once()


def test_set_boss_entry_all_inactive_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    clan_battle_boss_entry_id = 1
    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid") as e:
        repo.set_boss_entry_all_inactive()

    cursor.execute.assert_called_once()


def test_cb_entry_delete_by_guild_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()


def test_cb_entry_delete_by_guild_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossEntryRepository()
    guild_id = 1

    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid") as e:
        repo.delete_by_guild_id(guild_id)

    cursor.execute.assert_called_once()


# Clan Battle Boss Book
def test_get_all_by_message_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    guild_id = 1
    entry_id = 1

    # Mock the fetch_all_to_model result to return some sample clan_battle_boss_book objects
    cursor.fetchall.return_value = [
        {
            "clan_battle_boss_book_id": 1,
            "clan_battle_boss_entry_id": 1,
            "guild_id": 1,
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
            "clan_battle_boss_entry_id": 2,
            "guild_id": 2,
            "player_id": 10,
            "player_name": "Jane",
            "attack_type": "MATK",
            "damage": 450,
            "clan_battle_overall_entry_id": 11,
            "leftover_time": 60,
            "entry_date": datetime(2023, 4, 2, 10, 30),
        },
    ]

    result = repo.get_all_by_entry_id(guild_id, entry_id)

    assert len(result) == 2
    assert isinstance(result[0], ClanBattleBossBook)
    assert result[0].clan_battle_boss_book_id == 1
    assert result[0].player_name == "John"
    cursor.execute.assert_called_once()


def test_get_all_by_message_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    guild_id = 1
    entry_id = 1

    # Mock fetch_all_to_model result to return an empty list (no results)
    cursor.fetchall.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid") as e:
        result = repo.get_all_by_entry_id(guild_id, entry_id)

    cursor.execute.assert_called_once()


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

    result = repo.get_player_book_by_entry_id(message_id, player_id)

    assert isinstance(result, ClanBattleBossBook)
    assert result.clan_battle_boss_book_id == 1
    cursor.execute.assert_called_once()


def test_get_player_book_entry_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    message_id = 12345
    player_id = 67890

    # Mock the fetch_one_to_model result to return None
    cursor.fetchone.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.get_player_book_by_entry_id(message_id, player_id)

    cursor.execute.assert_called_once()


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


def test_delete_book_by_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    clan_battle_boss_book_id = 1

    result = repo.delete_book_by_id(clan_battle_boss_book_id)

    assert result == True
    cursor.execute.assert_called_once()


def test_delete_book_by_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    clan_battle_boss_book_id = 1

    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.delete_book_by_id(clan_battle_boss_book_id)

    cursor.execute.assert_called_once()


def test_delete_book_by_entry_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    entry_id = 1

    result = repo.delete_book_by_entry_id(entry_id)

    assert result == True
    cursor.execute.assert_called_once()


def test_delete_book_by_entry_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    entry_id = 1

    cursor.execute.side_effect = mariadb.Error("Invalid")

    with pytest.raises(mariadb.Error, match="Invalid"):
        repo.delete_book_by_entry_id(entry_id)

    cursor.execute.assert_called_once()


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


def test_update_damage_boss_book_by_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    clan_battle_boss_book_id = 1
    damage = None

    result = repo.update_damage_boss_book_by_id(clan_battle_boss_book_id, damage)

    assert result is True
    cursor.execute.assert_called_once()


def test_cb_repo_delete_by_guild_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()


def test_cb_repo_delete_by_guild_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossBookRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()


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


def test_get_latest_cb_period_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattlePeriodRepository()

    # Mock the fetch_one_to_model result to return None (no results)
    cursor.fetchone.return_value = None

    result = repo.get_latest_cb_period()

    assert result is None
    cursor.execute.assert_called_once()


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


def test_set_period_all_inactive_success(mock_db):
    conn, cursor = mock_db

    # Mock the execute result to simulate successful update
    cursor.execute.return_value.rowcount = 3

    repo = ClanBattlePeriodRepository()
    result = repo.set_period_all_inactive()

    assert result is True
    cursor.execute.assert_called_once()


def test_set_period_all_inactive_no_changes(mock_db):
    conn, cursor = mock_db

    # Mock the execute result to simulate no changes made
    cursor.execute.return_value.rowcount = 0

    repo = ClanBattlePeriodRepository()
    result = repo.set_period_all_inactive()

    assert result is True
    cursor.execute.assert_called_once()


def test_set_active_by_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattlePeriodRepository()
    clan_battle_period_id = 1

    result = repo.set_active_by_id(clan_battle_period_id)

    assert result is True
    cursor.execute.assert_called_once()


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


def test_fetch_clan_battle_boss_by_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossRepository()
    clan_battle_boss_id = 1

    # Mock the fetch_one_to_model result to return None
    cursor.fetchone.return_value = None

    result = repo.fetch_clan_battle_boss_by_id(clan_battle_boss_id)

    assert result is None
    cursor.execute.assert_called_once()


def test_fetch_clan_battle_boss_by_id_and_round_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossRepository()
    clan_battle_boss_id = 1
    round = 1

    # Mock the fetch_one_to_model result to return a sample clan battle boss object
    cursor.fetchone.return_value = {
        "clan_battle_boss_id": 1,
        "name": "Test Boss",
        "description": "A test boss for testing purposes.",
        "image_path": "/path/to/test/boss/image.png",
        "position": 0,
    }

    result = repo.fetch_clan_battle_boss_by_id_and_round(clan_battle_boss_id, round)

    assert isinstance(result, ClanBattleBoss)
    assert result.clan_battle_boss_id == 1
    assert result.name == "Test Boss"
    cursor.execute.assert_called_once()


def test_fetch_clan_battle_boss_by_id_and_round_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleBossRepository()
    clan_battle_boss_id = 1
    round = 1

    # Mock the fetch_one_to_model result to return None
    cursor.fetchone.return_value = None

    result = repo.fetch_clan_battle_boss_by_id_and_round(clan_battle_boss_id, round)

    assert result is None
    cursor.execute.assert_called_once()


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


def test_get_all_no_results(mock_db):
    conn, cursor = mock_db

    # Mock the fetch_all_to_model result to return no results
    cursor.fetchall.return_value = []

    repo = ClanBattleBossRepository()
    result = repo.get_all()

    assert len(result) == 0
    cursor.execute.assert_called_once()


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


def test_get_all_by_boss_entry_id_success(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    clan_battle_period_id = 2
    clan_battle_boss_id = 3
    boss_round = 4
    clan_battle_boss_entry_id = 5

    # Mock the fetch_all_to_model result to return some sample clan_battle_overall_entry objects
    cursor.fetchall.return_value = [
        {
            "clan_battle_overall_entry_id": 1,
            "guild_id": guild_id,
            "clan_battle_boss_entry_id": clan_battle_boss_entry_id,
            "clan_battle_": clan_battle_period_id,
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
            "clan_battle_boss_entry_id": clan_battle_boss_entry_id,
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

    result = repo.get_all_by_boss_entry_id(guild_id, clan_battle_boss_entry_id)

    assert len(result) == 2
    assert isinstance(result[0], ClanBattleOverallEntry)
    assert result[0].clan_battle_overall_entry_id == 1
    assert result[0].guild_id == guild_id
    cursor.execute.assert_called_once()


def test_get_all_by_boss_entry_id_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    clan_battle_boss_entry_id = 2

    # Mock the fetch_all_to_model result to return an empty list
    cursor.fetchall.return_value = []

    result = repo.get_all_by_boss_entry_id(guild_id, clan_battle_boss_entry_id)

    assert len(result) == 0
    cursor.execute.assert_called_once()


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


def test_get_player_overall_entry_count_failure(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1
    player_id = 2

    # Mock the fetch_one_to_model result to return no data
    cursor.fetchone.return_value = None

    result = repo.get_player_overall_entry_count(guild_id, player_id)


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


# def test_delete_by_guild_id_success(mock_db):
#     conn, cursor = mock_db
#
#     repo = ClanBattleOverallEntryRepository()
#     guild_id = 1
#
#     result = repo.delete_by_guild_id(guild_id)
#
#     assert result is True
#     cursor.execute.assert_called_once()


def test_delete_by_guild_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ClanBattleOverallEntryRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()


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


def test_guild_player_delete_by_guild_id_no_rows(mock_db):
    conn, cursor = mock_db

    repo = GuildPlayerRepository()
    guild_id = 1

    # Mock the fetch_all_to_model result to return an empty list
    cursor.fetchone.return_value = None

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()


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


def test_guild_player_get_all_by_guild_id_no_results(mock_db):
    conn, cursor = mock_db

    # Mock the fetch_all_to_model result to return an empty list of GuildPlayer objects
    cursor.fetchall.return_value = []

    repo = GuildPlayerRepository()
    guild_id = 1

    result = repo.get_all_by_guild_id(guild_id)

    assert len(result) == 0
    cursor.execute.assert_called_once()


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


def test_error_log_delete_by_guild_id_no_results(mock_db):
    conn, cursor = mock_db

    repo = ErrorLogRepository()
    guild_id = 1

    result = repo.delete_by_guild_id(guild_id)

    assert result is True
    cursor.execute.assert_called_once()
