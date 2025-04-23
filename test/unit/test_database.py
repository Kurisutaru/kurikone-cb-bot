from unittest.mock import MagicMock, patch

import mariadb
import pytest
from dependency_injector import providers

from config import GlobalConfig
from database import DatabasePool, db_connection_context
from logger import KuriLogger


@pytest.fixture
def mock_pool():
    with patch("database.PooledDB") as mock_pooled_db:
        mock_pool = MagicMock()
        mock_pooled_db.return_value = mock_pool
        yield mock_pool


@patch("database.PooledDB")
def test_pool_initialization(mock_pool_db, mock_container, mock_pool):
    mock_logger = MagicMock(spec=KuriLogger)
    mock_config = MagicMock(spec=GlobalConfig)
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


def test_get_connection(mock_container):
    # Mock dependencies
    mock_logger = MagicMock(spec=KuriLogger)

    # Override container dependencies
    mock_container.logger.override(providers.Object(mock_logger))

    # Mock PooledDB to return a mock pool
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.connection.return_value = mock_conn

    with patch("database.PooledDB", return_value=mock_pool):
        with patch("mariadb.connect") as mock_connect:
            mock_connect.return_value = MagicMock()  # Simulate successful connection
            db_pool = mock_container.db_pool()

            # Test get_connection
            conn = db_pool.get_connection()
            assert conn == mock_conn
            mock_pool.connection.assert_called_once()

    # Verify logger was called
    mock_logger.info.assert_called_with("Connection pool initialized with size: 20")


def test_context_manager(mock_container):
    # Mock dependencies
    mock_logger = MagicMock(spec=KuriLogger)

    # Override container dependencies
    mock_container.logger.override(providers.Object(mock_logger))

    # Mock PooledDB to return a mock pool
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.connection.return_value = mock_conn

    with patch("database.PooledDB", return_value=mock_pool):
        with patch("mariadb.connect") as mock_connect:
            mock_connect.return_value = MagicMock()  # Simulate successful connection
            db_pool = mock_container.db_pool()

            # Test context manager
            with db_pool as conn:
                assert conn == mock_conn
            mock_pool.connection.assert_called_once()

    # Verify logger was called
    mock_logger.info.assert_called_with("Connection pool initialized with size: 20")


def test_get_connection_function_with_context(mock_container):
    # Mock dependencies
    mock_logger = MagicMock(spec=KuriLogger)
    mock_config = MagicMock(spec=GlobalConfig)
    mock_config.MAX_POOL_SIZE = 20

    # Override container dependencies
    mock_container.logger.override(providers.Object(mock_logger))
    mock_container.config.override(providers.Object(mock_config))

    # Mock PooledDB and connection
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.connection.return_value = mock_conn

    with patch("database.PooledDB", return_value=mock_pool):
        with patch("mariadb.connect") as mock_connect:
            mock_connect.return_value = MagicMock()
            db_pool = mock_container.db_pool()

            from database import (
                get_connection,
                set_connection_context,
                reset_connection_context,
            )

            # No context set
            conn, should_close = get_connection()
            assert conn == mock_conn
            assert should_close is True
            mock_pool.connection.assert_called_once()

            # Context set
            set_connection_context(mock_conn)
            conn2, should_close2 = get_connection()
            assert conn2 == mock_conn
            assert should_close2 is False
            mock_pool.connection.assert_called_once()  # No new connection

            reset_connection_context()
            assert db_connection_context.get() is None

    mock_logger.info.assert_called_with("Connection pool initialized with size: 20")


def test_connection_failure(mock_container):
    # Mock dependencies
    mock_logger = MagicMock(spec=KuriLogger)

    # Override container dependencies
    mock_container.logger.override(providers.Object(mock_logger))

    # Patch PooledDB in the database module's namespace
    with patch("database.PooledDB", side_effect=mariadb.Error("Connection failed")):
        # Also patch mariadb.connect to prevent real connections
        with patch("mariadb.connect", side_effect=mariadb.Error("Connection failed")):
            with pytest.raises(mariadb.Error, match="Connection failed"):
                mock_container.db_pool()  # Instantiate via DI container

    # Verify logger was called
    mock_logger.critical.assert_called_with(
        "Failed to establish a database connection: Connection failed"
    )


def test_context_manager_exit_with_exception(mock_container):
    # Mock dependencies
    mock_logger = MagicMock(spec=KuriLogger)
    mock_config = MagicMock(spec=GlobalConfig)
    mock_container.logger.override(providers.Object(mock_logger))
    mock_container.config.override(providers.Object(mock_config))

    with patch("database.PooledDB") as mock_pooled_db:
        with patch("mariadb.connect") as mock_connect:
            mock_connect.return_value = MagicMock()
            mock_pooled_db.return_value = MagicMock()
            db_pool = mock_container.db_pool()

            with patch("builtins.print") as mock_print:
                try:
                    with db_pool:
                        raise ValueError("boom")
                except ValueError:
                    pass
                mock_print.assert_called_with("Exception in context: boom")


def test_get_connection_failure(mock_container):
    mock_logger = MagicMock(spec=KuriLogger)
    mock_config = MagicMock(spec=GlobalConfig)

    mock_container.logger.override(providers.Object(mock_logger))
    mock_container.config.override(providers.Object(mock_config))

    mock_pool = MagicMock()
    mock_pool.connection.side_effect = mariadb.Error("Connection error")

    with patch("database.PooledDB", return_value=mock_pool):
        with patch("mariadb.connect") as mock_connect:
            mock_connect.return_value = MagicMock()
            db_pool = mock_container.db_pool()

            with pytest.raises(mariadb.Error, match="Connection error"):
                db_pool.get_connection()
