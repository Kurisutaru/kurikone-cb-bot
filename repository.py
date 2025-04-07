import traceback

import mariadb

from database import db_pool
from models import *


class GuildRepository:
    def __init__(self):
        self.pool = db_pool

    def get_by_guild_id(self, guild_id: int):
        try:
            with self.pool as conn:
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
                    return None
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return None

    def insert_guild(self, guild: Guild):
        try:
            with self.pool as conn:
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
                    conn.commit()
                    return guild
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()
            return None


class GuildChannelRepository:
    def __init__(self):
        self.pool = db_pool

    def get_all_by_guild_id(self, guild_id: int):
        try:
            with self.pool as conn:
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
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return []

    def insert_channel(self, channel: Channel):
        try:
            with self.pool as conn:
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
                conn.commit()
                return channel
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()

    def update_channel(self, channel: Channel):
        try:
            with self.pool as conn:
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
                conn.commit()
                return channel
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()


class ChannelMessageRepository:
    def __init__(self):
        self.pool = db_pool

    def insert_channel_message(self, channel_message: ChannelMessage):
        try:
            with self.pool as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        INSERT INTO channel_message (channel_id, message_id) 
                        VALUES (?, ?)
                        """,
                        (channel_message.channel_id,
                         channel_message.message_id)
                    )
                    conn.commit()
                    return channel_message
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()
            return None

    def update_channel_message(self, channel_message: ChannelMessage):
        try:
            with self.pool as conn:
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
                    conn.commit()
                    return channel_message
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()
            return None

    def update_self_channel_message(self, old_channel_id:int, new_channel_id:int):
        try:
            with self.pool as conn:
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
                    conn.commit()
                    return True
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()
            return False

    def get_channel_message_by_channel_id(self, channel_id: int):
        try:
            with self.pool as conn:
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
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return None

    def get_all_by_guild_id(self, guild_id: int):
        try:
            with self.pool as conn:
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
                            entries.append( ChannelMessage(
                                channel_id=row['channel_id'],
                                message_id=row['message_id']
                            ))
                        return entries
                    return []
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return []


class ClanBattleBossEntryRepository:
    def __init__(self):
        self.pool = db_pool

    def insert_clan_battle_boss_entry(self, clan_battle_boss_entry: ClanBattleBossEntry):
        try:
            with self.pool as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        INSERT INTO clan_battle_boss_entry (message_id, 
                            clan_battle_period_id, 
                            clan_battle_boss_id, 
                            name, 
                            image_path, 
                            boss_round, 
                            current_health, 
                            max_health
                        ) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (clan_battle_boss_entry.message_id,
                         clan_battle_boss_entry.clan_battle_period_id,
                         clan_battle_boss_entry.clan_battle_boss_id,
                         clan_battle_boss_entry.name,
                         clan_battle_boss_entry.image_path,
                         clan_battle_boss_entry.boss_round,
                         clan_battle_boss_entry.current_health,
                         clan_battle_boss_entry.max_health)
                    )
                    clan_battle_boss_entry.clan_battle_boss_entry_id = cursor.lastrowid
                conn.commit()
                return clan_battle_boss_entry
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()
            return None

    def get_last_by_message_id(self, message_id: int):
        try:
            with self.pool as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        SELECT clan_battle_boss_entry_id,
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
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return None

    def update_on_attack(self, clan_battle_boss_entry_id: int, current_health: int):
        try:
            with self.pool as conn:
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
                    conn.commit()
                    return True
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()
            return False

class ClanBattleBossBookRepository:
    def __init__(self):
        self.pool = db_pool

    def get_all_by_message_id(self, message_id: int):
        try:
            with self.pool as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        SELECT CBBB.clan_battle_boss_book_id,
                               CBBB.clan_battle_boss_entry_id,
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
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return []

    def get_one_by_message_id_and_player_id(self, message_id: int, player_id: int):
        try:
            with self.pool as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        SELECT CBBB.clan_battle_boss_book_id,
                               CBBB.clan_battle_boss_entry_id,
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
                            player_id=result['player_id'],
                            player_name=result['player_name'],
                            attack_type=result['attack_type'],
                            damage=result['damage'],
                            clan_battle_overall_entry_id=result['clan_battle_overall_entry_id'],
                            leftover_time=result['leftover_time'],
                            entry_date=result['entry_date']
                        )
                    return None
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return None

    def check_book_count_by_player_id(self, guild_id: int, player_id: int):
        try:
            with self.pool as conn:
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
                              AND CBBB.entry_date BETWEEN (DATE(SYSDATE()) + INTERVAL 4 HOUR) AND (DATE(SYSDATE()) + INTERVAL 1 DAY + INTERVAL 4 HOUR)
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
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return 0

    def delete_book_by_id(self, clan_battle_boss_book_id: int):
        try:
            with self.pool as conn:
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
                    conn.commit()
                    return True
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()
            return False

    def insert_boss_book_entry(self, clan_battle_boss_book: ClanBattleBossBook):
        try:
            with self.pool as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        INSERT INTO KurikoneCbBot.clan_battle_boss_book (
                            clan_battle_boss_book_id, 
                            clan_battle_boss_entry_id, 
                            player_id, 
                            player_name, 
                            attack_type, 
                            damage, 
                            clan_battle_overall_entry_id, 
                            leftover_time,
                            entry_date
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, SYSDATE())
                        """,
                        (
                            clan_battle_boss_book.clan_battle_boss_entry_id,
                            clan_battle_boss_book.clan_battle_boss_entry_id,
                            clan_battle_boss_book.player_id,
                            clan_battle_boss_book.player_name,
                            clan_battle_boss_book.attack_type.name,
                            clan_battle_boss_book.damage,
                            clan_battle_boss_book.clan_battle_overall_entry_id,
                            clan_battle_boss_book.leftover_time
                        )
                    )
                    clan_battle_boss_book.clan_battle_boss_book_id = cursor.lastrowid
                conn.commit()
                return clan_battle_boss_book
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()
            return None

    def update_damage_boss_book_by_id(self, clan_battle_boss_book_id: int, damage: int):
        try:
            with self.pool as conn:
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
                    conn.commit()
                    return True
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()
            return False


