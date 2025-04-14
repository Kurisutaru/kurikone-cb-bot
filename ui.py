import asyncio

import discord
from discord.ui import View, Button, Modal, TextInput

from enums import EmojiEnum, AttackTypeEnum
from locales import Locale
from logger import KuriLogger
from models import ClanBattleLeftover
from services import MainService, UiService, ClanBattleBossBookService
import utils

l = Locale()
logger = KuriLogger()
_main_service = MainService()
_ui_service = UiService()
_clan_battle_boss_book_service = ClanBattleBossBookService()

# Book Button
class BookButton(Button):
    def __init__(self, text: str = EmojiEnum.BOOK.name.capitalize()):
        super().__init__(label=text,
                         style=discord.ButtonStyle.primary,
                         emoji=EmojiEnum.BOOK.value,
                         row=0)

    async def callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id

        service = await _ui_service.book_button_service(interaction)
        if not service.is_success:
            await utils.send_message_short(interaction, service.error_messages, True)
            return

        disable, count_left, leftover = service.result

        view = View(timeout=None)
        view.add_item(BookPatkButton(interaction, disable))
        view.add_item(BookMatkButton(interaction, disable))
        view.add_item(ConfirmationNoCancelButton(emoji_param=EmojiEnum.CANCEL))
        for left_data in leftover:
            view.add_item(BookLeftoverButton(left_data, interaction))

        await utils.send_message_medium(interaction=interaction,
                                        content=f"## {l.t(guild_id, "ui.prompts.choose_entry_type", count_left=count_left )}",
                                        view=view,
                                        ephemeral=True)


# Cancel Button
class CancelButton(Button):
    def __init__(self, text = EmojiEnum.CANCEL.name.capitalize()):
        super().__init__(label=text,
                         style=discord.ButtonStyle.danger,
                         emoji=EmojiEnum.CANCEL.value,
                         row=0)

    async def callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id

        service = await _ui_service.cancel_button_service(interaction)
        if not service.is_success:
            await utils.send_message_short(interaction, service.error_messages, True)
            return

        embeds = service.result

        await interaction.message.edit(embeds=embeds, view=ButtonView(guild_id))
        await utils.send_message_short(interaction, l.t(guild_id, "ui.events.removed_from_booking_list"), True)


# Entry Button
class EntryButton(Button):
    def __init__(self, text: str = EmojiEnum.ENTRY.name.capitalize()):
        super().__init__(label=text,
                         style=discord.ButtonStyle.primary,
                         emoji=EmojiEnum.ENTRY.value,
                         row=1)

    async def callback(self, interaction: discord.Interaction):
        book = await _clan_battle_boss_book_service.get_player_book_entry(message_id=interaction.message.id,
                                                                          player_id=interaction.user.id)
        if book.is_success and book.result is None:
            await utils.send_message_short(interaction=interaction,
                                           content=f"## {l.t(interaction.guild_id, "ui.status.not_yet_booked")}",
                                           ephemeral=True)
            return

        modal = EntryInputModal(interaction.guild_id)
        await interaction.response.send_modal(modal)


