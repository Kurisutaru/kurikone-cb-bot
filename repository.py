from typing import List

from contextlib import contextmanager
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
                    WHERE guild_id = ?
                    """,
                    (guild_id,)
                )
                result = cursor.fetchone()
                if result:
                    return Guild(
                        guild_id=result['guild_id'],
                        guild_name=result['guild_name']
                    )

    def insert_guild(self, guild: Guild) -> Guild:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    INSERT INTO guild (
                        guild_id, 
                        guild_name
                        )
                    VALUES (?, ?)
                    """,
                    (
                        guild.guild_id,
                        guild.guild_name,
                    )
                )

                return guild


    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM guild
                    WHERE guild_id = ?
                    """,
                    (
                        guild_id,
                    )
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
                    WHERE guild_id = ?
                    """,
                    (guild_id,)
                )
                result = cursor.fetchall()
                if result:
                    entries = []
                    for row in result:
                        entries.append(
                            Channel(
                                channel_id=row['channel_id'],
                                guild_id=row['guild_id'],
                                channel_type=row['channel_type']
                            )
                        )
                    return entries
                return []

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
                    VALUES (?, ?, ?)
                    """,
                    (
                        channel.channel_id,
                        channel.guild_id,
                        channel.channel_type.name
                    )
                )
                channel.channel_id = cursor.lastrowid

            return channel

    def update_channel(self, channel: Channel) -> Channel:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE channel
                        SET channel_id = ?
                    WHERE guild_id = ? and channel_type = ?
                    """,
                    (
                        channel.channel_id,
                        channel.guild_id,
                        channel.channel_type.name
                    )
                )
                channel.channel_id = cursor.lastrowid

            return channel

    def delete_channel_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM channel WHERE guild_id = ?
                    """,
                    (
                        guild_id,
                    )
                )
            return True


class ChannelMessageRepository:

    def insert_channel_message(self, channel_message: ChannelMessage) -> ChannelMessage:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    INSERT INTO channel_message (channel_id, message_id) 
                    VALUES (?, ?)
                    """,
                    (channel_message.channel_id,
                     channel_message.message_id)
                )

                return channel_message

    def update_channel_message(self, channel_message: ChannelMessage) -> ChannelMessage:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE channel_message 
                        SET message_id = ?
                    WHERE channel_id = ?
                    """,
                    (
                        channel_message.message_id,
                        channel_message.channel_id,
                    )
                )

                return channel_message

    def update_self_channel_message(self, old_channel_id: int, new_channel_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE channel_message 
                        SET channel_id = ?
                    WHERE channel_id = ?
                    """,
                    (
                        new_channel_id,
                        old_channel_id,
                    )
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
                    WHERE channel_id = ?
                    """,
                    (channel_id,)
                )
                result = cursor.fetchone()
                if result:
                    return ChannelMessage(
                        channel_id=result['channel_id'],
                        message_id=result['message_id']
                    )
                return None

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
                    WHERE G.guild_id = ?
                    """,
                    (guild_id,)
                )
                result = cursor.fetchall()
                if result:
                    entries = []
                    for row in result:
                        entries.append(ChannelMessage(
                            channel_id=row['channel_id'],
                            message_id=row['message_id']
                        ))
                    return entries
                return []

    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM channel_message 
                    WHERE channel_id IN (SELECT channel_id from channel WHERE guild_id = ?)
                    """,
                    (
                        guild_id,
                    )
                )

                return True


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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        clan_battle_boss_entry.guild_id,
                        clan_battle_boss_entry.message_id,
                        clan_battle_boss_entry.clan_battle_period_id,
                        clan_battle_boss_entry.clan_battle_boss_id,
                        clan_battle_boss_entry.name,
                        clan_battle_boss_entry.image_path,
                        clan_battle_boss_entry.boss_round,
                        clan_battle_boss_entry.current_health,
                        clan_battle_boss_entry.max_health
                    )
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
                    WHERE message_id = ?
                    ORDER BY boss_round, clan_battle_boss_entry_id DESC
                    LIMIT 1
                    """,
                    (message_id,)
                )
                result = cursor.fetchone()
                if result:
                    return ClanBattleBossEntry(
                        clan_battle_boss_entry_id=result['clan_battle_boss_entry_id'],
                        guild_id=result['guild_id'],
                        message_id=result['message_id'],
                        clan_battle_period_id=result['clan_battle_period_id'],
                        clan_battle_boss_id=result['clan_battle_boss_id'],
                        name=result['name'],
                        image_path=result['image_path'],
                        boss_round=result['boss_round'],
                        current_health=result['current_health'],
                        max_health=result['max_health']
                    )
                return None

    def update_on_attack(self, clan_battle_boss_entry_id: int, current_health: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE clan_battle_boss_entry 
                    SET current_health = ?
                    WHERE clan_battle_boss_entry_id = ?
                    """,
                    (
                        current_health,
                        clan_battle_boss_entry_id
                    )
                )

                return True

    def update_message_id(self, clan_battle_boss_entry_id: int, message_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE clan_battle_boss_entry 
                    SET message_id = ?
                    WHERE clan_battle_boss_entry_id = ?
                    """,
                    (
                        message_id,
                        clan_battle_boss_entry_id
                    )
                )

                return True


    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM clan_battle_boss_entry 
                    WHERE guild_id = ?
                    """,
                    (
                        guild_id,
                    )
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
                    WHERE CBE.message_id = ?
                    """,
                    (message_id,)
                )
                result = cursor.fetchall()
                if result:
                    entries = []
                    for row in result:
                        entries.append(ClanBattleBossBook(
                            clan_battle_boss_book_id=row['clan_battle_boss_book_id'],
                            clan_battle_boss_entry_id=row['clan_battle_boss_entry_id'],
                            guild_id=row['guild_id'],
                            player_id=row['player_id'],
                            player_name=row['player_name'],
                            attack_type=row['attack_type'],
                            damage=row['damage'],
                            clan_battle_overall_entry_id=row['clan_battle_overall_entry_id'],
                            leftover_time=row['leftover_time'],
                            entry_date=row['entry_date']
                        )
                        )
                    return entries
                return []

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
                        WHERE CBBB.player_id = ?
                          AND CBBE.message_id = ?
                    """,
                    (
                        player_id,
                        message_id
                    )
                )
                result = cursor.fetchone()
                if result:
                    return ClanBattleBossBook(
                        clan_battle_boss_book_id=result['clan_battle_boss_book_id'],
                        clan_battle_boss_entry_id=result['clan_battle_boss_entry_id'],
                        guild_id=result['guild_id'],
                        player_id=result['player_id'],
                        player_name=result['player_name'],
                        attack_type=result['attack_type'],
                        damage=result['damage'],
                        clan_battle_overall_entry_id=result['clan_battle_overall_entry_id'],
                        leftover_time=result['leftover_time'],
                        entry_date=result['entry_date']
                    )
                return None

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
                        WHERE G.guild_id = ?
                            AND CBBB.player_id = ?
                            AND CBBB.entry_date >= IF(CURRENT_TIME() < '05:00:00',
                                        CONCAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'),
                                        CONCAT(CURDATE(), ' 05:00:00'))
                            AND CBBB.entry_date < IF(CURRENT_TIME() < '05:00:00',
                                       CONCAT(CURDATE(), ' 05:00:00'),
                                       CONCAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'))
                    """,
                    (
                        guild_id,
                        player_id,
                    )
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
                    WHERE clan_battle_boss_book_id = ?
                    """,
                    (
                        clan_battle_boss_book_id,
                    )
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, SYSDATE())
                    """,
                    (
                        clan_battle_boss_book.clan_battle_boss_entry_id,
                        clan_battle_boss_book.clan_battle_boss_entry_id,
                        clan_battle_boss_book.guild_id,
                        clan_battle_boss_book.player_id,
                        clan_battle_boss_book.player_name,
                        clan_battle_boss_book.attack_type.name,
                        clan_battle_boss_book.damage,
                        clan_battle_boss_book.clan_battle_overall_entry_id,
                        clan_battle_boss_book.leftover_time
                    )
                )
                clan_battle_boss_book.clan_battle_boss_book_id = cursor.lastrowid

            return clan_battle_boss_book

    def update_damage_boss_book_by_id(self, clan_battle_boss_book_id: int, damage: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE clan_battle_boss_book 
                        SET damage = ? 
                    WHERE clan_battle_boss_book_id = ?
                    """,
                    (
                        damage,
                        clan_battle_boss_book_id,
                    )
                )

                return True


    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM clan_battle_boss_book 
                    WHERE guild_id = ?
                    """,
                    (
                        guild_id,
                    )
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
                    """
                )
                result = cursor.fetchone()
                if result:
                    return ClanBattlePeriod(
                        clan_battle_period_id=result['clan_battle_period_id'],
                        clan_battle_period_name=result['clan_battle_period_name'],
                        date_from=result['date_from'],
                        date_to=result['date_to'],
                        boss1_id=result['boss1_id'],
                        boss2_id=result['boss2_id'],
                        boss3_id=result['boss3_id'],
                        boss4_id=result['boss4_id'],
                        boss5_id=result['boss5_id']
                    )
                return None


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
                    WHERE clan_battle_boss_id = ?
                    """,
                    (clan_battle_boss_id,)
                )
                result = cursor.fetchone()
                if result:
                    return ClanBattleBoss(
                        clan_battle_boss_id=result['clan_battle_boss_id'],
                        name=result['name'],
                        description=result['description'],
                        image_path=result['image_path'],
                        position=result['position']
                    )
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
                    WHERE position = ?
                    AND ? BETWEEN round_from AND round_to
                    """,
                    (position, boss_round,)
                )
                result = cursor.fetchone()
                if result:
                    return ClanBattleBossHealth(
                        clan_battle_boss_health_id=result['clan_battle_boss_health_id'],
                        position=result['position'],
                        round_from=result['round_from'],
                        round_to=result['round_to'],
                        health=result['health']
                    )
                return None


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
                    WHERE guild_id = ? 
                    AND clan_battle_boss_id = ? 
                    AND boss_round = ?
                    ORDER BY entry_date
                    """,
                    (
                        guild_id,
                        clan_battle_boss_id,
                        boss_round,
                    )
                )
                result = cursor.fetchall()
                if result:
                    entries = []
                    for row in result:
                        entry = ClanBattleOverallEntry(
                            clan_battle_overall_entry_id=row['clan_battle_overall_entry_id'],
                            guild_id=row['guild_id'],
                            clan_battle_period_id=row['clan_battle_period_id'],
                            clan_battle_boss_id=row['clan_battle_boss_id'],
                            player_id=row['player_id'],
                            player_name=row['player_name'],
                            round=row['boss_round'],
                            attack_type=row['attack_type'],
                            damage=row['damage'],
                            leftover_time=row['leftover_time'],
                            overall_leftover_entry_id=row['overall_leftover_entry_id'],
                            entry_date=row['entry_date']
                        )
                        entries.append(entry)
                    return entries
                return []

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
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSDATE()
                    )
                    """,
                    (
                        cb_overall_entry.guild_id,
                        cb_overall_entry.clan_battle_period_id,
                        cb_overall_entry.clan_battle_boss_id,
                        cb_overall_entry.player_id,
                        cb_overall_entry.player_name,
                        cb_overall_entry.round,
                        cb_overall_entry.damage,
                        cb_overall_entry.attack_type.name,
                        cb_overall_entry.leftover_time,
                        cb_overall_entry.overall_leftover_entry_id
                    )
                )
                cb_overall_entry.clan_battle_overall_entry_id = cursor.lastrowid

            return cb_overall_entry

    def update_overall_link(self, cb_overall_entry_id: int, overall_leftover_entry_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    UPDATE clan_battle_overall_entry
                    SET overall_leftover_entry_id = ?
                    WHERE clan_battle_overall_entry_id = ?
    
                    """,
                    (
                        overall_leftover_entry_id,
                        cb_overall_entry_id
                    )
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
                    WHERE CBOE.guild_id = ?
                      AND CBOE.player_id = ?
                      AND CBOE.attack_type <> 'CARRY'
                      AND CURDATE() BETWEEN CBP.date_from AND CBP.date_to
                      AND CBOE.entry_date >= IF(CURRENT_TIME() < '05:00:00',
                                        CONCAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'),
                                        CONCAT(CURDATE(), ' 05:00:00'))
                      AND CBOE.entry_date < IF(CURRENT_TIME() < '05:00:00',
                                       CONCAT(CURDATE(), ' 05:00:00'),
                                       CONCAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), ' 05:00:00'))

                    """,
                    (
                        guild_id,
                        player_id,
                    )
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
                    WHERE CBOE.guild_id = ?
                        AND CBOE.player_id = ?
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
                    (
                        guild_id,
                        player_id,
                    )
                )
                result = cursor.fetchall()
                if result:
                    entries = []
                    for row in result:
                        entry = ClanBattleLeftover(
                            clan_battle_overall_entry_id=row['clan_battle_overall_entry_id'],
                            clan_battle_boss_id=row['clan_battle_boss_id'],
                            clan_battle_boss_name=row['name'],
                            player_id=row['player_id'],
                            attack_type=row['attack_type'],
                            leftover_time=row['leftover_time'],
                        )
                        entries.append(entry)
                    return entries
                return []

    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM clan_battle_overall_entry
                    WHERE guild_id = ?
                    """,
                    (
                        guild_id,
                    )
                )

                return True


class ClanBattleReportMessageRepository:
    def delete_by_guild_id(self, guild_id: int) -> bool:
        with connection_context() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    DELETE FROM clan_battle_report_message
                    WHERE guild_id = ?
                    """,
                    (
                        guild_id,
                    )
                )

                return True


class GuildPlayerRepository:
    def batch_insert(self, data: list[(int, int, str)]) -> bool:
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
                    WHERE guild_id = ?
                    """,
                    (
                        guild_id,
                    )
                )

                return True
