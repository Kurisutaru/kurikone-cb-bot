import asyncio
import traceback
import uuid

from discord import Embed, Message, TextChannel
from discord.abc import GuildChannel
from globals import locale, logger

from repository import *
from transactional import transactional, transaction_rollback

import utils

l = locale
log = logger

class Services:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Services, cls).__new__(cls)
            cls._instance.guild_repo = GuildRepository()
            cls._instance.channel_repo = ChannelRepository()
            cls._instance.channel_message_repo = ChannelMessageRepository()
            cls._instance.clan_battle_boss_entry_repo = ClanBattleBossEntryRepository()
            cls._instance.clan_battle_boss_book_repo = ClanBattleBossBookRepository()
            cls._instance.clan_battle_period_repo = ClanBattlePeriodRepository()
            cls._instance.clan_battle_boss_repo = ClanBattleBossRepository()
            cls._instance.clan_battle_boss_health_repo = ClanBattleBossHealthRepository()
            cls._instance.clan_battle_overall_entry_repo = ClanBattleOverallEntryRepository()
            cls._instance.guild_player_repo = GuildPlayerRepository()
            cls._instance.clan_battle_report_message_repo = ClanBattleReportMessageRepository()
            cls._instance.generic_repo = GenericRepository()
            cls._instance.error_log_repo = ErrorLogRepository()
        return cls._instance

    @transactional
    async def error_log_db(self, guild_id: int, exception: Exception, transaction_id: str):
        """Logs errors to the database with a UUID reference.
        Guarantees the log is written even if the main transaction fails.
        """
        try:
            # Capture the traceback as a string (works even outside exception context)
            stacktrace = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__)).rstrip()

            self.error_log_repo.insert(
                guild_id=guild_id,
                identifier=transaction_id,
                exception=str(exception),
                stacktrace=stacktrace,
            )
            log.error(f"[{transaction_id}] Error: {exception}\n{stacktrace}")
        except Exception as e:
            # Critical fallback: If DB logging fails, log to console + external service (e.g., Sentry)
            log.critical(
                f"FAILED to log error {transaction_id}. Falling back to console.",
                exc_info=e
            )
            # Optionally, add a fallback mechanism (e.g., file log, Sentry, etc.)

    def gen_id(self) -> str:
        trx_id = str(uuid.uuid4())
        return trx_id

_service = Services()

