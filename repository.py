from typing import List, Optional, Tuple, Type

from contextlib import contextmanager

import attrs

from models import *
from database import get_connection, reset_connection_context, set_connection_context, db_connection_context

@contextmanager
def connection_context():
    """
    Context manager that handles both transactional and non-transactional connections
    Returns a connection and manages its lifecycle automatically
    """
    conn, should_close = get_connection()
    try:
        # Set connection in context if not already set
        if not db_connection_context.get():
            set_connection_context(conn)

        yield conn
    finally:
        if should_close:
            conn.close()
            reset_connection_context()

T = TypeVar('T')

def fetch_all_to_model(cursor, model_class: Type[T]) -> List[T]:
    """Convert all fetched rows to instances of the given model class."""
    result = cursor.fetchall()
    if result:
        return [model_class(**row) for row in result]
    return []

def fetch_one_to_model(cursor, model_class: Type[T]) -> Optional[T]:
    """Convert a single fetched row to an instance of the given model class."""
    result = cursor.fetchone()
    if result:
        return model_class(**result)
    return None

class GenericRepository:
    def get_connection_id(self) -> int:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT CONNECTION_ID() AS CONNECTION_ID")
                result = cursor.fetchone()
                if result is None:
                    raise ValueError("Failed to retrieve connection ID")
                return int(result['CONNECTION_ID'])

    def set_session_read_uncommited(self):
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")

    def get_session_transaction_isolation(self):
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT @@SESSION.transaction_isolation AS TI")
                result = cursor.fetchone()
                if result is None:
                    raise ValueError("Failed to retrieve transaction Isolation")
                return str(result['TI'])

    def get_session_autocommit(self):
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT @@SESSION.autocommit AS TI")
                result = cursor.fetchone()
                if result is None:
                    raise ValueError("Failed to retrieve transaction Isolation")
                return bool(result['TI'])

    def get_session_transaction_id(self):
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT trx_id FROM information_schema.innodb_trx WHERE trx_mysql_thread_id = CONNECTION_ID()")
                result = cursor.fetchone()
                if result is None:
                    return "None"
                return result['trx_id']



