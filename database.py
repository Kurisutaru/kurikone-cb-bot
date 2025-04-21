import contextvars
import sys

from dbutils.pooled_db import PooledDB
import mariadb
from config import config
from globals import logger

log = logger


class DatabasePool:
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabasePool, cls).__new__(cls)
            try:
                cls._pool = PooledDB(
                    creator=mariadb.connect,
                    maxconnections=config.MAX_POOL_SIZE,
                    mincached=2,
                    maxcached=10,
                    maxusage=5,
                    blocking=True,
                    host=config.DB_HOST,
                    user=config.DB_USER,
                    password=config.DB_PASSWORD,
                    database=config.DB_NAME,
                    port=config.DB_PORT,
                    setsession=["SET SESSION time_zone = 'Asia/Tokyo'"],
                    reset=True,
                    failures=None,
                    ping=7,
                )
                log.info(
                    f"Connection pool initialized with size: {config.MAX_POOL_SIZE}"
                )
            except Exception as e:
                log.critical(f"Failed to establish a database connection")
                sys.exit(1)
        return cls._instance

    def get_connection(self):
        conn = self._pool.connection()
        return conn

    def __enter__(self):
        return self.get_connection()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            print(f"Exception in context: {exc_value}")
        pass


db_pool = DatabasePool()

# --------------------------------------------
# Context Management
# --------------------------------------------
# Context var for async-safe connection tracking
db_connection_context = contextvars.ContextVar("db_connection", default=None)
rollback_flag_context = contextvars.ContextVar("rollback_flag", default=False)


def get_connection():
    """
    Returns:
        Tuple[connection, should_close]
        - connection: Existing or new connection
        - should_close: Whether the connection should be closed after use
    """
    existing_conn = db_connection_context.get()
    if existing_conn is not None:
        return existing_conn, False
    else:
        new_conn = db_pool.get_connection()
        return new_conn, True


def set_connection_context(conn: mariadb.Connection):
    """Set connection for the current context"""
    db_connection_context.set(conn)


def reset_connection_context():
    """Clear connection from current context"""
    db_connection_context.set(None)