class MainService:
    @transactional
    async def setup_guild_channel_message(self, guild: discord.Guild, tl_shifter_channel: dict) -> \
            ServiceResult[None]:
        service_result = ServiceResult[None]()
        guild_id = guild.id
        try:
            # Master CB Data
            clan_battle_period = _service.clan_battle_period_repo.get_current_cb_period()

            if clan_battle_period is None:
                log.error("Need Database setup !")
                return service_result.set_error("Need Database setup !")

            guild_db = await self.guild_setup(guild_id=guild_id, guild_name=guild.name)
            if not guild_db.is_success:
                raise guild_db.error_messages

            channel_result = await self.setup_channel(guild)
            if not channel_result.is_success:
                raise channel_result.error_messages

            for enum, channel in channel_result.result:
                #Category doing nothing, pass
                if enum == ChannelEnum.CATEGORY:
                    continue

                # For TL Shifting watcher
                if enum == ChannelEnum.TL_SHIFTER and channel:
                    tl_shifter_channel[channel.id] = None
                    continue

                #Report
                if enum == ChannelEnum.REPORT and channel:
                    message = await self.setup_channel_report_message(channel)
                    if not message.is_success:
                        raise message.error_messages
                    continue

                # Boss Channel
                # Return if not enum named boss
                if "boss" in enum.name.lower():
                    message = await self.setup_channel_boss_message(enum, channel)
                    if not message.is_success:
                        raise message.error_messages

            service_result.set_success(None)

        except Exception as e:
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result

    # Guild Setup
    async def guild_setup(self, guild_id: int, guild_name: str) -> ServiceResult[Guild]:
        service_result = ServiceResult[Guild]()
        try:
            # logger.warning(f"Session Connection ID @guild_setup : {_service.generic_repo.get_connection_id()}")
            # logger.warning(f"Session Transaction Isolation @guild_setup : {_service.generic_repo.get_session_transaction_isolation()}")
            # logger.warning(f"Session Autocommit @guild_setup : {_service.generic_repo.get_session_autocommit()}")
            # logger.warning(f"Session Transaction ID @guild_setup : {_service.generic_repo.get_session_transaction_id()}")
            guild_db = _service.guild_repo.get_by_guild_id(guild_id)
            if guild_db is None:
                guild_db = _service.guild_repo.insert_guild(Guild(guild_id, guild_name))

            service_result.set_success(guild_db)
        except Exception as e:
            transaction_rollback()
            service_result.set_error(str(e))

        return service_result

    # Channel Setup
    async def setup_channel(self, guild: discord.Guild) -> ServiceResult[list[tuple[ChannelEnum, GuildChannel]]]:
        service_result = ServiceResult[list[tuple[ChannelEnum, GuildChannel]]]()
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
            }

            overwrites_tl_shifter = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }

            guild_channel = _service.channel_repo.get_all_by_guild_id(guild.id)
            processed_channel = []
            category_channel = None

            for enum in ChannelEnum:
                channel_data = next((channel for channel in guild_channel if channel.channel_type == enum), None)
                # Assume no Channel Exist for specific enum
                if channel_data is None:
                    local_overwrites = overwrites
                    if enum == ChannelEnum.TL_SHIFTER:
                        local_overwrites = overwrites_tl_shifter

                    if enum == ChannelEnum.CATEGORY:
                        channel = await guild.create_category(
                            name=ChannelEnum.CATEGORY.value['name'],
                            overwrites=overwrites
                        )
                        category_channel = channel
                    else:
                        channel = await guild.create_text_channel(
                            name=enum.value['name'],
                            category=category_channel,
                            overwrites=local_overwrites
                        )

                    _service.channel_repo.insert_channel(Channel(channel_id=channel.id,
                                                                                      guild_id=guild.id,
                                                                                      channel_type=enum))
                    processed_channel.append((enum, channel))
                else:
                    channel = guild.get_channel(channel_data.channel_id)
                    processed_channel.append((enum, channel))

            service_result.set_success(processed_channel)

        except Exception as e:
            transaction_rollback()
            service_result.set_error(str(e))

        return service_result

    # Channel Report to Message Setup
    async def setup_channel_report_message(self, channel: GuildChannel) -> ServiceResult[
        Optional[Message]]:
        service_result = ServiceResult[Optional[Message]]()
        try:
            if not isinstance(channel, TextChannel):
                return service_result

            result = await self.refresh_report_channel_message(channel.guild)
            if not result.is_success:
                service_result.set_error(result.error_messages)
                return service_result

            service_result.set_success(result.result)

        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))

        return service_result


    # Channel Boss to Message Setup
    async def setup_channel_boss_message(self, enum: ChannelEnum, channel: GuildChannel) -> ServiceResult[
        Optional[Message]]:
        service_result = ServiceResult[Optional[Message]]()
        try:
            if not isinstance(channel, TextChannel):
                return service_result

            guild_id = channel.guild.id

            # Get Message from Database
            ch_message = _service.channel_message_repo.get_channel_message_by_channel_id(channel_id=channel.id)

            if ch_message is None:
                message = await channel.send(content=l.t(guild_id, "ui.status.preparing_data"))
                ch_message = ChannelMessage(
                    channel_id=channel.id,
                    message_id=message.id,
                )
                _service.channel_message_repo.insert_channel_message(ch_message)

            period = _service.clan_battle_period_repo.get_current_cb_period()
            boss_id = getattr(period, f"{enum.value['type'].lower()}_id")

            cb_entry = _service.clan_battle_boss_entry_repo.get_last_by_message_id(message_id=ch_message.message_id)
            message = await utils.discord_try_fetch_message(channel, ch_message.message_id)

            # Main logic flow
            if message is None:
                # Case when message doesn't exist (was deleted)
                message = await channel.send(content=l.t(guild_id, "ui.status.preparing_data"))
                ch_message = ChannelMessage(
                    channel_id=channel.id,
                    message_id=message.id,
                )

                if cb_entry:
                    # Update existing entry with new message ID
                    cb_entry.message_id = message.id
                    _service.clan_battle_boss_entry_repo.update_message_id(cb_entry.clan_battle_boss_entry_id, message.id)
                else:
                    # Create new entry since neither message nor entry exists
                    await self.insert_clan_battle_entry_by_round(
                        guild_id=guild_id,
                        message_id=message.id,
                        boss_id=boss_id,
                        period_id=period.clan_battle_period_id,
                        boss_round=1
                    )

                # Update channel message in both cases
                _service.channel_message_repo.update_channel_message(ch_message)

            elif cb_entry is None:
                # Case when message exists but no entry exists
                await self.insert_clan_battle_entry_by_round(
                    guild_id=guild_id,
                    message_id=message.id,
                    boss_id=boss_id,
                    period_id=period.clan_battle_period_id,
                    boss_round=1
                )

            #Refresh the bosses
            embeds = await self.refresh_clan_battle_boss_embeds(guild_id, message)
            if embeds.is_success:
                import ui
                await message.edit(content="", embeds=embeds.result, view=ui.ButtonView(guild_id))

            service_result.set_success(message)

        except Exception as e:
            transaction_rollback()
            log.error(e)
            service_result.set_error(str(e))

        return service_result

    async def insert_clan_battle_entry_by_round(self, guild_id: int, message_id: int, boss_id: int, period_id: int,
                                                boss_round: int) -> ServiceResult[ClanBattleBossEntry]:
        service_result = ServiceResult[ClanBattleBossEntry]()

        try:
            cb_boss = _service.clan_battle_boss_repo.fetch_clan_battle_boss_by_id(boss_id)
            cb_boss_health = _service.clan_battle_boss_health_repo.get_one_by_position_and_round(
                position=cb_boss.position, boss_round=boss_round)

            if cb_boss is None:
                service_result.set_error(f"Boss is None")
                return service_result

            if cb_boss_health is None:
                service_result.set_error(f"Boss health is None")
                return service_result

            cb_entry = ClanBattleBossEntry(
                guild_id=guild_id,
                message_id=message_id,
                clan_battle_period_id=period_id,
                clan_battle_boss_id=cb_boss.clan_battle_boss_id,
                name=f"{cb_boss.name} 「{cb_boss.description}」",
                image_path=cb_boss.image_path,
                boss_round=1,
                current_health=cb_boss_health.health,
                max_health=cb_boss_health.health,
            )

            cb_entry = _service.clan_battle_boss_entry_repo.insert_clan_battle_boss_entry(cb_entry)
            service_result.set_success(cb_entry)

        except Exception as e:
            transaction_rollback()
            log.error(e)
            service_result.set_error(str(e))

        return service_result

    async def refresh_clan_battle_boss_embeds(self, guild_id: int, message_id: int) -> ServiceResult[list[Embed]]:
        service_result = ServiceResult[list[Embed]]()
        try:
            embeds = []
            message_id = message_id
            guild_id = guild_id

            # Header
            entry = _service.clan_battle_boss_entry_repo.get_last_by_message_id(message_id=message_id)

            embeds.append(utils.create_header_embed(guild_id, entry))

            # Entry
            cb_overall_repository = ClanBattleOverallEntryRepository()
            done_entries = cb_overall_repository.get_all_by_guild_id_boss_id_and_round(guild_id=guild_id,
                                                                                       clan_battle_boss_id=entry.clan_battle_boss_id,
                                                                                       boss_round=entry.boss_round)

            if len(done_entries) > 0:
                embeds.append(utils.create_done_embed(guild_id, done_entries))

            # Book
            book_entries = _service.clan_battle_boss_book_repo.get_all_by_message_id(message_id=message_id)

            if len(book_entries) > 0:
                embeds.append(utils.create_book_embed(guild_id, book_entries))

            service_result.set_success(embeds)

        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))

        return service_result

    @transactional
    async def done_entry(self, guild_id: int, message_id: int, user_id: int, display_name: str) -> \
            ServiceResult[None]:
        service_result = ServiceResult[None]()

        try:

            book = _service.clan_battle_boss_book_repo.get_player_book_entry(message_id, user_id)
            if book is None:
                service_result.set_error(f"Book result is None")
                return service_result

            boss_entry = _service.clan_battle_boss_entry_repo.get_last_by_message_id(message_id)
            if boss_entry is None:
                service_result.set_error(f"Boss entry is None")
                return service_result

            period = _service.clan_battle_period_repo.get_current_cb_period()
            if period is None:
                service_result.set_error(f"Period is None")
                return service_result

            _service.clan_battle_boss_book_repo.delete_book_by_id(book.clan_battle_boss_book_id)

            # Prepare insert into overall Entry
            cb_overall_repository = ClanBattleOverallEntryRepository()
            overall = cb_overall_repository.insert(cb_overall_entry=ClanBattleOverallEntry(
                                                       guild_id=guild_id,
                                                       clan_battle_period_id=period.clan_battle_period_id,
                                                       clan_battle_boss_id=boss_entry.clan_battle_boss_id,
                                                       player_id=user_id,
                                                       player_name=display_name,
                                                       boss_round=boss_entry.boss_round,
                                                       attack_type=book.attack_type,
                                                       damage=book.damage
                                                   )
                                                   )

            if not book.clan_battle_overall_entry_id is None:
                _service.clan_battle_overall_entry_repo.update_overall_link(cb_overall_entry_id=book.clan_battle_overall_entry_id,
                                                                                 overall_leftover_entry_id=overall.clan_battle_overall_entry_id)

            # Update Boss Entry
            _service.clan_battle_boss_entry_repo.update_on_attack(clan_battle_boss_entry_id=boss_entry.clan_battle_boss_entry_id,
                                                                       current_health=utils.reduce_int_ab_non_zero(
                                                                           boss_entry.current_health,
                                                                           book.damage))

            service_result.set_success(None)
        except Exception as e:
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result

    @transactional
    async def dead_ok(self, guild_id: int, message_id: int, user_id: int, display_name: str, leftover_time: int
                      ) -> ServiceResult[ClanBattleOverallEntry]:
        service_result = ServiceResult[ClanBattleOverallEntry]()
        try:

            book = _service.clan_battle_boss_book_repo.get_player_book_entry(message_id, user_id)
            if book is None:
                service_result.set_error(f"Book result is None")
                return service_result

            # Get CB Entry
            boss_entry = _service.clan_battle_boss_entry_repo.get_last_by_message_id(message_id)
            if boss_entry is None:
                service_result.set_error(f"Boss entry is None")
                return service_result

            period = _service.clan_battle_period_repo.get_current_cb_period()
            if period is None:
                service_result.set_error(f"Period is None")
                return service_result

            _service.clan_battle_boss_book_repo.delete_book_by_id(book.clan_battle_boss_book_id)

            # Prepare insert into overall Entry
            overall = _service.clan_battle_overall_entry_repo.insert(cb_overall_entry=ClanBattleOverallEntry(
                                                                              guild_id=guild_id,
                                                                              clan_battle_period_id=period.clan_battle_period_id,
                                                                              clan_battle_boss_id=boss_entry.clan_battle_boss_id,
                                                                              player_id=user_id,
                                                                              player_name=display_name,
                                                                              boss_round=boss_entry.boss_round,
                                                                              attack_type=book.attack_type,
                                                                              damage=book.damage,
                                                                              leftover_time=None if book.attack_type == AttackTypeEnum.CARRY else leftover_time
                                                                          )
                                                                          )

            # Update Boss Entry
            _service.clan_battle_boss_entry_repo.update_on_attack(clan_battle_boss_entry_id=boss_entry.clan_battle_boss_entry_id,
                                                                       current_health=utils.reduce_int_ab_non_zero(
                                                                           boss_entry.current_health,
                                                                           book.damage))

            if not book.clan_battle_overall_entry_id is None:
                _service.clan_battle_overall_entry_repo.update_overall_link(cb_overall_entry_id=book.clan_battle_overall_entry_id,
                                                                                 overall_leftover_entry_id=overall.clan_battle_overall_entry_id)

            service_result.set_success(overall)
        except Exception as e:
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result

    @transactional
    async def generate_next_boss(self, interaction: discord.interactions.Interaction, boss_id: int,
                                 message_id: int, attack_type: AttackTypeEnum, leftover_time: int) -> \
            ServiceResult[ClanBattleBossEntry]:
        service_result = ServiceResult[ClanBattleBossEntry]()

        try:
            message_id = message_id
            guild_id = interaction.guild_id
            channel_id = interaction.channel.id
            # Get CB Entry
            boss_entry = _service.clan_battle_boss_entry_repo.get_last_by_message_id(message_id)
            if boss_entry is None:
                service_result.set_error(f"Boss entry is None")
                return service_result

            # Edit Old one
            prev_msg = await utils.discord_try_fetch_message(channel=interaction.channel, message_id=message_id)
            if prev_msg is None:
                service_result.set_error(f"Previous message is not found")
                return service_result

            done_entries = _service.clan_battle_overall_entry_repo.get_all_by_guild_id_boss_id_and_round(
                guild_id=guild_id,
                clan_battle_boss_id=boss_entry.clan_battle_boss_id,
                boss_round=boss_entry.boss_round)

            await prev_msg.edit(content="", embeds=[
                utils.create_header_embed(guild_id=guild_id, cb_boss_entry=boss_entry, include_image=False,
                                          default_color=discord.Color.dark_grey()),
                utils.create_done_embed(guild_id=guild_id, list_cb_overall_entry=done_entries,
                                        default_color=discord.Color.dark_grey())],
                view=None)

            # Generate New One
            await utils.send_channel_message(interaction=interaction,
                content=f"{l.t(guild_id, "ui.events.boss_killed", user=interaction.user.display_name, attack_type=attack_type.value, leftover_time=leftover_time)}")

            next_round = boss_entry.boss_round + 1

            boss = _service.clan_battle_boss_repo.fetch_clan_battle_boss_by_id(boss_id)
            if boss is None:
                service_result.set_error(f"Boss entry is None")
                return service_result

            health = _service.clan_battle_boss_health_repo.get_one_by_position_and_round(
                position=boss.position, boss_round=next_round)

            if health is None:
                service_result.set_error(f"Boss Health is None")
                return service_result

            period = _service.clan_battle_period_repo.get_current_cb_period()
            if health is None:
                service_result.set_error(f"Period is None")
                return service_result

            new_message = await interaction.channel.send(content=l.t(guild_id, "ui.status.preparing_data"))
            channel_message = ChannelMessage(
                channel_id=channel_id,
                message_id=new_message.id,
            )

            _service.channel_message_repo.update_channel_message(channel_message)

            boss_entry = ClanBattleBossEntry(
                guild_id=guild_id,
                message_id=new_message.id,
                clan_battle_period_id=period.clan_battle_period_id,
                clan_battle_boss_id=boss.clan_battle_boss_id,
                name=f"{boss.name} 「{boss.description}」",
                image_path=boss.image_path,
                boss_round=next_round,
                current_health=health.health,
                max_health=health.health,
            )

            _service.clan_battle_boss_entry_repo.insert_clan_battle_boss_entry(boss_entry)

            service_result.set_success(boss_entry)
        except Exception as e:
            transaction_rollback()
            log.error(e)
            service_result.set_error(str(e))
            print(e)

        return service_result

    @transactional
    async def insert_boss_book_entry(self, guild_id: int, message_id: int, user_id: int, display_name: str,
                                     attack_type: AttackTypeEnum, parent_overall_id: int = None,
                                     leftover_time: int = None) -> ServiceResult[ClanBattleBossBook]:
        service_result = ServiceResult[ClanBattleBossBook]()
        try:

            book_count = _service.clan_battle_boss_book_repo.get_player_book_count(guild_id, user_id)
            if book_count is None:
                service_result.set_error(f"Player Book Count not found")
                return service_result

            boss_entry = _service.clan_battle_boss_entry_repo.get_last_by_message_id(message_id)
            if boss_entry is None:
                service_result.set_error(f"Boss entry not found")
                return service_result

            cb_book = ClanBattleBossBook(
                clan_battle_boss_entry_id=boss_entry.clan_battle_boss_entry_id,
                guild_id=guild_id,
                player_id=user_id,
                player_name=display_name,
                attack_type=attack_type,
                clan_battle_overall_entry_id=parent_overall_id,
                leftover_time=leftover_time
            )

            result = _service.clan_battle_boss_book_repo.insert_boss_book_entry(cb_book)
            service_result.set_success(result)

        except Exception as e:
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result


    @transactional
    async def install_bot_command(self, guild: discord.Guild, tl_shifter_channel: dict) -> ServiceResult[None]:
        service_result = ServiceResult[None]()
        try:
            guild_result = _service.guild_repo.get_by_guild_id(guild.id)
            if guild_result:
                service_result.set_error(l.t(guild.id, ""))
                return service_result

            setup = await self.setup_guild_channel_message(guild, tl_shifter_channel)
            if not setup.is_success:
                service_result.set_error(setup.error_messages)
                return service_result

            service_result.set_success(None)

        except Exception as e:
            transaction_rollback()
            log.error(e)
            service_result.set_error(str(e))

        return service_result

    @transactional
    async def uninstall_bot_command(self, guild: discord.Guild, tl_shifter_channel: dict) -> ServiceResult[list[int]]:
        service_result = ServiceResult[list[int]]()
        guild_id = guild.id
        try:
            guild_result = _service.guild_repo.get_by_guild_id(guild_id)
            if guild_result is None:
                service_result.set_error(l.t(guild_id, "message.guild_uninstalled"))
                return service_result

            # Get all related to the guild and remove all of them, including the CB Data

            # Clan Battle Boss Entry
            _service.clan_battle_boss_entry_repo.delete_by_guild_id(guild_id)

            # Clan Battle Boss Book
            _service.clan_battle_boss_book_repo.delete_by_guild_id(guild_id)

            # Clan Battle Overall Entry
            _service.clan_battle_overall_entry_repo.delete_by_guild_id(guild_id)

            # Clan Battle Report Message
            _service.clan_battle_report_message_repo.delete_by_guild_id(guild_id)

            # Guild Player
            _service.guild_player_repo.delete_by_guild_id(guild_id)

            # Channel Message
            _service.channel_message_repo.delete_by_guild_id(guild_id)

            # Channel
            channels = _service.channel_repo.get_all_by_guild_id(guild_id)
            if channels is None or len(channels) == 0:
                service_result.set_error("Channel not found")
                return service_result

            _service.channel_repo.delete_channel_by_guild_id(guild_id)

            # Guild
            _service.guild_repo.delete_by_guild_id(guild_id)

            # Error Log
            _service.error_log_repo.delete_by_guild_id(guild_id)

            # Remove TL-Shifter listener from global dictionary
            tl_shifter_channel.pop(guild.id, None)

            channels = [item.channel_id for item in channels]

            service_result.set_success(channels)

        except Exception as e:
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result

    @transactional
    async def sync_user_role(self, guild_id: int, members: list[GuildPlayer]) -> ServiceResult[None]:
        service_result = ServiceResult[None]()

        try:
            _service.guild_player_repo.delete_by_guild_id(guild_id)

            player_data = [
                (player.guild_id, player.player_id, player.player_name)
                for player in members
            ]

            _service.guild_player_repo.batch_insert(player_data)

            service_result.set_success(None)

        except Exception as e:
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result

    async def generate_report_text(self, guild_id:int, year:int, month:int, day:int) -> ServiceResult[str]:
        service_result = ServiceResult[str]()

        try:
            header = _service.clan_battle_period_repo.get_by_param(year, month)
            entries = _service.clan_battle_overall_entry_repo.get_report_entry_by_param(guild_id, year, month, day)

            result = f"# {header.clan_battle_period_name} - {l.t(guild_id, "ui.status.day", day=day)}{NEW_LINE}"

            sum_patk_count = sum(entry.patk_count for entry in entries) if entries else 0
            sum_matk_count = sum(entry.matk_count for entry in entries) if entries else 0
            sum_leftover_count = sum(entry.leftover_count for entry in entries) if entries else 0
            sum_carry_count = sum(entry.carry_count for entry in entries) if entries else 0


            result += f"```powershell{NEW_LINE}{l.t(guild_id, "ui.label.entry_summary")} | {AttackTypeEnum.PATK.value}: {sum_patk_count} {AttackTypeEnum.MATK.value}: {sum_matk_count} {AttackTypeEnum.CARRY.value}: {sum_carry_count} {AttackTypeEnum.LEFTOVER.value}: {sum_leftover_count} |{NEW_LINE}```"
            result += f"```powershell{NEW_LINE}"

            if len(entries):
                for data in entries:
                    result += f"| {AttackTypeEnum.PATK.value}: {data.patk_count} {AttackTypeEnum.MATK.value}: {data.matk_count} {AttackTypeEnum.CARRY.value}: {data.carry_count} {AttackTypeEnum.LEFTOVER.value}: {data.leftover_count} | {data.player_name.ljust(20)[:20]} {NEW_LINE}"
            else:
                result += f"{l.t(guild_id,"ui.status.not_synced")}{NEW_LINE}"
            result += f"```"
            service_result.set_success(result)

        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))

        return service_result


    @transactional
    async def refresh_report_channel_message(self, guild: discord.Guild) -> ServiceResult[Optional[Message]]:
        service_result = ServiceResult[Optional[Message]]()
        guild_id = guild.id
        # Current date info
        current_date = utils.now()
        try:
            log.info(f"Refreshing Clan Battle Report Daily on {guild.name} - {guild.id}")
            # Get current CB period once
            cur_period = _service.clan_battle_period_repo.get_current_cb_period_day()
            if cur_period.current_day == -1:
                service_result.set_error("No Running Clan Battle period detected")
                return service_result

            # Get channel data once
            channel_data = _service.channel_repo.get_all_by_guild_id_and_type(guild_id, ChannelEnum.REPORT.name)
            if channel_data is None:
                service_result.set_error("No Report channel found")
                return service_result

            channel = guild.get_channel(channel_data.channel_id)
            if channel is None:
                service_result.set_error("Report channel not found in guild")
                return service_result

            # Get or create base report message
            report_message_data = _service.channel_message_repo.get_channel_message_by_channel_id(channel.id)
            if report_message_data is None:
                report_message = await channel.send(content=l.t(guild_id, "ui.status.preparing_data"))
                channel_message = ChannelMessage(channel_id=channel.id, message_id=report_message.id)
                _service.channel_message_repo.insert_channel_message(channel_message)
            else:
                report_message = await utils.discord_try_fetch_message(channel, report_message_data.message_id)
                if report_message is None:
                    report_message = await channel.send(content=l.t(guild_id, "ui.status.preparing_data"))
                    report_message_data.message_id = report_message.id
                    _service.channel_message_repo.update_channel_message(report_message_data)

            # Get latest CB report message from DB
            cb_report_message_data = _service.clan_battle_report_message_repo.get_last_by_guild_period(
                guild_id, cur_period.clan_battle_period_id
            )

            # If no existing report message, create one with current day
            if cb_report_message_data is None:
                cb_report_message_data = ClanBattleReportMessage(
                    guild_id=guild_id,
                    clan_battle_period_id=cur_period.clan_battle_period_id,
                    day=cur_period.current_day,
                    message_id=report_message.id
                )
                _service.clan_battle_report_message_repo.insert(cb_report_message_data)

            # Always update the existing message first
            report_gen = await self.generate_report_text(
                guild_id,
                current_date.year,
                current_date.month,
                cb_report_message_data.day
            )

            if not report_gen.is_success:
                service_result.set_error(report_gen.error_messages)
                return service_result

            embed = Embed(description=report_gen.result, color=discord.Colour.blurple())
            await report_message.edit(content="", embed=embed)

            # Then check if we need a new message for new day
            if cur_period.current_day > cb_report_message_data.day:
                new_report_message = await channel.send(content=l.t(guild_id, "ui.status.preparing_data"))
                report_message_data.message_id = new_report_message.id
                _service.channel_message_repo.update_channel_message(report_message_data)

                new_cb_report_message_data = ClanBattleReportMessage(
                    guild_id=guild_id,
                    clan_battle_period_id=cur_period.clan_battle_period_id,
                    day=cur_period.current_day,
                    message_id=new_report_message.id
                )
                _service.clan_battle_report_message_repo.insert(new_cb_report_message_data)

                # Generate report for new day
                new_report_gen = await self.generate_report_text(
                    guild_id,
                    current_date.year,
                    current_date.month,
                    cur_period.current_day
                )

                if not new_report_gen.is_success:
                    service_result.set_error(new_report_gen.error_messages)
                    return service_result

                new_embed = Embed(description=new_report_gen.result, color=discord.Colour.blurple())
                await new_report_message.edit(content="", embed=new_embed)
                service_result.set_success(new_report_message)
                return service_result

            service_result.set_success(report_message)
        except Exception as e:
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result


    @transactional
    async def new_clan_battle_period(self, guild: discord.Guild) -> ServiceResult[None]:
        service_result = ServiceResult[None]()
        guild_id = guild.id
        # Current date info
        current_date = utils.now()
        try:
            log.info(f"Generating New Clan Battle Period on {guild.name} - {guild.id}")
            # Get current CB period once
            period = _service.clan_battle_period_repo.get_current_cb_period_day()
            if period.current_day == -1:
                service_result.set_error("No Running Clan Battle period detected")
                return service_result

            # Get channel data once
            channel_data = _service.channel_repo.get_boss_channel_by_guild_id(guild_id)
            if channel_data is None:
                service_result.set_error("Guild channel not found")
                return service_result

            # Loop through boss Channel
            for chan in channel_data:
                channel = guild.get_channel(chan.channel_id)
                if channel is None:
                    service_result.set_error("Channel not found in guild")
                    return service_result

                # Get ChannelMessage for MessageId, to get old message and edit remove the button view and make it dark
                ch_message = _service.channel_message_repo.get_channel_message_by_channel_id(channel_id=channel.id)
                if ch_message is None:
                    service_result.set_error("Channel Message not found in guild")
                    return service_result

                cur_msg = await utils.discord_try_fetch_message(channel, ch_message.message_id)
                if cur_msg:
                    # Set the embed color daaark
                    for embed in cur_msg.embeds:
                        embed.colour = discord.Colour.dark_grey()
                    await cur_msg.edit(content=None, embeds=cur_msg.embeds, view=None)

                # Create new one without touching old one
                message = await channel.send(content=l.t(guild_id, "ui.status.preparing_data"))
                ch_message.message_id = message.id
                _service.channel_message_repo.update_channel_message(ch_message)

                boss_id = getattr(period, f"{chan.channel_type.value['type'].lower()}_id")

                await self.insert_clan_battle_entry_by_round(
                    guild_id=guild_id,
                    message_id=message.id,
                    boss_id=boss_id,
                    period_id=period.clan_battle_period_id,
                    boss_round=1
                )

                # Refresh the bosses
                embeds = await self.refresh_clan_battle_boss_embeds(guild_id, message)
                if embeds.is_success:
                    import ui
                    await message.edit(content="", embeds=embeds.result, view=ui.ButtonView(guild_id))

            service_result.set_success(None)
        except Exception as e:
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result