class GuildRepository:
    def get_by_guild_id(self, guild_id: int) -> Optional[Guild]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT guild_id,
                           guild_name
                    FROM guild
                    WHERE guild_id = %(guild_id)s
                    """,
                    {
                        "guild_id" : guild_id,
                    }
                )
                return fetch_one_to_model(cursor, Guild)

    def insert_guild(self, guild: Guild) -> Guild:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    INSERT INTO guild (
                        guild_id, 
                        guild_name
                        )
                    VALUES (%(guild_id)s, %(guild_name)s)
                    """,
                    attrs.asdict(guild)
                )

                return guild


    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM guild
                    WHERE guild_id = %(guild_id)s
                    """,
                    {
                        'guild_id': guild_id,
                    }
                )

                return True


class ChannelRepository:

    def get_all_by_guild_id(self, guild_id: int) -> List[Channel]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT channel_id,
                           guild_id,
                           channel_type
                    FROM channel
                    WHERE guild_id = %(guild_id)s
                    """,
                    {
                        'guild_id' : guild_id,
                    }
                )
                return fetch_all_to_model(cursor, Channel)

    def get_boss_channel_by_guild_id(self, guild_id: int) -> List[Channel]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT channel_id,
                           guild_id,
                           channel_type
                    FROM channel
                    WHERE guild_id = %(guild_id)s AND UPPER(channel_type) like '%BOSS%'
                    """,
                    {
                        'guild_id' : guild_id,
                    }
                )
                return fetch_all_to_model(cursor, Channel)

    def get_all_by_guild_id_and_type(self, guild_id: int, channel_type: str) -> Optional[Channel]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT channel_id,
                           guild_id,
                           channel_type
                    FROM channel
                    WHERE guild_id = %(guild_id)s
                    AND channel_type = %(channel_type)s
                    """,
                    {
                        'guild_id' : guild_id,
                        'channel_type' : channel_type
                    }
                )
                return fetch_one_to_model(cursor, Channel)

    def insert_channel(self, channel: Channel) -> Channel:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    INSERT INTO channel (
                        channel_id, 
                        guild_id, 
                        channel_type
                        )
                    VALUES (%(channel_id)s, %(guild_id)s, %(channel_type)s)
                    """,
                    {
                        'channel_id' : channel.channel_id,
                        'guild_id' : channel.guild_id,
                        'channel_type' : channel.channel_type.name,
                    }
                )
                channel.channel_id = cursor.lastrowid

            return channel

    def update_channel(self, channel: Channel) -> Channel:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE channel
                        SET channel_id = %(channel_id)s
                    WHERE guild_id = %(guild_id)s and channel_type = %(channel_type)s
                    """,
                    {
                        'channel_id' : channel.channel_id,
                        'guild_id' : channel.guild_id,
                        'channel_type' : channel.channel_type.name,
                    }
                )
                channel.channel_id = cursor.lastrowid

            return channel

    def delete_channel_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM channel WHERE guild_id = %(guild_id)s
                    """,
                    {
                        'guild_id' : guild_id,
                    }
                )
            return True


class ChannelMessageRepository:

    def insert_channel_message(self, channel_message: ChannelMessage) -> ChannelMessage:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    INSERT INTO channel_message (channel_id, message_id) 
                    VALUES (%(channel_id)s, %(message_id)s)
                    """,
                    {
                        'channel_id' : channel_message.channel_id,
                        'message_id' : channel_message.message_id,
                    }
                )

                return channel_message

    def update_channel_message(self, channel_message: ChannelMessage) -> ChannelMessage:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE channel_message 
                        SET message_id = %(message_id)s
                    WHERE channel_id = %(channel_id)s
                    """,
                    {
                        'channel_id' : channel_message.channel_id,
                        'message_id' : channel_message.message_id,
                    }
                )

                return channel_message

    def update_self_channel_message(self, old_channel_id: int, new_channel_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE channel_message 
                        SET channel_id = %(new_channel_id)s
                    WHERE channel_id = %(old_channel_id)s
                    """,
                    {
                        'new_channel_id' : new_channel_id,
                        'old_channel_id' : old_channel_id,
                    }
                )

                return True

    def get_channel_message_by_channel_id(self, channel_id: int) -> Optional[ChannelMessage]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT channel_id,
                           message_id
                    FROM channel_message
                    WHERE channel_id = %(channel_id)s
                    """,
                    {
                        'channel_id' : channel_id,
                    }
                )
                return fetch_one_to_model(cursor, ChannelMessage)

    def get_all_by_guild_id(self, guild_id: int) -> list[ChannelMessage]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT CM.channel_id,
                           CM.message_id
                    FROM channel_message CM 
                        JOIN channel C ON C.channel_id = CM.channel_id
                        JOIN guild G ON G.guild_id = C.guild_id
                    WHERE G.guild_id = %(guild_id)s
                    """,
                    {
                        'guild_id' : guild_id,
                    }
                )
                return fetch_all_to_model(cursor, ChannelMessage)

    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM channel_message 
                    WHERE channel_id IN (SELECT channel_id from channel WHERE guild_id = %(guild_id)s)
                    """,
                    {
                        'guild_id' : guild_id,
                    }
                )

                return True

    def get_message_by_guild_id_and_channel_type(self, guild_id, channel_type) -> Optional[ChannelMessage]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT CM.channel_id, CM.message_id
                    FROM channel_message CM
                             JOIN channel C on CM.channel_id = C.channel_id
                    WHERE C.guild_id = %(guild_id)s
                      AND C.channel_type = %(channel_type)s

                    """,
                    {
                        'guild_id': guild_id,
                        'channel_type' : channel_type
                    }
                )
                return fetch_one_to_model(cursor, ChannelMessage)


