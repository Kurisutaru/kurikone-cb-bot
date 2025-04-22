import pytest
from unittest.mock import MagicMock, call, patch
import mariadb
from dbutils.pooled_db import PooledDB
from dependency_injector import providers

from config import GlobalConfig
from database import DatabasePool
from logger import KuriLogger


@pytest.fixture
def mock_pool():
    with patch("database.PooledDB") as mock_pooled_db:
        mock_pool = MagicMock()
        mock_pooled_db.return_value = mock_pool
        yield mock_pool


@pytest.fixture
def db_pool(mock_container, mock_pool):
    from database import DatabasePool

    # Bypassing dependency injector for simplicity; directly passing mocks
    instance = DatabasePool.__new__(DatabasePool)
    instance._pool = mock_pool
    DatabasePool._instance = instance
    return instance


def test_singleton_pattern(mock_container):
    mock_logger = MagicMock(spec=KuriLogger)
    mock_config = MagicMock(spec=GlobalConfig)

    from database import DatabasePool

    DatabasePool._instance = None  # Reset singleton

    # Mock PooledDB and mariadb.connect to avoid real connections
    with (
        patch("database.mariadb.connect") as mock_connect,
        patch("database.PooledDB") as mock_pooled_db,
    ):
        mock_container.logger.override(providers.Object(mock_logger))
        mock_container.config.override(mock_config)

        # Create instances (should trigger PooledDB initialization)
        instance1 = DatabasePool()
        instance2 = DatabasePool()

        # Verify singleton behavior
        assert instance1 is instance2
        assert DatabasePool._instance is not None

        # Ensure PooledDB was called with mocked config values
        mock_pooled_db.assert_called_once()


@patch("database.PooledDB")
def test_pool_initialization(mock_pool_db, mock_container, mock_pool):
    mock_logger = MagicMock()
    mock_config = MagicMock()
    mock_config.MAX_POOL_SIZE = 5
    mock_config.DB_HOST = "localhost"
    mock_config.DB_USER = "user"
    mock_config.DB_PASSWORD = "pass"
    mock_config.DB_NAME = "test_db"
    mock_config.DB_PORT = 3306

    mock_container.logger.override(providers.Object(mock_logger))
    mock_container.config.override(mock_config)

    DatabasePool._instance = None  # Reset singleton
    instance = DatabasePool()

    mock_pool_db.assert_called_once_with(
        creator=mariadb.connect,
        maxconnections=mock_config.MAX_POOL_SIZE,
        mincached=2,
        maxcached=10,
        maxusage=5,
        blocking=True,
        host=mock_config.DB_HOST,
        user=mock_config.DB_USER,
        password=mock_config.DB_PASSWORD,
        database=mock_config.DB_NAME,
        port=mock_config.DB_PORT,
        setsession=["SET SESSION time_zone = 'Asia/Tokyo'"],
        reset=True,
        failures=None,
        ping=7,
    )
    mock_logger.info.assert_called_with(
        f"Connection pool initialized with size: {mock_config.MAX_POOL_SIZE}"
    )


def test_get_connection(db_pool):
    mock_conn = MagicMock()
    db_pool._pool.connection.return_value = mock_conn
    conn = db_pool.get_connection()
    assert conn == mock_conn
    db_pool._pool.connection.assert_called_once()


def test_context_manager(db_pool):
    mock_conn = MagicMock()
    db_pool._pool.connection.return_value = mock_conn
    with db_pool as conn:
        assert conn == mock_conn
    db_pool._pool.connection.assert_called_once()


def test_get_connection_function_with_context(mock_container, db_pool):
    # Create mock db_pool and connection
    mock_conn = MagicMock()
    mock_pool = MagicMock()
    mock_pool.connection.return_value = mock_conn

    from database import (
        DatabasePool,
        get_connection,
        set_connection_context,
        reset_connection_context,
    )

    db_pool = MagicMock(spec=DatabasePool)
    db_pool.get_connection.return_value = mock_conn
    db_pool._pool = mock_pool

    mock_container.db_pool.override(providers.Object(db_pool))

    # --- No context set ---
    conn, should_close = get_connection()
    assert conn == mock_conn
    assert should_close is True

    # --- Context set ---
    set_connection_context(mock_conn)
    conn2, should_close2 = get_connection()
    assert conn2 == mock_conn
    assert should_close2 is False

    reset_connection_context()


def test_connection_failure(mock_container):
    # Reset the singleton instance
    DatabasePool._instance = None

    mock_logger = MagicMock()
    mock_container.logger.override(providers.Object(mock_logger))

    with patch("database.PooledDB", side_effect=Exception("Connection failed")):
        with pytest.raises(SystemExit):
            DatabasePool()

    mock_logger.critical.assert_called_with("Failed to establish a database connection")


def test_context_manager_exit_clean(mock_container):
    db_pool = DatabasePool()
    mock_conn = MagicMock()
    db_pool.get_connection = MagicMock(return_value=mock_conn)

    with db_pool as conn:
        assert conn == mock_conn


def test_context_exit_called(mock_container):
    db_pool = DatabasePool()

    with patch.object(DatabasePool, "__exit__", wraps=db_pool.__exit__) as mock_exit:
        with db_pool:
            pass
        mock_exit.assert_called_once()


def test_context_manager_exit_with_exception(mock_container):
    db_pool = DatabasePool()

    with patch("builtins.print") as mock_print:
        try:
            with db_pool:
                raise ValueError("boom")
        except ValueError:
            pass

        mock_print.assert_called_with("Exception in context: boom")