class UiService:
    async def book_button_service(self, interaction: discord.Interaction) -> ServiceResult[Tuple[bool, int, list[ClanBattleLeftover]]]:
        service_result = ServiceResult[Tuple[bool, int, list[ClanBattleLeftover]]]()
        guild_id = interaction.guild_id
        try:
            user_id = interaction.user.id

            boss_book = _service.clan_battle_boss_book_repo.get_player_book_count(guild_id, user_id)
            if boss_book > 0:
                service_result.set_error(l.t(guild_id, "ui.status.booked"))
                return service_result

            entry_count = _service.clan_battle_overall_entry_repo.get_player_overall_entry_count(
                guild_id, user_id)

            count = entry_count

            disable = count == 3

            # generate Leftover ?
            leftover = _service.clan_battle_overall_entry_repo.get_leftover_by_guild_id_and_player_id(
                guild_id=guild_id, player_id=user_id)

            service_result.set_success((disable, utils.reduce_int_ab_non_zero(a=3, b=count), leftover))

        except Exception as e:
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result

    @transactional
    async def cancel_button_service(self, interaction: discord.Interaction) -> ServiceResult[list[Embed]]:
        service_result = ServiceResult[list[Embed]]()
        guild_id = interaction.guild_id
        try:
            user_id = interaction.user.id
            message_id = interaction.message.id

            book_result = _service.clan_battle_boss_book_repo.get_player_book_entry(
                message_id=message_id,
                player_id=user_id
            )

            if book_result is None:
                service_result.set_error(l.t(guild_id, "ui.validation.book_entry_not_found"))
                return service_result

            _service.clan_battle_boss_book_repo.delete_book_by_id(book_result.clan_battle_boss_book_id)
            embeds = await MainService().refresh_clan_battle_boss_embeds(guild_id, interaction.message)

            service_result.set_success(embeds.result)

        except Exception as e:
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result

    @transactional
    async def entry_input_service(self, interaction: discord.Interaction, user_input: str) -> ServiceResult[list[Embed]]:
        service_result = ServiceResult[list[Embed]]()
        guild_id = interaction.guild_id
        try:
            message_id = interaction.message.id
            if not user_input.isdigit():
                service_result.set_error(f"## {l.t(guild_id, "ui.validation.only_numbers_allowed")}")
                return service_result

            damage = int(user_input)

            if damage < 1:
                service_result.set_error(f"## {l.t(guild_id, "ui.validation.must_be_greater_than_zero")}")
                return service_result

            # Update damage
            book = _service.clan_battle_boss_book_repo.get_player_book_entry(
                message_id=interaction.message.id,
                player_id=interaction.user.id)

            if book is None:
                raise l.t(guild_id, "ui.validation.book_entry_not_found")


            _service.clan_battle_boss_book_repo.update_damage_boss_book_by_id(
                book.clan_battle_boss_book_id,
                damage)

            embeds = await MainService().refresh_clan_battle_boss_embeds(guild_id, message_id)
            service_result.set_success(embeds.result)

        except Exception as e:
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result

    async def done_button_service(self, interaction: discord.Interaction) -> ServiceResult[None]:
        service_result = ServiceResult[None]()
        guild_id = interaction.guild_id
        try:
            message_id = interaction.message.id
            user_id = interaction.user.id
            book_result = _service.clan_battle_boss_book_repo.get_player_book_entry(message_id, user_id)

            if book_result is None:
                service_result.set_error(f"## {l.t(guild_id, "ui.status.not_yet_booked")}")
                return service_result

            if book_result.damage is None:
                service_result.set_error(f"## {l.t(guild_id, "ui.validation.enter_entry_type_first")}")
                return service_result

            return service_result
        except Exception as e:
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result

    async def dead_button_service(self, interaction: discord.Interaction) -> ServiceResult[ClanBattleBossBook]:
        service_result = ServiceResult[ClanBattleBossBook]()
        guild_id = interaction.guild_id
        try:
            message_id = interaction.message.id
            user_id = interaction.user.id

            book = _service.clan_battle_boss_book_repo.get_player_book_entry(message_id, user_id)

            if book is None:
                service_result.set_error(f"## {l.t(guild_id, "ui.status.not_yet_booked")}")
                return service_result

            if book.damage is None:
                service_result.set_error(f"## {l.t(guild_id, "ui.validation.enter_entry_type_first")}")
                return service_result

            boss_entry = _service.clan_battle_boss_entry_repo.get_last_by_message_id(message_id)
            if book.damage < boss_entry.current_health:
                service_result.set_error(f"## {l.t(guild_id, "ui.validation.entry_damage_less_than_boss_hp")}")
                return service_result

            service_result.set_success(book)
        except Exception as e:
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(l.t(guild_id, "message.unhandled_exception", uuid=trx_id))

        return service_result