class ClanBattleBossEntryRepository:

    def insert_clan_battle_boss_entry(self, clan_battle_boss_entry: ClanBattleBossEntry) -> ClanBattleBossEntry:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
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
                    ) 
                    VALUES (
                         %(guild_id)s, 
                         %(message_id)s, 
                         %(clan_battle_period_id)s, 
                         %(clan_battle_boss_id)s,
                         %(name)s,
                         %(image_path)s,
                         %(boss_round)s,
                         %(current_health)s,
                         %(max_health)s)
                    """,
                    attrs.asdict(clan_battle_boss_entry)
                )
                clan_battle_boss_entry.clan_battle_boss_entry_id = cursor.lastrowid

            return clan_battle_boss_entry

    def get_last_by_message_id(self, message_id: int) -> Optional[ClanBattleBossEntry]:
        with connection_context() as conn:

            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
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
                    """,
                    {
                        'message_id' : message_id,
                    }
                )
                return fetch_one_to_model(cursor, ClanBattleBossEntry)

    def get_last_active_period_by_message_id(self, message_id: int) -> Optional[ClanBattleBossEntry]:
        with connection_context() as conn:

    def update_on_attack(self, clan_battle_boss_entry_id: int, current_health: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE clan_battle_boss_entry 
                    SET current_health = %(current_health)s
                    WHERE clan_battle_boss_entry_id = %(clan_battle_boss_entry_id)s
                    """,
                    {
                        'clan_battle_boss_entry_id': clan_battle_boss_entry_id,
                        'current_health' : current_health,
                    }
                )

                return True

    def update_message_id(self, clan_battle_boss_entry_id: int, message_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE clan_battle_boss_entry 
                    SET message_id = %(message_id)s
                    WHERE clan_battle_boss_entry_id = %(clan_battle_boss_entry_id)s
                    """,
                    {
                        'clan_battle_boss_entry_id': clan_battle_boss_entry_id,
                        'message_id' : message_id,
                    }
                )

                return True


    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM clan_battle_boss_entry 
                    WHERE guild_id = %(guild_id)s
                    """,
                    {
                        'guild_id' : guild_id,
                    }
                )

                return True


class ClanBattleBossBookRepository:

    def get_all_by_message_id(self, message_id: int) -> list[ClanBattleBossBook]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
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
                    """,
                    {
                        'message_id' : message_id,
                    }
                )
                return fetch_all_to_model(cursor, ClanBattleBossBook)

    def get_player_book_entry(self, message_id: int, player_id: int) -> Optional[ClanBattleBossBook]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
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
                    """,
                    {
                        'player_id' : player_id,
                        'message_id' : message_id,
                    }
                )
                return fetch_one_to_model(cursor, ClanBattleBossBook)

    def get_player_book_count(self, guild_id: int, player_id: int) -> int:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
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
                                        CONCAT(CURDATE(), ' 05:00:00'))
                            AND CBBB.entry_date < IF(CURRENT_TIME() < '05:00:00',
                                       CONCAT(CURDATE(), ' 05:00:00'),
                                       CONCAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'))
                    """,
                    {
                        'guild_id' : guild_id,
                        'player_id' : player_id,
                    }
                )
                result = cursor.fetchone()
                if result:
                    return int(result['Book_Count'])
                return 0

    def delete_book_by_id(self, clan_battle_boss_book_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE
                    FROM clan_battle_boss_book
                    WHERE clan_battle_boss_book_id = %(clan_battle_boss_book_id)s
                    """,
                    {
                        'clan_battle_boss_book_id': clan_battle_boss_book_id,
                    }
                )

                return True

    def insert_boss_book_entry(self, clan_battle_boss_book: ClanBattleBossBook) -> ClanBattleBossBook:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    INSERT INTO clan_battle_boss_book (
                        clan_battle_boss_book_id, 
                        clan_battle_boss_entry_id,
                        guild_id,
                        player_id, 
                        player_name, 
                        attack_type, 
                        damage, 
                        clan_battle_overall_entry_id, 
                        leftover_time,
                        entry_date
                    )
                    VALUES (
                        %(clan_battle_boss_book_id)s,
                        %(clan_battle_boss_entry_id)s,
                        %(guild_id)s,
                        %(player_id)s,
                        %(player_name)s,
                        %(attack_type)s,
                        %(damage)s,
                        %(clan_battle_overall_entry_id)s,
                        %(leftover_time)s,
                        SYSDATE()
                    )
                    """,
                    clan_battle_boss_book.to_db_dict()
                )
                clan_battle_boss_book.clan_battle_boss_book_id = cursor.lastrowid

            return clan_battle_boss_book

    def update_damage_boss_book_by_id(self, clan_battle_boss_book_id: int, damage: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE clan_battle_boss_book 
                        SET damage = %(damage)s
                    WHERE clan_battle_boss_book_id = %(clan_battle_boss_book_id)s
                    """,
                    {
                        'clan_battle_boss_book_id': clan_battle_boss_book_id,
                        'damage' : damage
                    }
                )

                return True


    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM clan_battle_boss_book 
                    WHERE guild_id = %(guild_id)s
                    """,
                    {
                        'guild_id' : guild_id,
                    }
                )

                return True

