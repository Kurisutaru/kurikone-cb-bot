import contextvars

from dbutils.pooled_db import PooledDB
import mariadb
from config import config


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
                    blocking=True,
                    host=config.DB_HOST,
                    user=config.DB_USER,
                    password=config.DB_PASSWORD,
                    database=config.DB_NAME,
                    port=config.DB_PORT,
                    autocommit=True
                )
                print(f"Connection pool initialized with size: {config.MAX_POOL_SIZE}")
            except Exception as e:
                print(f"Failed to initialize connection pool: {e}")
                raise
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
connection_context_var = contextvars.ContextVar('db_connection', default=None)


def get_connection():
    """
    Returns:
        Tuple[connection, should_close]
        - connection: Existing or new connection
        - should_close: Whether the connection should be closed after use
    """
    existing_conn = connection_context_var.get()
    if existing_conn is not None:
        return existing_conn, False
    else:
        new_conn = db_pool.get_connection()
        return new_conn, True


def set_connection_context(conn: mariadb.Connection):
    """Set connection for the current context"""
    connection_context_var.set(conn)


def reset_connection_context():
    """Clear connection from current context"""
    connection_context_var.set(None)