class GuildService:
    async def get_guild_by_id(self, guild_id: int) -> ServiceResult[Guild]:
        service_result = ServiceResult[Guild]()

        try:
            data = _service.guild_repo.get_by_guild_id(guild_id)
            service_result.set_success(data)

        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))
            print(e)

        return service_result

    @transactional
    async def insert_guild(self, guild_id: int, guild_name: str) -> ServiceResult[Guild]:
        service_result = ServiceResult[Guild]()

        try:
            guild = Guild(guild_id=guild_id, guild_name=guild_name)
            data = _service.guild_repo.insert_guild(guild)
            service_result.set_success(data)

        except Exception as e:
            transaction_rollback()
            log.error(e)
            service_result.set_error(str(e))
            print(e)

        return service_result


class ChannelService:

    async def get_all_by_guild_id(self, guild_id: int) -> ServiceResult[list[Channel]]:
        service_result = ServiceResult[list[Channel]]()

        try:
            data = _service.channel_repo.get_all_by_guild_id(guild_id)
            service_result.set_success(data)

        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))
            print(e)

        return service_result

    @transactional
    async def insert_channel(self, guild_id: int, channel_id: int, channel_type: ChannelEnum) -> \
            ServiceResult[Channel]:
        service_result = ServiceResult[Channel]()

        try:
            channel = Channel(channel_id=channel_id, guild_id=guild_id, channel_type=channel_type)
            data = _service.channel_repo.insert_channel(channel)
            service_result.set_success(data)

        except Exception as e:
            transaction_rollback()
            log.error(e)
            service_result.set_error(str(e))
            print(e)

        return service_result