class ClanBattlePeriodRepository:
    def __init__(self):
        self.pool = db_pool

    def get_current_running_clan_battle_period(self):
        try:
            with self.pool as conn:
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
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return None


class ClanBattleBossRepository:
    def __init__(self):
        self.pool = db_pool

    def get_one_by_clan_battle_boss_id(self, clan_battle_boss_id: int):
        try:
            with self.pool as conn:
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
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return None


class ClanBattleBossHealthRepository:
    def __init__(self):
        self.pool = db_pool

    def get_one_by_position_and_round(self, position: int, boss_round: int):
        try:
            with self.pool as conn:
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
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return None


class ClanBattleOverallEntryRepository:
    def __init__(self):
        self.pool = db_pool

    def get_all_by_guild_id_boss_id_and_round(self, guild_id: int, clan_battle_boss_id: int, boss_round: int):
        try:
            with self.pool as conn:
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
                                overall_parent_entry_id,
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
                                overall_parent_entry_id=row['overall_parent_entry_id'],
                                entry_date=row['entry_date']
                            )
                            entries.append(entry)
                        return entries
                    return []
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return []

    def insert(self, cb_overall_entry: ClanBattleOverallEntry):
        try:
            with self.pool as conn:
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
                            overall_parent_entry_id, 
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
                            cb_overall_entry.overall_parent_entry_id
                        )
                    )
                    cb_overall_entry.clan_battle_overall_entry_id = cursor.lastrowid
                conn.commit()
                return cb_overall_entry
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()
            return None

    def update_overall_link(self, cb_overall_entry_id: int, overall_parent_entry_id: int):
        try:
            with self.pool as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        UPDATE clan_battle_overall_entry
                        SET overall_parent_entry_id = ?
                        WHERE clan_battle_overall_entry_id = ?
                        
                        """,
                        (
                            overall_parent_entry_id,
                            cb_overall_entry_id
                        )
                    )
                    conn.commit()
                    return True
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            conn.rollback()
            return False

    def get_entry_count_by_guild_id_and_player_id(self, guild_id: int, player_id: int):
        try:
            with self.pool as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(CBOE.clan_battle_overall_entry_id) AS entry_count
                        FROM clan_battle_overall_entry CBOE
                                 JOIN clan_battle_period CBP ON CBP.clan_battle_period_id = CBOE.clan_battle_period_id
                                 JOIN clan_battle_boss CBB ON CBOE.clan_battle_boss_id = CBB.clan_battle_boss_id
                        WHERE CBOE.guild_id = ?
                          AND CBOE.player_id = ?
                          AND CBOE.overall_parent_entry_id IS NULL
                          AND DATE(SYSDATE()) BETWEEN CBP.date_from AND CBP.date_to
                          AND CBOE.entry_date BETWEEN (DATE(SYSDATE()) + INTERVAL 4 HOUR) AND (DATE(SYSDATE()) + INTERVAL 1 DAY + INTERVAL 4 HOUR)

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
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return 0

    def get_leftover_by_guild_id_and_player_id(self, guild_id: int, player_id: int):
        try:
            with self.pool as conn:
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
                          AND CBOE.overall_parent_entry_id IS NULL
                          AND DATE(SYSDATE()) BETWEEN CBP.date_from AND CBP.date_to
                          AND CBOE.entry_date BETWEEN (DATE(SYSDATE()) + INTERVAL 4 HOUR) AND (DATE(SYSDATE()) + INTERVAL 1 DAY + INTERVAL 4 HOUR)

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
        except mariadb.Error as e:
            traceback.print_exc()
            print(f"Database Error : {e}")
            return []