# Entry Input
class EntryInputModal(Modal):
    def __init__(self, guild_id: int) -> None:
        super().__init__(
            title=l.t(guild_id, "ui.popup.entry_input.title")
        )
        self.user_input.label = l.t(guild_id, "ui.popup.entry_input.label")
        self.user_input.placeholder = l.t(guild_id, "ui.popup.entry_input.placeholder")

    # Define a text input
    user_input = TextInput(
        label="Damage input",
        placeholder="20",
        style=discord.TextStyle.short,
        required=True,
        min_length=1,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        message_id = interaction.message.id

        service = await _ui_service.entry_input_service(interaction, self.user_input.value)
        if not service.is_success:
            await utils.send_message_short(interaction, service.error_messages, True)
            return

        embeds = service.result

        # Refresh Messages
        message = await utils.discord_try_fetch_message(interaction.channel, message_id)
        if message:
            await interaction.message.edit(embeds=embeds, view=ButtonView(guild_id))

        await interaction.response.defer(ephemeral=True)


# Done Button
class DoneButton(Button):
    def __init__(self, text: str = EmojiEnum.DONE.name.capitalize()):
        super().__init__(label=text,
                         style=discord.ButtonStyle.green,
                         emoji=EmojiEnum.DONE.value,
                         row=1)

    async def callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        message_id = interaction.message.id

        service = await _ui_service.done_button_service(interaction)
        if not service.is_success:
            await utils.send_message_short(interaction, service.error_messages, True)
            return

        view = View(timeout=None)
        view.add_item(DoneOkButton(message_id=message_id))
        view.add_item(ConfirmationNoCancelButton(emoji_param=EmojiEnum.NO))

        await utils.send_message_long(interaction=interaction,
                                      content=f"## {l.t(guild_id, "ui.prompts.confirm_mark_as_done")}",
                                      view=view,
                                      ephemeral=True)


# Done Ok Confirm Button
class DoneOkButton(Button):
    def __init__(self, message_id: int):
        super().__init__(label=EmojiEnum.DONE.name.capitalize(),
                         style=discord.ButtonStyle.green,
                         emoji=EmojiEnum.DONE.value,
                         row=0)
        self.message_id = message_id

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        display_name = interaction.user.display_name
        message_id = self.message_id
        guild_id = interaction.guild_id

        done_service = await _main_service.done_entry(guild_id, message_id, user_id, display_name)
        if not done_service.is_success:
            await utils.discord_close_response(interaction=interaction)
            logger.error(done_service.error_messages)
            return

        # Refresh Messages
        message = await utils.discord_try_fetch_message(channel=interaction.channel, message_id=message_id)
        if message:
            embeds = await _main_service.refresh_clan_battle_boss_embeds(guild_id, message_id)
            if not embeds.is_success:
                await interaction.response.defer(ephemeral=True)
                logger.error(embeds.error_messages)
                return

            await message.edit(embeds=embeds.result, view=ButtonView(guild_id))

        asyncio.create_task(_main_service.refresh_report_channel_message(interaction.guild))

        await utils.discord_close_response(interaction=interaction)


# Dead Button
class DeadButton(Button):
    def __init__(self, text: str = EmojiEnum.FINISH.value):
        super().__init__(label=text,
                         style=discord.ButtonStyle.gray,
                         emoji=EmojiEnum.FINISH.value,
                         row=1)

    async def callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        message_id = interaction.message.id

        service = await _ui_service.dead_button_service(interaction)
        if not service.is_success:
            await utils.send_message_short(interaction, service.error_messages, True)
            return

        book = service.result

        # Fresh Entry
        if book.leftover_time is None:
            modal = LeftoverModal(guild_id)
            await interaction.response.send_modal(modal)
        # Carry over
        else:
            view = View(timeout=None)
            view.add_item(DeadOkButton(message_id=message_id, leftover_time=book.leftover_time))
            view.add_item(ConfirmationNoCancelButton(emoji_param=EmojiEnum.NO))

            await utils.send_message_long(interaction=interaction,
                                          content=f"## {l.t(guild_id, "ui.prompts.confirm_mark_as_boss_kill")}",
                                          view=view,
                                          ephemeral=True)


# Leftover Modal
class LeftoverModal(Modal):
    def __init__(self, guild_id: int):
        super().__init__(
            title=l.t(guild_id, "ui.popup.leftover_input.title")
        )
        self.guild_id = guild_id
        self.user_input.label = l.t(guild_id, "ui.popup.leftover_input.label")
        self.user_input.placeholder = l.t(guild_id, "ui.popup.leftover_input.placeholder")

    # Define a text input
    user_input = TextInput(
        label="Leftover time (in seconds)",
        placeholder="20",
        style=discord.TextStyle.short,
        required=True,
        min_length=1,
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):
        message_id = interaction.message.id
        guild_id = interaction.guild.id
        # Handle the submitted input
        if not self.user_input.value.isdigit():
            await utils.send_message_short(interaction=interaction,
                                           content=f"## {l.t(guild_id, "ui.validation.only_numbers_allowed")}",
                                           ephemeral=True)
            return

        leftover_time = int(self.user_input.value)

        if leftover_time < 20 or leftover_time > 90:
            await utils.send_message_short(interaction=interaction,
                                           content=f"## {l.t(guild_id, "ui.validation.leftover_time_range_invalid")}",
                                           ephemeral=True)
            return

        view = View(timeout=None)
        view.add_item(DeadOkButton(message_id=message_id, leftover_time=leftover_time))
        view.add_item(ConfirmationNoCancelButton(emoji_param=EmojiEnum.NO))

        await utils.send_message_long(interaction=interaction,
                                      content=f"## {l.t(guild_id, "ui.prompts.boss_kill_confirmation", leftover_time=leftover_time)}",
                                      view=view,
                                      ephemeral=True)


# Dead Ok Confirm Button
class DeadOkButton(Button):
    def __init__(self, message_id: int, leftover_time: int):
        super().__init__(label=EmojiEnum.DONE.name.capitalize(),
                         style=discord.ButtonStyle.green,
                         emoji=EmojiEnum.DONE.value,
                         row=0)
        self.message_id = message_id
        self.leftover_time = leftover_time

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        display_name = interaction.user.display_name
        message_id = self.message_id
        guild_id = interaction.guild_id
        leftover_time = self.leftover_time

        await utils.discord_close_response(interaction=interaction)

        dead_result = await _main_service.dead_ok(guild_id, message_id, user_id, display_name, leftover_time)
        if not dead_result.is_success:
            logger.error(dead_result.error_messages)
            await interaction.response.defer(ephemeral=True)

        boss_id = dead_result.result.clan_battle_boss_id
        generate = await _main_service.generate_next_boss(interaction, boss_id, message_id,
                                                              dead_result.result.attack_type, leftover_time)
        if not generate.is_success:
            logger.error(generate.error_messages)
            await interaction.response.defer(ephemeral=True)

        message = await utils.discord_try_fetch_message(interaction.channel, generate.result.message_id)
        if message is None:
            logger.error("Failed to fetch message")
            await interaction.response.defer(ephemeral=True)

        embeds = await _main_service.refresh_clan_battle_boss_embeds(guild_id, message.id)
        if not embeds.is_success:
            await interaction.response.defer(ephemeral=True)
            logger.error(embeds.error_messages)
            return

        asyncio.create_task(_main_service.refresh_report_channel_message(interaction.guild))

        await message.edit(content="", embeds=embeds.result, view=ButtonView(guild_id))


# PATK Button
class BookPatkButton(Button):
    def __init__(self, interaction: discord.Interaction, disable: bool):
        self.local_emoji = EmojiEnum.PATK
        self.attack_type = AttackTypeEnum.PATK
        self.parent_interaction = interaction

        super().__init__(label=self.local_emoji.name,
                         style=discord.ButtonStyle.success,
                         emoji=self.local_emoji.value,
                         disabled=disable,
                         row=0)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        display_name = interaction.user.display_name
        guild_id = interaction.guild_id
        message_id = self.parent_interaction.message.id

        insert_result = await _main_service.insert_boss_book_entry(guild_id, message_id, user_id, display_name,
                                                                       self.attack_type)
        if not insert_result.is_success:
            await interaction.response.defer(ephemeral=True)
            logger.error(insert_result.error_messages)
            return

        embeds = await _main_service.refresh_clan_battle_boss_embeds(guild_id, message_id)
        if not insert_result.is_success:
            await interaction.response.defer(ephemeral=True)
            logger.error(embeds.error_messages)
            return

        await self.parent_interaction.message.edit(embeds=embeds.result, view=ButtonView(guild_id))
        await utils.discord_close_response(interaction=interaction)
        await utils.send_channel_message_short(interaction=interaction,
                                       content=f"{l.t(guild_id, "ui.events.user_added_to_booking_list", user=display_name, emoji=self.local_emoji.value)}")


# MATK Button
class BookMatkButton(Button):
    def __init__(self, interaction: discord.Interaction, disable: bool):
        self.local_emoji = EmojiEnum.MATK
        self.attack_type = AttackTypeEnum.MATK
        self.parent_interaction = interaction

        super().__init__(label=self.local_emoji.name,
                         style=discord.ButtonStyle.blurple,
                         emoji=self.local_emoji.value,
                         disabled=disable,
                         row=0)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        display_name = interaction.user.display_name
        guild_id = interaction.guild_id
        message_id = self.parent_interaction.message.id

        insert_result = await _main_service.insert_boss_book_entry(guild_id, message_id, user_id, display_name,
                                                                   self.attack_type)
        if not insert_result.is_success:
            await interaction.response.defer(ephemeral=True)
            logger.error(insert_result.error_messages)
            return

        embeds = await _main_service.refresh_clan_battle_boss_embeds(guild_id, message_id)
        if not insert_result.is_success:
            await interaction.response.defer(ephemeral=True)
            logger.error(embeds.error_messages)
            return

        await self.parent_interaction.message.edit(embeds=embeds.result, view=ButtonView(guild_id))
        await utils.discord_close_response(interaction=interaction)
        await utils.send_channel_message_short(interaction=interaction,
                                       content=f"{l.t(guild_id, "ui.events.user_added_to_booking_list", user=display_name, emoji=self.local_emoji.value)}")


# Leftover Button
class BookLeftoverButton(Button):
    def __init__(self, leftover: ClanBattleLeftover, interaction: discord.Interaction):
        self.local_emoji = EmojiEnum.CARRY
        self.attack_type = AttackTypeEnum.CARRY
        self.parent_interaction = interaction
        self.parent_overall_id = leftover.clan_battle_overall_entry_id
        self.label_string = f"{leftover.attack_type.value} {leftover.leftover_time}s ({leftover.clan_battle_boss_name})"
        self.leftover_time = leftover.leftover_time

        super().__init__(label=self.label_string,
                         style=discord.ButtonStyle.blurple,
                         emoji=self.local_emoji.value,
                         row=1)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        display_name = interaction.user.display_name
        guild_id = interaction.guild_id
        message_id = self.parent_interaction.message.id
        leftover_time = self.leftover_time
        attack_type = self.attack_type
        parent_overall_id = self.parent_overall_id

        insert_result = await _main_service.insert_boss_book_entry(guild_id, message_id, user_id, display_name,
                                                                       attack_type, parent_overall_id, leftover_time)
        if not insert_result.is_success:
            await interaction.response.defer(ephemeral=True)
            logger.error(insert_result.error_messages)
            return

        message = await utils.discord_try_fetch_message(interaction.channel, message_id)
        if message is None:
            await interaction.response.defer(ephemeral=True)
            logger.error("Could not fetch message")
            return

        embeds = await _main_service.refresh_clan_battle_boss_embeds(guild_id, message_id)
        if not insert_result.is_success:
            await interaction.response.defer(ephemeral=True)
            logger.error(embeds.error_messages)
            return

        await self.parent_interaction.message.edit(embeds=embeds.result, view=ButtonView(guild_id))
        await utils.discord_close_response(interaction=interaction)
        await utils.send_channel_message_short(interaction=interaction,
                                       content=f"{l.t(guild_id, "ui.events.user_added_to_booking_list", user=display_name, emoji=self.local_emoji.value)}")

# Universal Done / OK Button
class ConfirmationOkDoneButton(Button):
    def __init__(self, emoji_param: EmojiEnum = EmojiEnum.DONE, text: str= None):
        super().__init__(label=text or emoji_param.name.capitalize(),
                         style=discord.ButtonStyle.green,
                         emoji=emoji_param.value,
                         row=0)

# Universal Cancel / No Button
class ConfirmationNoCancelButton(Button):
    def __init__(self, emoji_param: EmojiEnum = EmojiEnum.NO, text: str= None):
        super().__init__(label=text or emoji_param.name.capitalize(),
                         style=discord.ButtonStyle.red,
                         emoji=emoji_param.value,
                         row=0)

    async def callback(self, interaction: discord.Interaction):
        await utils.discord_close_response(interaction=interaction)


class ButtonView(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.add_item(BookButton(text=l.t(guild_id, "ui.button.book")))
        self.add_item(CancelButton(text=l.t(guild_id, "ui.button.cancel")))
        self.add_item(EntryButton(text=l.t(guild_id, "ui.button.entry")))
        self.add_item(DoneButton(text=l.t(guild_id, "ui.button.done")))
        self.add_item(DeadButton(text=l.t(guild_id, "ui.button.dead")))