class ClanBattlePeriodService:

    async def get_current_cb_period(self) -> ServiceResult[ClanBattlePeriod]:
        service_result = ServiceResult[ClanBattlePeriod]()
        try:
            data = _service.clan_battle_period_repo.get_current_cb_period()
            service_result.set_success(data)

        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))
            print(e)

        return service_result

    async def get_current_cb_period_day(self) -> ServiceResult[ClanBattlePeriodDay]:
        service_result = ServiceResult[ClanBattlePeriodDay]()
        try:
            data = _service.clan_battle_period_repo.get_current_cb_period_day()
            service_result.set_success(data)

        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))
            print(e)

        return service_result


class ClanBattleBossBookService:

    async def get_player_book_count(self, guild_id: int, player_id: int) -> ServiceResult[int]:
        service_result = ServiceResult[int]()

        try:
            cb_book = _service.clan_battle_boss_book_repo.get_player_book_count(guild_id=guild_id,
                                                                                     player_id=player_id)
            service_result.set_success(cb_book)
        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))

        return service_result

    async def get_player_book_entry(self, message_id: int, player_id: int) -> ServiceResult[ClanBattleBossBook]:
        service_result = ServiceResult[ClanBattleBossBook]()

        try:
            cb_book = _service.clan_battle_boss_book_repo.get_player_book_entry(message_id=message_id,
                                                                                     player_id=player_id)
            service_result.set_success(cb_book)

        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))

        return service_result

    @transactional
    async def delete_book_by_id(self, book_id: int) -> ServiceResult[None]:
        service_result = ServiceResult[None]()
        try:
            _service.clan_battle_boss_book_repo.delete_book_by_id(book_id)
            service_result.set_success(None)

        except Exception as e:
            transaction_rollback()
            log.error(e)
            service_result.set_error(str(e))

        return service_result

    @transactional
    async def update_damage_boss_book_by_id(self, book_id: int, damage_boss_book_id: int) -> ServiceResult[
        None]:
        service_result = ServiceResult[None]()
        try:
            _service.clan_battle_boss_book_repo.update_damage_boss_book_by_id(book_id, damage_boss_book_id)
            service_result.set_success(None)

        except Exception as e:
            transaction_rollback()
            log.error(e)
            service_result.set_error(str(e))

        return service_result