class ClanBattlePeriodRepository:

    def get_current_cb_period(self) -> Optional[ClanBattlePeriod] :
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT clan_battle_period_id,
                           clan_battle_period_name,
                           date_from,
                           date_to,
                           boss1_id,
                           boss2_id,
                           boss3_id,
                           boss4_id,
                           boss5_id
                    FROM clan_battle_period
                    WHERE SYSDATE() BETWEEN date_from AND date_to
                    ORDER BY clan_battle_period_id DESC
                    LIMIT 1
                    """
                )
                return fetch_one_to_model(cursor, ClanBattlePeriod)

    def get_by_id(self, clan_battle_period_id:int) -> Optional[ClanBattlePeriod] :
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT clan_battle_period_id,
                           clan_battle_period_name,
                           date_from,
                           date_to,
                           boss1_id,
                           boss2_id,
                           boss3_id,
                           boss4_id,
                           boss5_id
                    FROM clan_battle_period
                    WHERE clan_battle_period_id = %(clan_battle_period_id)s
                    ORDER BY clan_battle_period_id DESC
                    LIMIT 1
                    """,
                    {
                        'clan_battle_period_id': clan_battle_period_id
                    }
                )
                return fetch_one_to_model(cursor, ClanBattlePeriod)

    def get_by_param(self, year: int, month:int) -> Optional[ClanBattlePeriod]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                        SELECT clan_battle_period_id,
                           clan_battle_period_name,
                           date_from,
                           date_to,
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
                    """,
                    {
                        'year' : year,
                        'month' : month,
                    }
                )
                return fetch_one_to_model(cursor, ClanBattlePeriod)

    def get_by_id_day(self, clan_battle_period_id:int) -> Optional[ClanBattlePeriod] :
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                     SELECT clan_battle_period_id,
                           clan_battle_period_name,
                           date_to,
                           date_from,
                           boss1_id,
                           boss2_id,
                           boss3_id,
                           boss4_id,
                           boss5_id,
                           IFNULL(DATEDIFF(
                                          IF(HOUR(SYSDATE()) < 5, DATE_SUB(SYSDATE(), INTERVAL 1 DAY),
                                             SYSDATE()),
                                          date_from
                                  ) + 1, -1) AS current_day
                    FROM (SELECT 1 AS dummy) AS d
                             LEFT JOIN clan_battle_period ON clan_battle_period_id = %(clan_battle_period_id)s
                    ORDER BY clan_battle_period_id DESC
                    LIMIT 1
                    """,
                    {
                        'clan_battle_period_id': clan_battle_period_id
                    }
                )
                return fetch_one_to_model(cursor, ClanBattlePeriodDay)


    def get_current_cb_period_day(self) -> Optional[ClanBattlePeriodDay] :
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT clan_battle_period_id,
                           clan_battle_period_name,
                           date_to,
                           date_from,
                           boss1_id,
                           boss2_id,
                           boss3_id,
                           boss4_id,
                           boss5_id,
                           IFNULL(DATEDIFF(
                                          IF(HOUR(SYSDATE()) < 5, DATE_SUB(SYSDATE(), INTERVAL 1 DAY),
                                             SYSDATE()),
                                          date_from
                                  ) + 1, -1) AS current_day
                    FROM (SELECT 1 AS dummy) AS d
                             LEFT JOIN clan_battle_period
                                       ON SYSDATE() BETWEEN date_from AND date_to
                    ORDER BY clan_battle_period_id DESC
                    LIMIT 1
                    """
                )
                return fetch_one_to_model(cursor, ClanBattlePeriodDay)

    def set_all_inactive(self) -> bool :
        with connection_context() as conn:

class ClanBattleBossRepository:

    def fetch_clan_battle_boss_by_id(self, clan_battle_boss_id: int) -> Optional[ClanBattleBoss]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT clan_battle_boss_id,
                           name,
                           description,
                           image_path,
                           position
                    FROM clan_battle_boss
                    WHERE clan_battle_boss_id = %(clan_battle_boss_id)s
                    """,
                    {
                        'clan_battle_boss_id': clan_battle_boss_id,
                    }
                )
                result = cursor.fetchone()
                if result:
                    return ClanBattleBoss(**result)
                return None


