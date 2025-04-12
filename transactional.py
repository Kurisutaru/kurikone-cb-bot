# transactional.py
import asyncio
from contextvars import ContextVar
from functools import wraps

from database import rollback_flag_context, get_connection, reset_connection_context, set_connection_context, \
    db_connection_context


def transaction_rollback():
    """Java equivalent of TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()"""
    rollback_flag_context.set(True)


def transactional(func):
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        conn = db_connection_context.get()
        if conn is not None:  # Nested transaction
            return func(*args, **kwargs)

        # New transaction
        conn, should_close = get_connection()
        conn.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
        conn.autocommit = False

        set_connection_context(conn)
        rollback_flag_context.set(False)

        conn.begin()

        try:
            result = func(*args, **kwargs)
            if rollback_flag_context.get():
                conn.rollback()
            else:
                conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            if should_close:
                conn.close()
                db_connection_context.set(None)
                reset_connection_context()

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        conn = db_connection_context.get()
        if conn is not None:  # Nested transaction
            return await func(*args, **kwargs)

        # New transaction
        conn, should_close = get_connection()
        conn.autocommit = False

        # Set isolation level using a cursor
        #with conn.cursor() as cursor:
        #    cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")

        set_connection_context(conn)
        rollback_flag_context.set(False)

        conn.begin()

        try:
            result = await func(*args, **kwargs)
            if rollback_flag_context.get():
                conn.rollback()
            else:
                conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            if should_close:
                conn.close()
                reset_connection_context()

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