class ClanBattleOverallEntryService:

    async def get_player_overall_entry_count(self, guild_id: int, player_id: int) -> ServiceResult[int]:
        service_result = ServiceResult[int]()

        try:
            book_count = _service.clan_battle_overall_entry_repo.get_player_overall_entry_count(
                guild_id, player_id)
            service_result.set_success(book_count)
        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))

        return service_result

    async def get_leftover_by_guild_id_and_player_id(self, guild_id: int, player_id: int) -> ServiceResult[
        list[ClanBattleLeftover]]:
        service_result = ServiceResult[list[ClanBattleLeftover]]()

        try:
            leftover_list = _service.clan_battle_overall_entry_repo.get_leftover_by_guild_id_and_player_id(
                guild_id, player_id)
            service_result.set_success(leftover_list)
        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))

        return service_result


class ClanBattleBossEntryService:

    @transactional
    async def insert_clan_battle_boss_entry(self, clan_battle_boss_entry: ClanBattleBossEntry) -> \
            ServiceResult[ClanBattleBossEntry]:
        service_result = ServiceResult[ClanBattleBossEntry]()

        try:
            result = _service.clan_battle_boss_entry_repo.insert_clan_battle_boss_entry(clan_battle_boss_entry)
            service_result.set_success(result)
        except Exception as e:
            transaction_rollback()
            log.error(e)
            service_result.set_error(str(e))

        return service_result

    async def get_last_by_message_id(self, message_id: int) -> ServiceResult[ClanBattleBossEntry]:
        service_result = ServiceResult[ClanBattleBossEntry]()

        try:
            result = _service.clan_battle_boss_entry_repo.get_last_by_message_id(message_id)
            service_result.set_success(result)
        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))

        return service_result


class ClanBattleBossPeriodService:

    async def get_current_cb_period(self) -> ServiceResult[ClanBattlePeriod]:
        service_result = ServiceResult[ClanBattlePeriod]()

        try:
            result = _service.clan_battle_period_repo.get_current_cb_period()
            service_result.set_success(result)
        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))

        return service_result