class ClanBattleBossHealthRepository:

    def get_one_by_position_and_round(self, position: int, boss_round: int) -> Optional[ClanBattleBossHealth]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT clan_battle_boss_health_id,
                           position,
                           round_from,
                           round_to,
                           health
                    FROM clan_battle_boss_health
                    WHERE position = %(position)s
                    AND %(boss_round)s BETWEEN round_from AND round_to
                    """,
                    {
                        'position' : position,
                        'boss_round' : boss_round,
                    }
                )
                return fetch_one_to_model(cursor, ClanBattleBossHealth)


class ClanBattleOverallEntryRepository:
    def get_all_by_guild_id_boss_id_and_round(self, guild_id: int, clan_battle_boss_id: int, boss_round: int) -> list[ClanBattleOverallEntry]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT clan_battle_overall_entry_id,
                            guild_id,
                            clan_battle_period_id,
                            clan_battle_boss_id,
                            player_id,
                            player_name,
                            boss_round,
                            attack_type,
                            damage,
                            leftover_time,
                            overall_leftover_entry_id,
                            entry_date
                    FROM clan_battle_overall_entry
                    WHERE guild_id = %(guild_id)s
                    AND clan_battle_boss_id = %(clan_battle_boss_id)s
                    AND boss_round = %(boss_round)s
                    ORDER BY entry_date
                    """,
                    {
                        'guild_id' : guild_id,
                        'clan_battle_boss_id': clan_battle_boss_id,
                        'boss_round' : boss_round,
                    }
                )
                return fetch_all_to_model(cursor, ClanBattleOverallEntry)

    def insert(self, cb_overall_entry: ClanBattleOverallEntry) -> ClanBattleOverallEntry:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    INSERT INTO clan_battle_overall_entry (
                        guild_id, 
                        clan_battle_period_id, 
                        clan_battle_boss_id, 
                        player_id, 
                        player_name, 
                        boss_round, 
                        damage, 
                        attack_type, 
                        leftover_time, 
                        overall_leftover_entry_id, 
                        entry_date
                    )
                    VALUES 
                    (
                        %(guild_id)s,
                        %(clan_battle_period_id)s,
                        %(clan_battle_boss_id)s,
                        %(player_id)s,
                        %(player_name)s,
                        %(boss_round)s,
                        %(damage)s,
                        %(attack_type)s,
                        %(leftover_time)s,
                        %(overall_leftover_entry_id)s,
                        SYSDATE()
                    )
                    """,
                    attrs.asdict(cb_overall_entry)
                )
                cb_overall_entry.clan_battle_overall_entry_id = cursor.lastrowid

            return cb_overall_entry

    def update_overall_link(self, cb_overall_entry_id: int, overall_leftover_entry_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE clan_battle_overall_entry
                    SET overall_leftover_entry_id = %(overall_leftover_entry_id)s
                    WHERE clan_battle_overall_entry_id = %(cb_overall_entry_id)s
    
                    """,
                    {
                        'overall_leftover_entry_id': overall_leftover_entry_id,
                        'cb_overall_entry_id': cb_overall_entry_id,
                    }
                )

                return True

    def get_player_overall_entry_count(self, guild_id: int, player_id: int) -> int:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(CBOE.clan_battle_overall_entry_id) AS entry_count
                    FROM clan_battle_overall_entry CBOE
                             JOIN clan_battle_period CBP ON CBP.clan_battle_period_id = CBOE.clan_battle_period_id
                             JOIN clan_battle_boss CBB ON CBOE.clan_battle_boss_id = CBB.clan_battle_boss_id
                    WHERE CBOE.guild_id = %(guild_id)s
                      AND CBOE.player_id = %(player_id)s
                      AND CBOE.attack_type <> 'CARRY'
                      AND CURDATE() BETWEEN CBP.date_from AND CBP.date_to
                      AND CBOE.entry_date >= IF(CURRENT_TIME() < '05:00:00',
                                        CONCAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'),
                                        CONCAT(CURDATE(), ' 05:00:00'))
                      AND CBOE.entry_date < IF(CURRENT_TIME() < '05:00:00',
                                       CONCAT(CURDATE(), ' 05:00:00'),
                                       CONCAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'))

                    """,
                    {
                        'guild_id': guild_id,
                        'player_id': player_id,
                    }
                )
                result = cursor.fetchone()
                if result:
                    return result['entry_count']
                return 0

    def get_leftover_by_guild_id_and_player_id(self, guild_id: int, player_id: int) -> List[ClanBattleLeftover]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT CBOE.clan_battle_overall_entry_id,
                           CBOE.clan_battle_boss_id,
                           CBB.name,
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
                        AND CURDATE() BETWEEN CBP.date_from AND CBP.date_to
                        AND CONVERT_TZ(CBOE.entry_date, @@session.time_zone, 'Asia/Tokyo') >= IF(CURRENT_TIME() < '05:00:00',
                                        CONCAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'),
                                        CONCAT(CURDATE(), ' 05:00:00'))
                        AND CONVERT_TZ(CBOE.entry_date, @@session.time_zone, 'Asia/Tokyo') < IF(CURRENT_TIME() < '05:00:00',
                                       CONCAT(CURDATE(), ' 05:00:00'),
                                       CONCAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'));
                    """,
                    {
                        'guild_id': guild_id,
                        'player_id': player_id,
                    }
                )
                return fetch_all_to_model(cursor, ClanBattleLeftover)

    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM clan_battle_overall_entry
                    WHERE guild_id = %(guild_id)s
                    """,
                    {
                        'guild_id': guild_id,
                    }
                )

                return True

    def get_report_entry_by_param(self, guild_id:int, year:int, month: int, day: int) -> list[ClanBattleReportEntry]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                        WITH PERIOD AS (SELECT clan_battle_period_id, date_from, date_to
                                    FROM clan_battle_period
                                    WHERE date_from <= LAST_DAY(CONCAT(%(year)s, '-', LPAD(%(month)s, 2, '0'), '-01'))
                                      AND date_to >= CONCAT(%(year)s, '-', LPAD(%(month)s, 2, '0'), '-01')
                                    LIMIT 1)
                       , ENTRY AS (SELECT DATEDIFF(
                                                  IF(HOUR(CBOE.entry_date) < 5, DATE_SUB(CBOE.entry_date, INTERVAL 1 DAY),
                                                     CBOE.entry_date),
                                                  CBP.date_from
                                          ) + 1                                                                          AS day,
                                          CBOE.guild_id,
                                          CBOE.player_id                                                                 AS player_id,
                                          CBOE.player_name                                                               AS player_name,
                                          SUM(IF(attack_type = 'PATK', 1, 0))                                            AS patk_count,
                                          SUM(IF(attack_type = 'MATK', 1, 0))                                            AS matk_count,
                                          SUM(IF(leftover_time IS NOT NULL AND overall_leftover_entry_id IS NULL, 1, 0)) AS leftover_count,
                                          SUM(IF(attack_type = 'CARRY', 1, 0))                                           AS carry_count
                                   FROM clan_battle_overall_entry CBOE
                                            JOIN
                                        PERIOD CBP ON CBP.clan_battle_period_id = CBOE.clan_battle_period_id
                                            JOIN
                                        clan_battle_boss CBB ON CBOE.clan_battle_boss_id = CBB.clan_battle_boss_id
                                   WHERE CBOE.entry_date BETWEEN CBP.date_from AND CBP.date_to
                                     AND CBOE.guild_id = %(guild_id)s
                                   GROUP BY DATEDIFF(
                                                    IF(HOUR(CBOE.entry_date) < 5,
                                                       DATE_SUB(CBOE.entry_date, INTERVAL 1 DAY),
                                                       CBOE.entry_date),
                                                    CBP.date_from
                                            ) + 1,
                                            CBOE.guild_id,
                                            CBOE.player_id,
                                            CBOE.player_name)
                    SELECT GP.player_name as player_name,
                           COALESCE(E.patk_count, 0) AS patk_count,
                           COALESCE(E.matk_count, 0) AS matk_count,
                           COALESCE(E.leftover_count, 0) AS leftover_count,
                           COALESCE(E.carry_count, 0) AS carry_count
                    FROM guild_player GP
                             LEFT JOIN ENTRY E on GP.player_id = E.player_id AND E.day = %(day)s
                    WHERE GP.guild_id = %(guild_id)s
                    """,
                    {
                        'guild_id': guild_id,
                        'year': year,
                        'month': month,
                        'day': day
                    }
                )
                return fetch_all_to_model(cursor, ClanBattleReportEntry)

    def get_report_entry_by_guild_and_period_id(self, guild_id:int, period_id: int) -> list[ClanBattleReportEntry]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                        WITH ENTRY AS (SELECT DATEDIFF(
                                                  IF(HOUR(CBOE.entry_date) < 5, DATE_SUB(CBOE.entry_date, INTERVAL 1 DAY),
                                                     CBOE.entry_date),
                                                  CBP.date_from
                                          ) + 1                                                                          AS day,
                                          CBOE.guild_id,
                                          CBOE.player_id                                                                 AS player_id,
                                          CBOE.player_name                                                               AS player_name,
                                          SUM(IF(attack_type = 'PATK', 1, 0))                                            AS patk_count,
                                          SUM(IF(attack_type = 'MATK', 1, 0))                                            AS matk_count,
                                          SUM(IF(leftover_time IS NOT NULL AND overall_leftover_entry_id IS NULL, 1, 0)) AS leftover_count,
                                          SUM(IF(attack_type = 'CARRY', 1, 0))                                           AS carry_count
                                   FROM clan_battle_overall_entry CBOE
                                            JOIN
                                        clan_battle_period CBP ON CBP.clan_battle_period_id = CBOE.clan_battle_period_id
                                            JOIN
                                        clan_battle_boss CBB ON CBOE.clan_battle_boss_id = CBB.clan_battle_boss_id
                                   WHERE CBOE.entry_date BETWEEN CBP.date_from AND CBP.date_to
                                     AND CBP.clan_battle_period_id = %(guild_id)s
                                     AND CBOE.guild_id = %(guild_id)s
                                   GROUP BY DATEDIFF(
                                                    IF(HOUR(CBOE.entry_date) < 5,
                                                       DATE_SUB(CBOE.entry_date, INTERVAL 1 DAY),
                                                       CBOE.entry_date),
                                                    CBP.date_from
                                            ) + 1,
                                            CBOE.guild_id,
                                            CBOE.player_id,
                                            CBOE.player_name)
                    SELECT GP.player_name as player_name,
                           COALESCE(E.patk_count, 0) AS patk_count,
                           COALESCE(E.matk_count, 0) AS matk_count,
                           COALESCE(E.leftover_count, 0) AS leftover_count,
                           COALESCE(E.carry_count, 0) AS carry_count
                    FROM guild_player GP
                             LEFT JOIN ENTRY E on GP.player_id = E.player_id
                    WHERE GP.guild_id = %(guild_id)s
                    """,
                    {
                        'guild_id': guild_id,
                        'period_id': period_id,
                    }
                )

                return fetch_all_to_model(cursor, ClanBattleReportEntry)

class ClanBattleReportMessageRepository:
    def get_by_guild_period_and_days(self, guild_id: int, clan_battle_period_id: int, day : int) -> Optional[ClanBattleReportMessage]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT clan_battle_report_message_id,
                           guild_id,
                           clan_battle_period_id,
                           day,
                           message_id
                    FROM clan_battle_report_message
                    WHERE guild_id = %(guild_id)s
                      AND clan_battle_period_id = %(clan_battle_period_id)s
                      AND day = %(day)s
                    """,
                    {
                        'guild_id': guild_id,
                        'clan_battle_period_id': clan_battle_period_id,
                        'day': day
                    }
                )
                result = cursor.fetchone()
                if result:
                    return ClanBattleReportMessage(**result)

                return fetch_one_to_model(cursor, ClanBattleReportMessage)

    def get_last_by_guild_period(self, guild_id: int, clan_battle_period_id: int) -> Optional[ClanBattleReportMessage]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT clan_battle_report_message_id,
                           guild_id,
                           clan_battle_period_id,
                           day,
                           message_id
                    FROM clan_battle_report_message
                    WHERE guild_id = %(guild_id)s
                      AND clan_battle_period_id = %(clan_battle_period_id)s
                    ORDER BY clan_battle_report_message_id DESC
                    """,
                    {
                        'guild_id': guild_id,
                        'clan_battle_period_id': clan_battle_period_id,
                    }
                )

                return fetch_one_to_model(cursor, ClanBattleReportMessage)

    def insert(self, report: ClanBattleReportMessage) -> ClanBattleReportMessage:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
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
                    """,
                    attrs.asdict(report)
                )
                report.clan_battle_report_message_id = cursor.lastrowid
                return report

    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM clan_battle_report_message
                    WHERE guild_id = %(guild_id)s
                    """,
                    {
                        'guild_id': guild_id,
                    }
                )

                return True




class GuildPlayerRepository:
    def batch_insert(self, data: list[Tuple[int, int, str]]) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.executemany(
                    """
                    INSERT INTO guild_player (guild_id, player_id, player_name) 
                    VALUES (?, ?, ?)
                    """,
                    data
                )

                return True

    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM guild_player
                    WHERE guild_id = %(guild_id)s
                    """,
                    {
                        'guild_id': guild_id,
                    }
                )

                return True

    def get_all_by_guild_id(self, guild_id: int) -> list[GuildPlayer]:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                """
                    SELECT guild_id, player_id, player_name 
                    FROM guild_player
                    WHERE guild_id = %(guild_id)s
                """,
                    {
                        'guild_id': guild_id,
                    }
                )

                return fetch_all_to_model(cursor, GuildPlayer)


class ErrorLogRepository:
    def insert(self, guild_id: int, identifier: str, exception: str,stacktrace: str) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                """
                    INSERT INTO error_log
                    (guild_id, identifier, exception, stacktrace) VALUES 
                    (%(guild_id)s, %(identifier)s,  %(exception)s, %(stacktrace)s)
                """,
                    {
                        'guild_id': guild_id,
                        'identifier': identifier,
                        'exception': exception,
                        'stacktrace': stacktrace,
                    }
                )
                return True

    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                """
                    DELETE FROM error_log
                    WHERE guild_id = %(guild_id)s
                """,
                    {
                        'guild_id': guild_id,
                    }
                )
                return True