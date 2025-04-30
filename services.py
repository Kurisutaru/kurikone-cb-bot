import asyncio
import traceback
import uuid

import discord
from discord import Embed, Message, TextChannel, app_commands
from discord.abc import GuildChannel
from discord.ext.commands.bot import Bot

from globals import NEW_LINE
from locales import Locale
from logger import KuriLogger
from repository import *
from transactional import transactional, transaction_rollback
from utils import (
    discord_try_fetch_message,
    create_header_embed,
    create_done_embed,
    create_book_embed,
    reduce_int_ab_non_zero,
    send_channel_message,
    generate_random_boss_period,
    generate_current_cb_period,
    now,
    date_between,
)


class Services:
    def __init__(
        self,
        guild_repo: GuildRepository,
        channel_repo: ChannelRepository,
        clan_battle_boss_entry_repo: ClanBattleBossEntryRepository,
        clan_battle_boss_book_repo: ClanBattleBossBookRepository,
        clan_battle_period_repo: ClanBattlePeriodRepository,
        clan_battle_boss_repo: ClanBattleBossRepository,
        clan_battle_boss_health_repo: ClanBattleBossHealthRepository,
        clan_battle_overall_entry_repo: ClanBattleOverallEntryRepository,
        guild_player_repo: GuildPlayerRepository,
        clan_battle_report_message_repo: ClanBattleReportMessageRepository,
        error_log_repo: ErrorLogRepository,
    ):
        self.guild_repo = guild_repo
        self.channel_repo = channel_repo
        self.clan_battle_boss_entry_repo = clan_battle_boss_entry_repo
        self.clan_battle_boss_book_repo = clan_battle_boss_book_repo
        self.clan_battle_period_repo = clan_battle_period_repo
        self.clan_battle_boss_repo = clan_battle_boss_repo
        self.clan_battle_boss_health_repo = clan_battle_boss_health_repo
        self.clan_battle_overall_entry_repo = clan_battle_overall_entry_repo
        self.guild_player_repo = guild_player_repo
        self.clan_battle_report_message_repo = clan_battle_report_message_repo
        self.error_log_repo = error_log_repo

    @inject
    async def error_log_db(
        self,
        guild_id: int,
        exception: Exception,
        transaction_id: str,
        log: KuriLogger = Provide["logger"],
    ):
        """Logs errors to the database with a UUID reference.
        Guarantees the log is written even if the main transaction fails.
        """
        try:
            # Capture the traceback as a string (works even outside exception context)
            stacktrace = "".join(
                traceback.format_exception(
                    type(exception), exception, exception.__traceback__
                )
            ).rstrip()
            self.error_log_repo.insert(
                guild_id, transaction_id, str(exception), stacktrace
            )
            log.error(f"[{transaction_id}] Error: {exception}")
        except Exception as e:
            # Critical fallback: If DB logging fails, log to console + external service (e.g., Sentry)
            log.critical(
                f"FAILED to log error {transaction_id}. Falling back to console.",
                exc_info=e,
            )
            # Optionally, add a fallback mechanism (e.g., file log, Sentry, etc.)

        return True

    def gen_id(self) -> str:
        trx_id = str(uuid.uuid4())
        return trx_id


class MainService:
    @transactional
    @inject
    async def setup_guild_channel_message(
        self,
        guild: discord.Guild,
        tl_shifter_channel: dict,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[None]:

        service_result = ServiceResult[None]()
        guild_id = guild.id
        try:
            # Master CB Data
            clan_battle_period = (
                _service.clan_battle_period_repo.get_current_active_cb_period()
            )

            if clan_battle_period is None:
                log.error("Need Database setup !")
                return service_result.set_error("Need Database setup !")

            guild_db = await self.guild_setup(guild_id=guild_id, guild_name=guild.name)
            if not guild_db.is_success:
                raise Exception(guild_db.error_messages)

            channel_result = await self.setup_channel(guild)
            if not channel_result.is_success:
                raise Exception(channel_result.error_messages)

            for channel in channel_result.result:
                # Category doing nothing, pass
                if channel.channel_type == ChannelEnum.CATEGORY:
                    continue

                # For TL Shifting watcher
                if channel.channel_type == ChannelEnum.TL_SHIFTER and channel:
                    tl_shifter_channel[channel.channel_id] = None
                    continue

                discord_channel = guild.get_channel(channel.channel_id)
                # Report
                if channel.channel_type == ChannelEnum.REPORT and channel:
                    message = await self.setup_channel_report_message(discord_channel)
                    if not message.is_success:
                        raise Exception(message.error_messages)
                    continue

                # Boss Channel
                # Return if not enum named boss
                if "boss" in channel.channel_type.name.lower():
                    message = await self.setup_channel_boss_message(
                        channel, discord_channel
                    )
                    if not message.is_success:
                        raise Exception(message.error_messages)

            service_result.set_success(None)

        except Exception as e:
            log.error(e)
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    # Guild Setup
    @inject
    async def guild_setup(
        self,
        guild_id: int,
        guild_name: str,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
    ) -> ServiceResult[Guild]:
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
            log.error(e)
            raise e

        return service_result

    # Channel Setup
    @inject
    async def setup_channel(
        self,
        guild: discord.Guild,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
    ) -> ServiceResult[list[Channel]]:
        service_result = ServiceResult[list[Channel]]()
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=True, send_messages=False
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_messages=True
                ),
            }

            overwrites_tl_shifter = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
                ),
            }

            guild_channel = _service.channel_repo.get_all_by_guild_id(guild.id)
            processed_channel = []
            category_channel = None

            for enum in ChannelEnum:
                channel_data = next(
                    (
                        channel
                        for channel in guild_channel
                        if channel.channel_type == enum
                    ),
                    None,
                )
                # Assume no Channel Exist for specific enum
                if channel_data is None:
                    local_overwrites = overwrites
                    if enum == ChannelEnum.TL_SHIFTER:
                        local_overwrites = overwrites_tl_shifter

                    if enum == ChannelEnum.CATEGORY:
                        channel = await guild.create_category(
                            name=ChannelEnum.CATEGORY.value["name"],
                            overwrites=overwrites,
                        )
                        category_channel = channel
                    else:
                        channel = await guild.create_text_channel(
                            name=enum.value["name"],
                            category=category_channel,
                            overwrites=local_overwrites,
                        )

                    channel_data = _service.channel_repo.insert_channel(
                        Channel(channel.id, guild.id, enum)
                    )
                    processed_channel.append(channel_data)
                else:
                    processed_channel.append(channel_data)

            service_result.set_success(processed_channel)

        except Exception as e:
            log.error(e)
            raise e

        return service_result

    # Channel Report to Message Setup
    @inject
    async def setup_channel_report_message(
        self,
        channel: GuildChannel,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
    ) -> ServiceResult[Optional[Message]]:
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
            raise e

        return service_result

    # Channel Boss to Message Setup
    @inject
    async def setup_channel_boss_message(
        self,
        channel: Channel,
        discord_channel: GuildChannel,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[Optional[Message]]:
        service_result = ServiceResult[Optional[Message]]()
        try:
            if not isinstance(discord_channel, TextChannel):
                return service_result

            guild_id = discord_channel.guild.id

            if channel.message_id is None:
                message = await discord_channel.send(
                    content=l.t(guild_id, "ui.status.preparing_data")
                )
                channel.message_id = message.id
                _service.channel_repo.update_channel(channel)
            else:
                message = await discord_try_fetch_message(
                    discord_channel, channel.message_id
                )

            period = _service.clan_battle_period_repo.get_current_active_cb_period_day()
            boss_id = getattr(
                period, f"{channel.channel_type.value['type'].lower()}_id"
            )

            cb_entry = _service.clan_battle_boss_entry_repo.get_boss_entry_by_param(
                guild_id, period.clan_battle_period_id, boss_id
            )

            # Edit previous message to remove button and make embed dark
            if message and cb_entry is None and period.current_day == 1:
                # Edit old
                for embed in message.embeds:
                    embed.colour = discord.Colour.dark_grey()
                await message.edit(view=None, embeds=message.embeds)
                # Create new one
                message = await discord_channel.send(
                    content=l.t(guild_id, "ui.status.preparing_data")
                )
                channel.message_id = message.id
                _service.channel_repo.update_channel(channel)

            # Main logic flow
            if cb_entry is None:
                # Case when message exists but no entry exists
                await self.insert_clan_battle_entry_by_round(
                    guild_id=guild_id,
                    boss_id=boss_id,
                    period_id=period.clan_battle_period_id,
                    boss_round=1,
                )

            # Refresh the bosses
            embeds = await self.refresh_clan_battle_boss_embeds(guild_id, boss_id)
            if embeds.is_success:
                import ui

                await message.edit(
                    content="", embeds=embeds.result, view=ui.ButtonView(guild_id)
                )

            service_result.set_success(message)

        except Exception as e:
            log.error(e)
            raise e

        return service_result

    @inject
    async def insert_clan_battle_entry_by_round(
        self,
        guild_id: int,
        boss_id: int,
        period_id: int,
        boss_round: int,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
    ) -> ServiceResult[ClanBattleBossEntry]:
        service_result = ServiceResult[ClanBattleBossEntry]()

        try:
            cb_boss = _service.clan_battle_boss_repo.fetch_clan_battle_boss_by_id(
                boss_id
            )
            cb_boss_health = (
                _service.clan_battle_boss_health_repo.get_one_by_position_and_round(
                    position=cb_boss.position, boss_round=boss_round
                )
            )

            if cb_boss is None:
                service_result.set_error(f"Boss is None")
                return service_result

            if cb_boss_health is None:
                service_result.set_error(f"Boss health is None")
                return service_result

            cb_entry = ClanBattleBossEntry(
                guild_id=guild_id,
                clan_battle_period_id=period_id,
                clan_battle_boss_id=cb_boss.clan_battle_boss_id,
                boss_round=1,
                current_health=cb_boss_health.health,
                is_active=True,
            )

            cb_entry = (
                _service.clan_battle_boss_entry_repo.insert_clan_battle_boss_entry(
                    cb_entry
                )
            )
            service_result.set_success(cb_entry)

        except Exception as e:
            log.error(e)
            transaction_rollback()
            service_result.set_error(str(e))

        return service_result

    @transactional
    @inject
    async def refresh_clan_battle_boss_embeds(
        self,
        guild_id: int,
        boss_id: int,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
    ) -> ServiceResult[list[Embed]]:
        service_result = ServiceResult[list[Embed]]()
        try:
            embeds = []
            guild_id = guild_id

            active_period = (
                _service.clan_battle_period_repo.get_current_active_cb_period()
            )

            # Header
            entry = _service.clan_battle_boss_entry_repo.get_boss_entry_by_param(
                guild_id, active_period.clan_battle_period_id, boss_id
            )

            embeds.append(create_header_embed(guild_id, entry))

            # Entry
            cb_overall_repository = ClanBattleOverallEntryRepository()
            done_entries = cb_overall_repository.get_all_by_boss_entry_id(
                guild_id, entry.clan_battle_boss_entry_id
            )

            if len(done_entries) > 0:
                embeds.append(create_done_embed(guild_id, done_entries))

            # Book
            book_entries = _service.clan_battle_boss_book_repo.get_all_by_entry_id(
                guild_id, entry.clan_battle_boss_entry_id
            )

            if len(book_entries) > 0:
                embeds.append(create_book_embed(guild_id, book_entries))

            service_result.set_success(embeds)

        except Exception as e:
            log.error(e)
            service_result.set_error(str(e))

        return service_result

    @transactional
    @inject
    async def done_entry(
        self,
        interaction: discord.Interaction,
        service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[list[Embed]]:
        service_result = ServiceResult[list[Embed]]()

        try:
            boss_entry = service.clan_battle_boss_entry_repo.get_boss_entry_active_cb_by_channel_id(
                interaction.channel.id
            )

            book_result = (
                service.clan_battle_boss_book_repo.get_player_book_by_entry_id(
                    boss_entry.clan_battle_boss_entry_id,
                    interaction.user.id,
                )
            )

            period = service.clan_battle_period_repo.get_current_active_cb_period_day()

            service.clan_battle_boss_book_repo.delete_book_by_id(
                book_result.clan_battle_boss_book_id
            )

            # Prepare insert into overall Entry
            cb_overall_repository = ClanBattleOverallEntryRepository()
            overall = cb_overall_repository.insert(
                cb_overall_entry=ClanBattleOverallEntry(
                    guild_id=interaction.guild_id,
                    clan_battle_boss_entry_id=boss_entry.clan_battle_boss_entry_id,
                    clan_battle_period_id=period.clan_battle_period_id,
                    clan_battle_boss_id=boss_entry.clan_battle_boss_id,
                    player_id=interaction.user.id,
                    player_name=interaction.user.display_name,
                    boss_round=boss_entry.boss_round,
                    day=period.current_day,
                    attack_type=book_result.attack_type,
                    damage=book_result.damage,
                )
            )

            if not book_result.clan_battle_overall_entry_id is None:
                service.clan_battle_overall_entry_repo.update_overall_link(
                    cb_overall_entry_id=book_result.clan_battle_overall_entry_id,
                    overall_leftover_entry_id=overall.clan_battle_overall_entry_id,
                )

            # Update Boss Entry
            service.clan_battle_boss_entry_repo.update_on_attack(
                clan_battle_boss_entry_id=boss_entry.clan_battle_boss_entry_id,
                current_health=reduce_int_ab_non_zero(
                    boss_entry.current_health, book_result.damage
                ),
            )

            embeds = await self.refresh_clan_battle_boss_embeds(
                interaction.guild_id, boss_entry.clan_battle_boss_id
            )

            service_result.set_success(embeds.result)
        except Exception as e:
            log.error(e)
            transaction_rollback()
            trx_id = service.gen_id()
            asyncio.create_task(service.error_log_db(interaction.guild_id, e, trx_id))
            service_result.set_error(
                l.t(interaction.guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @transactional
    @inject
    async def dead_ok(
        self,
        interaction: discord.Interaction,
        leftover_time: int,
        service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[ClanBattleOverallEntry]:
        service_result = ServiceResult[ClanBattleOverallEntry]()
        guild_id = interaction.guild_id
        try:
            boss_entry = service.clan_battle_boss_entry_repo.get_boss_entry_active_cb_by_channel_id(
                interaction.channel.id
            )

            book_result = (
                service.clan_battle_boss_book_repo.get_player_book_by_entry_id(
                    boss_entry.clan_battle_boss_entry_id,
                    interaction.user.id,
                )
            )

            period = service.clan_battle_period_repo.get_current_active_cb_period_day()

            # Delete all book by boss entry (Including whom deaded the bosses)
            service.clan_battle_boss_book_repo.delete_book_by_entry_id(
                boss_entry.clan_battle_boss_entry_id
            )

            # Prepare insert into overall Entry
            overall = service.clan_battle_overall_entry_repo.insert(
                cb_overall_entry=ClanBattleOverallEntry(
                    guild_id=guild_id,
                    clan_battle_boss_entry_id=boss_entry.clan_battle_boss_entry_id,
                    clan_battle_period_id=period.clan_battle_period_id,
                    clan_battle_boss_id=boss_entry.clan_battle_boss_id,
                    player_id=interaction.user.id,
                    player_name=interaction.user.display_name,
                    boss_round=boss_entry.boss_round,
                    day=period.current_day,
                    attack_type=book_result.attack_type,
                    damage=book_result.damage,
                    leftover_time=(
                        None
                        if book_result.attack_type == AttackTypeEnum.CARRY
                        else leftover_time
                    ),
                )
            )

            # Update Boss Entry
            service.clan_battle_boss_entry_repo.update_on_attack(
                clan_battle_boss_entry_id=boss_entry.clan_battle_boss_entry_id,
                current_health=reduce_int_ab_non_zero(
                    boss_entry.current_health, book_result.damage
                ),
            )

            if not book_result.clan_battle_overall_entry_id is None:
                service.clan_battle_overall_entry_repo.update_overall_link(
                    cb_overall_entry_id=book_result.clan_battle_overall_entry_id,
                    overall_leftover_entry_id=overall.clan_battle_overall_entry_id,
                )

            await self.generate_next_boss(
                interaction,
                book_result.attack_type,
                leftover_time,
            )

            service_result.set_success(overall)

        except Exception as e:
            log.error(e)
            transaction_rollback()
            trx_id = service.gen_id()
            asyncio.create_task(service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @inject
    async def generate_next_boss(
        self,
        interaction: discord.Interaction,
        attack_type: AttackTypeEnum,
        leftover_time: int,
        service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[ClanBattleBossEntry]:
        service_result = ServiceResult[ClanBattleBossEntry]()

        try:
            guild_id = interaction.guild_id
            channel_id = interaction.channel.id

            boss_entry = service.clan_battle_boss_entry_repo.get_boss_entry_active_cb_by_channel_id(
                interaction.channel.id
            )

            period = service.clan_battle_period_repo.get_current_active_cb_period_day()

            # Edit Old one

            done_entries = (
                service.clan_battle_overall_entry_repo.get_all_by_param_and_round(
                    guild_id,
                    period.clan_battle_period_id,
                    boss_entry.clan_battle_boss_id,
                    boss_entry.boss_round,
                )
            )

            await interaction.message.edit(
                content="",
                embeds=[
                    create_header_embed(
                        guild_id=guild_id,
                        cb_boss_entry=boss_entry,
                        include_image=False,
                        default_color=discord.Color.dark_grey(),
                    ),
                    create_done_embed(
                        guild_id=guild_id,
                        list_cb_overall_entry=done_entries,
                        default_color=discord.Color.dark_grey(),
                    ),
                ],
                view=None,
            )

            # Generate New One
            await send_channel_message(
                interaction=interaction,
                content=f"{l.t(guild_id, "ui.events.boss_killed", user=interaction.user.display_name, attack_type=attack_type.value, leftover_time=leftover_time)}",
            )

            next_round = boss_entry.boss_round + 1

            boss = service.clan_battle_boss_repo.fetch_clan_battle_boss_by_id_and_round(
                boss_entry.clan_battle_boss_id, next_round
            )

            new_message = await interaction.channel.send(
                content=l.t(guild_id, "ui.status.preparing_data")
            )

            service.channel_repo.update_channel_message(channel_id, new_message.id)

            # Inactive old one
            service.clan_battle_boss_entry_repo.set_active_by_id(
                boss_entry.clan_battle_boss_entry_id, False
            )

            boss_entry = (
                service.clan_battle_boss_entry_repo.get_boss_entry_by_param_round(
                    interaction.guild_id,
                    period.clan_battle_period_id,
                    boss_entry.clan_battle_boss_id,
                    next_round,
                )
            )
            if boss_entry is None:
                boss_entry = ClanBattleBossEntry(
                    guild_id=guild_id,
                    clan_battle_period_id=period.clan_battle_period_id,
                    clan_battle_boss_id=boss.clan_battle_boss_id,
                    boss_round=next_round,
                    current_health=boss.health,
                    is_active=True,
                )

                service.clan_battle_boss_entry_repo.insert_clan_battle_boss_entry(
                    boss_entry
                )
            else:
                service.clan_battle_boss_entry_repo.set_active_by_id(
                    boss_entry.clan_battle_boss_entry_id, True
                )

            from ui import ButtonView

            embeds = await self.refresh_clan_battle_boss_embeds(
                interaction.guild_id, boss_entry.clan_battle_boss_id
            )
            await new_message.edit(
                content="", embeds=embeds.result, view=ButtonView(guild_id)
            )

            service_result.set_success(boss_entry)
        except Exception as e:
            log.error(e)
            transaction_rollback()
            service_result.set_error(str(e))
            print(e)

        return service_result

    @transactional
    @inject
    async def install_bot_command(
        self,
        guild: discord.Guild,
        tl_shifter_channel: dict,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[None]:
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
            log.error(e)
            transaction_rollback()
            service_result.set_error(str(e))

        return service_result

    @transactional
    @inject
    async def uninstall_bot_command(
        self,
        guild: discord.Guild,
        tl_shifter_channel: dict,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[list[int]]:
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
            log.error(e)
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @transactional
    @inject
    async def sync_user_role(
        self,
        guild_id: int,
        members: list[GuildPlayer],
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[None]:
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
            log.error(e)
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @inject
    async def generate_report_text(
        self,
        guild_id: int,
        year: int,
        month: int,
        day: int,
        period_id: int = None,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[str]:
        service_result = ServiceResult[str]()

        try:
            if period_id is None:
                header = _service.clan_battle_period_repo.get_by_param(year, month)
                entries = (
                    _service.clan_battle_overall_entry_repo.get_report_entry_by_param(
                        guild_id, year, month, day
                    )
                )
            else:
                header = _service.clan_battle_period_repo.get_by_id_day(period_id)
                entries = _service.clan_battle_overall_entry_repo.get_report_entry_by_guild_and_period_id(
                    guild_id, period_id, day
                )

            result = f"# {header.clan_battle_period_name} - {l.t(guild_id, "ui.status.day", day=day)}{NEW_LINE}"

            sum_patk_count = (
                sum(entry.patk_count for entry in entries) if entries else 0
            )
            sum_matk_count = (
                sum(entry.matk_count for entry in entries) if entries else 0
            )
            sum_leftover_count = (
                sum(entry.leftover_count for entry in entries) if entries else 0
            )
            sum_carry_count = (
                sum(entry.carry_count for entry in entries) if entries else 0
            )

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
    @inject
    async def refresh_report_channel_message(
        self,
        guild: discord.Guild,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[Optional[Message]]:
        service_result = ServiceResult[Optional[Message]]()
        guild_id = guild.id
        # Current date info
        current_date = now()
        try:
            # Get current CB period once
            cur_period = (
                _service.clan_battle_period_repo.get_current_active_cb_period_day()
            )
            if cur_period.current_day == -1:
                service_result.set_error("No Running Clan Battle period detected")
                return service_result

            # Get channel data once
            channel_data = _service.channel_repo.get_by_guild_id_and_type(
                guild_id, ChannelEnum.REPORT.name
            )
            if channel_data is None:
                service_result.set_error("No Report channel found")
                return service_result

            channel = guild.get_channel(channel_data.channel_id)
            if channel is None:
                service_result.set_error("Report channel not found in guild")
                return service_result

            if channel_data.message_id is None:
                message = await channel.send(
                    content=l.t(guild_id, "ui.status.preparing_data")
                )
                channel_data.message_id = message.id
                _service.channel_repo.update_channel(channel_data)
            else:
                message = await discord_try_fetch_message(
                    channel, channel_data.message_id
                )

            # Get latest CB report message from DB
            cb_report_message_data = (
                _service.clan_battle_report_message_repo.get_last_by_guild_period(
                    guild_id, cur_period.clan_battle_period_id, cur_period.current_day
                )
            )

            # If no existing report message, create one with current day
            if cb_report_message_data is None:
                # Alter here if message exist but report data is new,
                # so it don't replace old one, but create new one if Period LIVE
                if cur_period.period_type == PeriodType.LIVE or (
                    cur_period.period_type == PeriodType.OFFSEASON
                    and cur_period.current_day == 1
                ):
                    if message.content != l.t(guild_id, "ui.status.preparing_data"):
                        message = await channel.send(content="ui.status.preparing_data")
                        channel_data.message_id = message.id
                        _service.channel_repo.update_channel(channel_data)

                cb_report_message_data = ClanBattleReportMessage(
                    guild_id=guild_id,
                    clan_battle_period_id=cur_period.clan_battle_period_id,
                    day=cur_period.current_day,
                    message_id=message.id,
                )
                _service.clan_battle_report_message_repo.insert(cb_report_message_data)

            # Always update the existing message first
            report_gen = await self.generate_report_text(
                guild_id,
                current_date.year,
                current_date.month,
                cb_report_message_data.day,
                cur_period.clan_battle_period_id,
            )

            if not report_gen.is_success:
                service_result.set_error(report_gen.error_messages)
                return service_result

            embed = Embed(description=report_gen.result, color=discord.Colour.blurple())
            await message.edit(content="", embed=embed)

            # Then check if we need a new message for new day
            if cur_period.current_day > cb_report_message_data.day:
                new_report_message = await channel.send(
                    content=l.t(guild_id, "ui.status.preparing_data")
                )
                channel_data.message_id = new_report_message.id
                _service.channel_repo.update_channel(channel_data)

                new_cb_report_message_data = ClanBattleReportMessage(
                    guild_id=guild_id,
                    clan_battle_period_id=cur_period.clan_battle_period_id,
                    day=cur_period.current_day,
                    message_id=new_report_message.id,
                )
                _service.clan_battle_report_message_repo.insert(
                    new_cb_report_message_data
                )

                # Generate report for new day
                new_report_gen = await self.generate_report_text(
                    guild_id,
                    current_date.year,
                    current_date.month,
                    cur_period.current_day,
                    cur_period.clan_battle_period_id,
                )

                if not new_report_gen.is_success:
                    service_result.set_error(new_report_gen.error_messages)
                    return service_result

                new_embed = Embed(
                    description=new_report_gen.result, color=discord.Colour.blurple()
                )
                await new_report_message.edit(content="", embed=new_embed)
                service_result.set_success(new_report_message)
                return service_result

            service_result.set_success(message)
        except Exception as e:
            log.error(e)
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @transactional
    @inject
    async def check_clan_battle_period(
        self,
        log: KuriLogger = Provide["logger"],
        _service: Services = Provide["services"],
    ) -> ServiceResult[bool]:
        service_result = ServiceResult[bool]()
        try:
            # Get CB period mark as active
            active_period = (
                _service.clan_battle_period_repo.get_current_active_cb_period()
            )
            # Get current CB period (should be)
            current_period = _service.clan_battle_period_repo.get_latest_cb_period()

            # Check if all exist and same period then nothing to do
            if (
                active_period
                and current_period
                and active_period.clan_battle_period_id
                == current_period.clan_battle_period_id
            ):
                service_result.set_success(False)
                return service_result

            # If active period is existed copy the mobs only like aoi
            # If not, randomize the boss
            # Also just prepare, don't make it active, let the 5AM Cron task do the job to switch the period
            if current_period is None:
                if active_period is None:
                    bosses = _service.clan_battle_boss_repo.get_all()
                    rand_boss = generate_random_boss_period(bosses)
                    current_period = generate_current_cb_period()
                    # Append the generated random boss
                    current_period.merge_bosses(rand_boss)
                else:
                    current_period = generate_current_cb_period()
                    current_period.merge_bosses(active_period)

                # Set all other period not active
                _service.clan_battle_period_repo.set_period_all_inactive()
                _service.clan_battle_period_repo.insert(current_period)
            # If there's created period, set other inactive, set current into active
            else:
                # Set all other period not active
                _service.clan_battle_period_repo.set_period_all_inactive()
                _service.clan_battle_period_repo.set_active_by_id(
                    current_period.clan_battle_period_id
                )

            # Invalid all Boss Entries
            _service.clan_battle_boss_entry_repo.set_boss_entry_all_inactive()

            service_result.set_success(True)
        except Exception as e:
            log.error(e)
            transaction_rollback()

        return service_result

    @inject
    async def check_command_tree_sync(
        self,
        bot: Bot,  # Type hint for discord.ext.commands.bot.Bot
        guild_id: Optional[int] = None,
        log: KuriLogger = Provide["logger"],
    ):
        """
        Compare local and Discord command trees by name and description, syncing if they differ.

        Args:
            bot: The bot instance.
            guild_id: Optional guild ID for guild-specific commands.
            log: Logger instance for output.
        """
        tree = bot.tree
        guild_obj = discord.utils.get(bot.guilds, id=guild_id)
        if guild_id and not guild_obj:
            log.error(f"Guild {guild_id} not found.")
            return

        # Define location for logging (accessible to both if and else)
        location = f"Guild {guild_obj.id} - {guild_obj.name}" if guild_obj else "Global"

        # Fetch remote (Discord) commands
        try:
            remote_commands = await tree.fetch_commands(guild=guild_obj)
        except discord.HTTPException as e:
            log.error(f"Failed to fetch commands: {e}")
            return

        # Get local commands (match guild scope)
        local_commands = tree.get_commands(guild=guild_obj)

        # Serialize commands (name and description only)
        def serialize_command(cmd: any) -> dict:
            if isinstance(cmd, app_commands.ContextMenu):
                return {
                    "name": cmd.name,
                    "description": "",
                    "type": "context_menu",
                }
            # Local AppCommand or Command, or remote AppCommand
            cmd_type = (
                "slash"
                if isinstance(cmd, (app_commands.AppCommand, app_commands.Command))
                else (
                    "context_menu"
                    if isinstance(cmd, app_commands.AppCommand)
                    and cmd.type.value in (2, 3)
                    else "slash"
                )
            )
            return {
                "name": cmd.name,
                "description": getattr(cmd, "description", "") or "",
                "type": cmd_type,
            }

        # Sort serialized commands by name for consistent comparison
        remote_serialized = sorted(
            [serialize_command(cmd) for cmd in remote_commands], key=lambda x: x["name"]
        )
        local_serialized = sorted(
            [serialize_command(cmd) for cmd in local_commands], key=lambda x: x["name"]
        )

        # Compare and sync if needed
        if remote_serialized != local_serialized:
            log.info(f"🔁 Command tree out of sync ({location}). Syncing...")
            try:
                await tree.sync(guild=guild_obj)
                log.info(f"✅ Command tree synced ({location}).")
            except discord.HTTPException as e:
                log.error(f"Failed to sync command tree: {e}")
        else:
            log.info(f"✅ Command tree in sync ({location}).")


class UiService:

    @inject
    async def book_button_service(
        self,
        interaction: discord.Interaction,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[Tuple[bool, int, list[ClanBattleLeftover]]]:
        service_result = ServiceResult[Tuple[bool, int, list[ClanBattleLeftover]]]()
        guild_id = interaction.guild_id
        try:
            user_id = interaction.user.id

            # Check if ended
            boss_entry = _service.clan_battle_period_repo.get_current_active_cb_period()
            if not date_between(now(), boss_entry.date_from, boss_entry.date_to):
                service_result.set_error(l.t(guild_id, "ui.status.clan_battle_ended"))
                return service_result

            boss_book = _service.clan_battle_boss_book_repo.get_player_book_count(
                guild_id, user_id
            )
            if boss_book > 0:
                service_result.set_error(l.t(guild_id, "ui.status.booked"))
                return service_result

            entry_count = (
                _service.clan_battle_overall_entry_repo.get_player_overall_entry_count(
                    guild_id, user_id
                )
            )

            count = entry_count

            disable = count == 3

            # generate Leftover ?
            leftover = _service.clan_battle_overall_entry_repo.get_leftover_by_guild_id_and_player_id(
                guild_id=guild_id, player_id=user_id
            )

            service_result.set_success(
                (disable, reduce_int_ab_non_zero(a=3, b=count), leftover)
            )

        except Exception as e:
            log.error(e)
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @transactional
    @inject
    async def cancel_button_service(
        self,
        interaction: discord.Interaction,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[list[Embed]]:
        service_result = ServiceResult[list[Embed]]()
        guild_id = interaction.guild_id
        try:
            user_id = interaction.user.id

            # Check if ended
            boss_entry = _service.clan_battle_period_repo.get_current_active_cb_period()
            if not date_between(now(), boss_entry.date_from, boss_entry.date_to):
                service_result.set_error(l.t(guild_id, "ui.status.clan_battle_ended"))
                return service_result

            entry = _service.clan_battle_boss_entry_repo.get_boss_entry_active_cb_by_channel_id(
                interaction.channel.id
            )

            book_result = (
                _service.clan_battle_boss_book_repo.get_player_book_by_entry_id(
                    entry.clan_battle_boss_entry_id,
                    user_id,
                )
            )

            if book_result is None:
                service_result.set_error(
                    l.t(guild_id, "ui.validation.book_entry_not_found")
                )
                return service_result

            _service.clan_battle_boss_book_repo.delete_book_by_id(
                book_result.clan_battle_boss_book_id
            )
            embeds = await MainService().refresh_clan_battle_boss_embeds(
                guild_id, entry.clan_battle_boss_id
            )

            service_result.set_success(embeds.result)

        except Exception as e:
            log.error(e)
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @inject
    async def entry_button_service(
        self,
        interaction: discord.Interaction,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[None]:
        service_result = ServiceResult[None]()
        guild_id = interaction.guild_id
        try:
            # Check if ended
            boss_entry = _service.clan_battle_period_repo.get_current_active_cb_period()
            if not date_between(now(), boss_entry.date_from, boss_entry.date_to):
                service_result.set_error(l.t(guild_id, "ui.status.clan_battle_ended"))
                return service_result

            entry = _service.clan_battle_boss_entry_repo.get_boss_entry_active_cb_by_channel_id(
                interaction.channel.id
            )

            book_result = (
                _service.clan_battle_boss_book_repo.get_player_book_by_entry_id(
                    entry.clan_battle_boss_entry_id,
                    interaction.user.id,
                )
            )
            if book_result is None:
                service_result.set_error(
                    f"## {l.t(interaction.guild_id, "ui.status.not_yet_booked")}"
                )
                return service_result

            service_result.set_success(None)
        except Exception as e:
            log.error(e)
            transaction_rollback()
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @transactional
    @inject
    async def entry_input_service(
        self,
        interaction: discord.Interaction,
        user_input: str,
        service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[list[Embed]]:
        service_result = ServiceResult[list[Embed]]()
        guild_id = interaction.guild_id
        try:
            # Check if ended
            boss_entry = service.clan_battle_period_repo.get_current_active_cb_period()
            if not date_between(now(), boss_entry.date_from, boss_entry.date_to):
                service_result.set_error(l.t(guild_id, "ui.status.clan_battle_ended"))
                return service_result

            if not user_input.isdigit():
                service_result.set_error(
                    f"## {l.t(guild_id, "ui.validation.only_numbers_allowed")}"
                )
                return service_result

            damage = int(user_input)

            if damage < 1:
                service_result.set_error(
                    f"## {l.t(guild_id, "ui.validation.must_be_greater_than_zero")}"
                )
                return service_result

            entry = service.clan_battle_boss_entry_repo.get_boss_entry_active_cb_by_channel_id(
                interaction.channel.id
            )

            book_result = (
                service.clan_battle_boss_book_repo.get_player_book_by_entry_id(
                    entry.clan_battle_boss_entry_id,
                    interaction.user.id,
                )
            )

            if book_result is None:
                raise l.t(guild_id, "ui.validation.book_entry_not_found")

            service.clan_battle_boss_book_repo.update_damage_boss_book_by_id(
                book_result.clan_battle_boss_book_id, damage
            )

            embeds = await MainService().refresh_clan_battle_boss_embeds(
                guild_id, entry.clan_battle_boss_id
            )
            service_result.set_success(embeds.result)

        except Exception as e:
            log.error(e)
            transaction_rollback()
            trx_id = service.gen_id()
            asyncio.create_task(service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @inject
    async def done_button_service(
        self,
        interaction: discord.Interaction,
        _service: Services = Provide["services"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[None]:
        service_result = ServiceResult[None]()
        guild_id = interaction.guild_id
        try:
            # Check if ended
            boss_entry = _service.clan_battle_period_repo.get_current_active_cb_period()
            if not date_between(now(), boss_entry.date_from, boss_entry.date_to):
                service_result.set_error(l.t(guild_id, "ui.status.clan_battle_ended"))
                return service_result

            entry = _service.clan_battle_boss_entry_repo.get_boss_entry_active_cb_by_channel_id(
                interaction.channel.id
            )

            book_result = (
                _service.clan_battle_boss_book_repo.get_player_book_by_entry_id(
                    entry.clan_battle_boss_entry_id,
                    interaction.user.id,
                )
            )

            if book_result is None:
                service_result.set_error(
                    f"## {l.t(guild_id, "ui.status.not_yet_booked")}"
                )
                return service_result

            if book_result.damage is None:
                service_result.set_error(
                    f"## {l.t(guild_id, "ui.validation.enter_entry_type_first")}"
                )
                return service_result

            service_result.set_success(None)
        except Exception as e:
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @inject
    async def dead_button_service(
        self,
        interaction: discord.Interaction,
        _service: Services = Provide["services"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[ClanBattleBossBook]:
        service_result = ServiceResult[ClanBattleBossBook]()
        guild_id = interaction.guild_id
        try:
            # Check if ended
            boss_entry = _service.clan_battle_period_repo.get_current_active_cb_period()
            if not date_between(now(), boss_entry.date_from, boss_entry.date_to):
                service_result.set_error(l.t(guild_id, "ui.status.clan_battle_ended"))
                return service_result

            entry = _service.clan_battle_boss_entry_repo.get_boss_entry_active_cb_by_channel_id(
                interaction.channel.id
            )

            book_result = (
                _service.clan_battle_boss_book_repo.get_player_book_by_entry_id(
                    entry.clan_battle_boss_entry_id,
                    interaction.user.id,
                )
            )

            if book_result is None:
                service_result.set_error(
                    f"## {l.t(guild_id, "ui.status.not_yet_booked")}"
                )
                return service_result

            if book_result.damage is None:
                service_result.set_error(
                    f"## {l.t(guild_id, "ui.validation.enter_entry_type_first")}"
                )
                return service_result

            boss_entry = _service.clan_battle_boss_entry_repo.get_boss_entry_active_cb_by_channel_id(
                interaction.channel.id
            )
            if book_result.damage < boss_entry.current_health:
                service_result.set_error(
                    f"## {l.t(guild_id, "ui.validation.entry_damage_less_than_boss_hp")}"
                )
                return service_result

            service_result.set_success(book_result)
        except Exception as e:
            trx_id = _service.gen_id()
            asyncio.create_task(_service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @transactional
    @inject
    async def insert_boss_book_entry(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        display_name: str,
        attack_type: AttackTypeEnum,
        parent_overall_id: int = None,
        leftover_time: int = None,
        main_service: MainService = Provide["main_service"],
        service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
        l: Locale = Provide["locale"],
    ) -> ServiceResult[list[Embed]]:
        service_result = ServiceResult[list[Embed]]()
        try:
            channel = service.channel_repo.get_by_channel_id_with_boss(channel_id)

            boss_entry = (
                service.clan_battle_boss_entry_repo.get_boss_entry_active_cb_by_param(
                    guild_id, channel.boss_id
                )
            )

            service.clan_battle_boss_book_repo.insert_boss_book_entry(
                ClanBattleBossBook(
                    clan_battle_boss_entry_id=boss_entry.clan_battle_boss_entry_id,
                    guild_id=guild_id,
                    player_id=user_id,
                    player_name=display_name,
                    attack_type=attack_type,
                    clan_battle_overall_entry_id=parent_overall_id,
                    leftover_time=leftover_time,
                )
            )

            embeds = await main_service.refresh_clan_battle_boss_embeds(
                guild_id, boss_entry.clan_battle_boss_id
            )

            service_result.set_success(embeds.result)

        except Exception as e:
            log.error(e)
            transaction_rollback()
            trx_id = service.gen_id()
            asyncio.create_task(service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result

    @transactional
    @inject
    async def rotate_round(
        self,
        interaction: discord.Interaction,
        boss_round: int,
        main_service: MainService = Provide["main_service"],
        service: Services = Provide["services"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ) -> ServiceResult[list[Embed]]:
        service_result = ServiceResult[list[Embed]]()
        guild_id = interaction.guild.id
        try:
            boss_entry = service.clan_battle_boss_entry_repo.get_boss_entry_active_cb_by_channel_id(
                interaction.channel.id
            )

            round_entry = (
                service.clan_battle_boss_entry_repo.get_boss_entry_by_param_round(
                    interaction.guild_id,
                    boss_entry.clan_battle_period_id,
                    boss_entry.clan_battle_boss_id,
                    boss_round,
                )
            )

            service.clan_battle_boss_entry_repo.set_active_by_id(
                boss_entry.clan_battle_boss_entry_id, False
            )

            if round_entry is None:
                boss_db = service.clan_battle_boss_repo.fetch_clan_battle_boss_by_id_and_round(
                    boss_entry.clan_battle_boss_id, boss_round
                )

                round_entry = (
                    service.clan_battle_boss_entry_repo.insert_clan_battle_boss_entry(
                        ClanBattleBossEntry(
                            guild_id=boss_entry.guild_id,
                            clan_battle_period_id=boss_entry.clan_battle_period_id,
                            clan_battle_boss_id=boss_entry.clan_battle_boss_id,
                            boss_round=boss_round,
                            current_health=boss_db.health,
                            is_active=True,
                        )
                    )
                )
            else:
                service.clan_battle_boss_entry_repo.set_active_by_id(
                    round_entry.clan_battle_boss_entry_id, True
                )

            embeds = await main_service.refresh_clan_battle_boss_embeds(
                interaction.guild_id, round_entry.clan_battle_boss_id
            )

            service_result.set_success(embeds.result)

        except Exception as e:
            log.error(e)
            transaction_rollback()
            trx_id = service.gen_id()
            asyncio.create_task(service.error_log_db(guild_id, e, trx_id))
            service_result.set_error(
                l.t(guild_id, "message.unhandled_exception", uuid=trx_id)
            )

        return service_result


class GuildService:

    @inject
    async def get_guild_by_id(
        self, guild_id: int, _service: Services = Provide["services"]
    ) -> ServiceResult[Guild]:
        service_result = ServiceResult[Guild]()

        try:
            data = _service.guild_repo.get_by_guild_id(guild_id)
            service_result.set_success(data)

        except Exception as e:
            service_result.set_error(str(e))

        return service_result

    @transactional
    @inject
    async def insert_guild(
        self,
        guild_id: int,
        guild_name: str,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
    ) -> ServiceResult[Guild]:
        service_result = ServiceResult[Guild]()

        try:
            guild = Guild(guild_id=guild_id, guild_name=guild_name)
            data = _service.guild_repo.insert_guild(guild)
            service_result.set_success(data)

        except Exception as e:
            log.error(e)
            transaction_rollback()
            service_result.set_error(str(e))
            print(e)

        return service_result


class ChannelService:

    @inject
    async def get_all_by_guild_id(
        self, guild_id: int, _service: Services = Provide["services"]
    ) -> ServiceResult[list[Channel]]:
        service_result = ServiceResult[list[Channel]]()

        try:
            data = _service.channel_repo.get_all_by_guild_id(guild_id)
            service_result.set_success(data)

        except Exception as e:
            service_result.set_error(str(e))
            print(e)

        return service_result

    @transactional
    @inject
    async def insert_channel(
        self,
        guild_id: int,
        channel_id: int,
        channel_type: ChannelEnum,
        _service: Services = Provide["services"],
        log: KuriLogger = Provide["logger"],
    ) -> ServiceResult[Channel]:
        service_result = ServiceResult[Channel]()

        try:
            channel = Channel(
                channel_id=channel_id, guild_id=guild_id, channel_type=channel_type
            )
            data = _service.channel_repo.insert_channel(channel)
            service_result.set_success(data)

        except Exception as e:
            log.error(e)
            transaction_rollback()
            service_result.set_error(str(e))
            print(e)

        return service_result


class ClanBattlePeriodService:

    @inject
    async def get_latest_cb_period(
        self, _service: Services = Provide["services"]
    ) -> ServiceResult[ClanBattlePeriod]:
        service_result = ServiceResult[ClanBattlePeriod]()
        try:
            data = _service.clan_battle_period_repo.get_latest_cb_period()
            service_result.set_success(data)

        except Exception as e:
            service_result.set_error(str(e))
            print(e)

        return service_result

    @inject
    async def get_current_active_cb_period(
        self, _service: Services = Provide["services"]
    ) -> ServiceResult[ClanBattlePeriod]:
        service_result = ServiceResult[ClanBattlePeriod]()
        try:
            data = _service.clan_battle_period_repo.get_current_active_cb_period()
            service_result.set_success(data)

        except Exception as e:
            service_result.set_error(str(e))
            print(e)

        return service_result

    @inject
    async def get_current_cb_period_day(
        self, _service: Services = Provide["services"]
    ) -> ServiceResult[ClanBattlePeriodDay]:
        service_result = ServiceResult[ClanBattlePeriodDay]()
        try:
            data = _service.clan_battle_period_repo.get_current_active_cb_period_day()
            service_result.set_success(data)

        except Exception as e:
            service_result.set_error(str(e))
            print(e)

        return service_result
