# transactional.py
import asyncio
from functools import wraps
from database import connection_context_var, get_connection


def transactional(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if connection_context_var.get() is not None:
            return func(*args, **kwargs)  # Reuse existing connection

        # New transaction
        conn, should_close = get_connection()
        connection_context_var.set(conn)
        conn.autocommit = False
        conn.begin()

        try:
            result = func(*args, **kwargs)  # Sync call
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
            connection_context_var.set(None)

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        if connection_context_var.get() is not None:
            return await func(*args, **kwargs)  # Reuse existing connection

        # New transaction
        conn, should_close = get_connection()
        connection_context_var.set(conn)
        conn.autocommit = False
        conn.begin()

        try:
            result = await func(*args, **kwargs)  # Async call
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
            connection_context_var.set(None)

    return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper