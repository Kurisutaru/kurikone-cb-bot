import asyncio

import discord
from dependency_injector.wiring import inject, Provide
from discord import ButtonStyle, TextStyle
from discord.ui import View, Button, Modal, TextInput

from enums import EmojiEnum, AttackTypeEnum
from locales import Locale
from logger import KuriLogger
from models import ClanBattleLeftover
from services import MainService, UiService
from utils import (
    send_message_short,
    send_message_medium,
    send_message_long,
    discord_close_response,
    send_channel_message_short,
)


# Book Button
class BookButton(Button):
    def __init__(self, text: str = EmojiEnum.BOOK.name.capitalize()):
        super().__init__(
            label=text, style=ButtonStyle.primary, emoji=EmojiEnum.BOOK.value, row=0
        )

    @inject
    async def callback(
        self,
        interaction: discord.Interaction,
        ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        guild_id = interaction.guild_id

        service = await ui_service.book_button_service(interaction)
        if not service.is_success:
            await send_message_short(interaction, service.error_messages, True)
            return

        disable, count_left, leftover = service.result

        view = View(timeout=None)
        view.add_item(BookPatkButton(interaction, disable))
        view.add_item(BookMatkButton(interaction, disable))
        view.add_item(
            ConfirmationNoCancelButton(
                text=l.t(guild_id, "ui.button.close"), emoji_param=EmojiEnum.CANCEL
            )
        )
        for left_data in leftover:
            view.add_item(BookLeftoverButton(left_data, interaction))

        await send_message_medium(
            interaction=interaction,
            content=f"## {l.t(guild_id, "ui.prompts.choose_entry_type", count_left=count_left )}",
            view=view,
            ephemeral=True,
        )


# Cancel Button
class CancelButton(Button):
    def __init__(self, text=EmojiEnum.CANCEL.name.capitalize()):
        super().__init__(
            label=text, style=ButtonStyle.danger, emoji=EmojiEnum.CANCEL.value, row=0
        )

    @inject
    async def callback(
        self,
        interaction: discord.Interaction,
        _ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        guild_id = interaction.guild_id

        service = await _ui_service.cancel_button_service(interaction)
        if not service.is_success:
            await send_message_short(interaction, service.error_messages, True)
            return

        embeds = service.result

        await interaction.message.edit(embeds=embeds, view=ButtonView(guild_id))
        await send_message_short(
            interaction, l.t(guild_id, "ui.events.removed_from_booking_list"), True
        )


# Round Button
class RotateButton(Button):
    def __init__(self, text=EmojiEnum.ROTATE.name.capitalize()):
        super().__init__(
            label=text, style=ButtonStyle.blurple, emoji=EmojiEnum.ROTATE.value, row=0
        )

    @inject
    async def callback(
        self,
        interaction: discord.Interaction,
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        modal = RoundModal(interaction)
        await interaction.response.send_modal(modal)


# Round Modal
class RoundModal(Modal):
    @inject
    def __init__(
        self,
        parent_inter: discord.Interaction,
        l: Locale = Provide["locale"],
    ):
        self.guild_id = parent_inter.guild_id
        self.user_input.label = l.t(self.guild_id, "ui.popup.round_input.label")
        self.user_input.placeholder = l.t(
            self.guild_id, "ui.popup.round_input.placeholder"
        )
        self.parent_inter = parent_inter
        super().__init__(title=l.t(parent_inter.guild_id, "ui.popup.round_input.title"))

    # Define a text input
    user_input = TextInput(
        label="Round",
        placeholder="5",
        style=TextStyle.short,
        required=True,
        min_length=1,
        max_length=2,
    )

    @inject
    async def on_submit(
        self,
        interaction: discord.Interaction,
        ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        if not self.user_input.value.isdigit():
            await send_message_short(
                interaction=interaction,
                content=f"## {l.t(interaction.guild_id, "ui.validation.only_numbers_allowed")}",
                ephemeral=True,
            )
            return

        round_select = int(self.user_input.value)
        service = await ui_service.rotate_round(interaction, round_select)
        if not service.is_success:
            await send_message_short(interaction, service.error_messages, True)
            return

        await self.parent_inter.message.edit(
            embeds=service.result, view=ButtonView(interaction.guild_id)
        )
        await interaction.response.defer(ephemeral=True)


# Entry Button
class EntryButton(Button):
    def __init__(self, text: str = EmojiEnum.ENTRY.name.capitalize()):
        super().__init__(
            label=text, style=ButtonStyle.primary, emoji=EmojiEnum.ENTRY.value, row=1
        )

    @inject
    async def callback(
        self,
        interaction: discord.Interaction,
        _ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):

        service = await _ui_service.entry_button_service(interaction)
        if not service.is_success:
            await send_message_short(interaction, service.error_messages, True)
            return

        modal = EntryInputModal(interaction)
        await interaction.response.send_modal(modal)


# Entry Input
class EntryInputModal(Modal):
    @inject
    def __init__(
        self,
        parent_inter: discord.Interaction,
        l: Locale = Provide["locale"],
    ) -> None:
        super().__init__(title=l.t(parent_inter.guild_id, "ui.popup.entry_input.title"))
        self.user_input.label = l.t(parent_inter.guild_id, "ui.popup.entry_input.label")
        self.user_input.placeholder = l.t(
            parent_inter.guild_id, "ui.popup.entry_input.placeholder"
        )
        self.parent_inter = parent_inter

    # Define a text input
    user_input = TextInput(
        label="Damage input",
        placeholder="20",
        style=TextStyle.short,
        required=True,
        min_length=1,
        max_length=10,
    )

    @inject
    async def on_submit(
        self,
        interaction: discord.Interaction,
        ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        guild_id = interaction.guild_id

        service = await ui_service.entry_input_service(
            interaction, self.user_input.value
        )
        if not service.is_success:
            await send_message_short(interaction, service.error_messages, True)
            return

        await self.parent_inter.message.edit(
            embeds=service.result, view=ButtonView(guild_id)
        )
        await interaction.response.defer(ephemeral=True)


# Done Button
class DoneButton(Button):
    def __init__(self, text: str = EmojiEnum.DONE.name.capitalize()):
        super().__init__(
            label=text, style=ButtonStyle.green, emoji=EmojiEnum.DONE.value, row=1
        )

    @inject
    async def callback(
        self,
        interaction: discord.Interaction,
        ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        guild_id = interaction.guild_id

        service = await ui_service.done_button_service(interaction)
        if not service.is_success:
            await send_message_short(interaction, service.error_messages, True)
            return

        view = View(timeout=None)
        view.add_item(DoneOkButton(interaction))
        view.add_item(ConfirmationNoCancelButton(emoji_param=EmojiEnum.NO))

        await send_message_long(
            interaction=interaction,
            content=f"## {l.t(guild_id, "ui.prompts.confirm_mark_as_done")}",
            view=view,
            ephemeral=True,
        )


# Done Ok Confirm Button
class DoneOkButton(Button):
    def __init__(self, parent_inter: discord.Interaction):
        super().__init__(
            label=EmojiEnum.DONE.name.capitalize(),
            style=ButtonStyle.green,
            emoji=EmojiEnum.DONE.value,
            row=0,
        )
        self.parent_inter = parent_inter

    @inject
    async def callback(
        self,
        interaction: discord.Interaction,
        main_service: MainService = Provide["main_service"],
        ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        guild_id = interaction.guild_id

        done_service = await main_service.done_entry(interaction)
        if not done_service.is_success:
            await discord_close_response(interaction=interaction)
            log.error(done_service.error_messages)
            return

        await self.parent_inter.message.edit(
            embeds=done_service.result, view=ButtonView(guild_id)
        )

        asyncio.create_task(
            main_service.refresh_report_channel_message(interaction.guild)
        )

        await discord_close_response(interaction=interaction)


# Dead Button
class DeadButton(Button):
    def __init__(self, text: str = EmojiEnum.FINISH.value):
        super().__init__(
            label=text, style=ButtonStyle.gray, emoji=EmojiEnum.FINISH.value, row=1
        )

    @inject
    async def callback(
        self,
        interaction: discord.Interaction,
        _ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        guild_id = interaction.guild_id

        service = await _ui_service.dead_button_service(interaction)
        if not service.is_success:
            await send_message_short(interaction, service.error_messages, True)
            return

        book = service.result

        # Fresh Entry
        if book.leftover_time is None:
            modal = LeftoverModal(interaction)
            await interaction.response.send_modal(modal)
        # Carry over
        else:
            view = View(timeout=None)
            view.add_item(DeadOkButton(interaction, book.leftover_time))
            view.add_item(ConfirmationNoCancelButton(emoji_param=EmojiEnum.NO))

            await send_message_long(
                interaction=interaction,
                content=f"## {l.t(guild_id, "ui.prompts.confirm_mark_as_boss_kill")}",
                view=view,
                ephemeral=True,
            )


# Leftover Modal
class LeftoverModal(Modal):
    @inject
    def __init__(
        self,
        parent_inter: discord.Interaction,
        l: Locale = Provide["locale"],
    ):
        self.guild_id = parent_inter.guild_id
        self.user_input.label = l.t(self.guild_id, "ui.popup.leftover_input.label")
        self.user_input.placeholder = l.t(
            self.guild_id, "ui.popup.leftover_input.placeholder"
        )
        self.parent_inter = parent_inter
        super().__init__(
            title=l.t(parent_inter.guild_id, "ui.popup.leftover_input.title")
        )

    # Define a text input
    user_input = TextInput(
        label="Leftover time (in seconds)",
        placeholder="20",
        style=TextStyle.short,
        required=True,
        min_length=1,
        max_length=2,
    )

    @inject
    async def on_submit(
        self,
        interaction: discord.Interaction,
        _ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        guild_id = interaction.guild.id
        # Handle the submitted input
        if not self.user_input.value.isdigit():
            await send_message_short(
                interaction=interaction,
                content=f"## {l.t(guild_id, "ui.validation.only_numbers_allowed")}",
                ephemeral=True,
            )
            return

        leftover_time = int(self.user_input.value)

        if leftover_time < 20 or leftover_time > 90:
            await send_message_short(
                interaction=interaction,
                content=f"## {l.t(guild_id, "ui.validation.leftover_time_range_invalid")}",
                ephemeral=True,
            )
            return

        view = View(timeout=None)
        view.add_item(DeadOkButton(interaction, leftover_time))
        view.add_item(ConfirmationNoCancelButton(emoji_param=EmojiEnum.NO))

        await send_message_long(
            interaction=interaction,
            content=f"## {l.t(guild_id, "ui.prompts.boss_kill_confirmation", leftover_time=leftover_time)}",
            view=view,
            ephemeral=True,
        )


# Dead Ok Confirm Button
class DeadOkButton(Button):
    def __init__(self, parent_inter: discord.Interaction, leftover_time: int):
        super().__init__(
            label=EmojiEnum.DONE.name.capitalize(),
            style=ButtonStyle.green,
            emoji=EmojiEnum.DONE.value,
            row=0,
        )
        self.parent_inter = parent_inter
        self.leftover_time = leftover_time

    @inject
    async def callback(
        self,
        interaction: discord.Interaction,
        _main_service: MainService = Provide["main_service"],
        _ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        leftover_time = self.leftover_time

        await discord_close_response(interaction=interaction)

        dead_result = await _main_service.dead_ok(self.parent_inter, leftover_time)
        if not dead_result.is_success:
            log.error(dead_result.error_messages)
            await interaction.response.defer(ephemeral=True)
            return

        asyncio.create_task(
            _main_service.refresh_report_channel_message(interaction.guild)
        )


# PATK Button
class BookPatkButton(Button):
    def __init__(
        self,
        interaction: discord.Interaction,
        disable: bool,
        l: Locale = Provide["locale"],
    ):
        self.local_emoji = EmojiEnum.PATK
        self.attack_type = AttackTypeEnum.PATK
        self.parent_inter = interaction

        super().__init__(
            label=l.t(interaction.guild_id, "ui.button.physical"),
            style=ButtonStyle.success,
            emoji=self.local_emoji.value,
            disabled=disable,
            row=0,
        )

    @inject
    async def callback(
        self,
        interaction: discord.Interaction,
        ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        user_id = interaction.user.id
        display_name = interaction.user.display_name
        channel_id = interaction.channel.id
        guild_id = interaction.guild_id

        embeds = await ui_service.insert_boss_book_entry(
            guild_id,
            channel_id,
            user_id,
            display_name,
            self.attack_type,
        )
        if not embeds.is_success:
            await interaction.response.defer(ephemeral=True)
            log.error(embeds.error_messages)
            return

        await self.parent_inter.message.edit(
            embeds=embeds.result, view=ButtonView(guild_id)
        )
        await discord_close_response(interaction=interaction)
        await send_channel_message_short(
            interaction=interaction,
            content=f"{l.t(guild_id, "ui.events.user_added_to_booking_list", user=display_name, emoji=self.local_emoji.value)}",
        )


# MATK Button
class BookMatkButton(Button):
    @inject
    def __init__(
        self,
        interaction: discord.Interaction,
        disable: bool,
        l: Locale = Provide["locale"],
    ):
        self.local_emoji = EmojiEnum.MATK
        self.attack_type = AttackTypeEnum.MATK
        self.parent_inter = interaction

        super().__init__(
            label=l.t(interaction.guild_id, "ui.button.magical"),
            style=ButtonStyle.blurple,
            emoji=self.local_emoji.value,
            disabled=disable,
            row=0,
        )

    @inject
    async def callback(
        self,
        interaction: discord.Interaction,
        ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        user_id = interaction.user.id
        display_name = interaction.user.display_name
        channel_id = interaction.channel.id
        guild_id = interaction.guild_id

        embeds = await ui_service.insert_boss_book_entry(
            guild_id,
            channel_id,
            user_id,
            display_name,
            self.attack_type,
        )
        if not embeds.is_success:
            await interaction.response.defer(ephemeral=True)
            log.error(embeds.error_messages)
            return

        await self.parent_inter.message.edit(
            embeds=embeds.result, view=ButtonView(guild_id)
        )
        await discord_close_response(interaction=interaction)
        await send_channel_message_short(
            interaction=interaction,
            content=f"{l.t(guild_id, "ui.events.user_added_to_booking_list", user=display_name, emoji=self.local_emoji.value)}",
        )


# Leftover Button
class BookLeftoverButton(Button):
    @inject
    def __init__(
        self,
        leftover: ClanBattleLeftover,
        interaction: discord.Interaction,
        l: Locale = Provide["locale"],
    ):
        self.local_emoji = EmojiEnum.CARRY
        self.attack_type = AttackTypeEnum.CARRY
        self.parent_inter = interaction
        self.parent_overall_id = leftover.clan_battle_overall_entry_id
        self.label_string = l.t(
            interaction.guild_id,
            "ui.button.leftover",
            type=leftover.attack_type.value,
            sec=leftover.leftover_time,
            boss=leftover.clan_battle_boss_name,
        )
        self.leftover_time = leftover.leftover_time

        super().__init__(
            label=self.label_string,
            style=ButtonStyle.blurple,
            emoji=self.local_emoji.value,
            row=1,
        )

    @inject
    async def callback(
        self,
        interaction: discord.Interaction,
        ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        log: KuriLogger = Provide["logger"],
    ):
        user_id = interaction.user.id
        display_name = interaction.user.display_name
        channel_id = interaction.channel.id
        guild_id = interaction.guild_id

        embeds = await ui_service.insert_boss_book_entry(
            guild_id,
            channel_id,
            user_id,
            display_name,
            self.attack_type,
            self.parent_overall_id,
            self.leftover_time,
        )
        if not embeds.is_success:
            await interaction.response.defer(ephemeral=True)
            log.error(embeds.error_messages)
            return

        await self.parent_inter.message.edit(
            embeds=embeds.result, view=ButtonView(guild_id)
        )
        await discord_close_response(interaction=interaction)
        await send_channel_message_short(
            interaction=interaction,
            content=f"{l.t(guild_id, "ui.events.user_added_to_booking_list", user=display_name, emoji=self.local_emoji.value)}",
        )


# Universal Done / OK Button
class ConfirmationOkDoneButton(Button):
    def __init__(self, emoji_param: EmojiEnum = EmojiEnum.DONE, text: str = None):
        super().__init__(
            label=text or emoji_param.name.capitalize(),
            style=ButtonStyle.green,
            emoji=emoji_param.value,
            row=0,
        )


# Universal Cancel / No Button
class ConfirmationNoCancelButton(Button):
    def __init__(self, emoji_param: EmojiEnum = EmojiEnum.NO, text: str = None):
        super().__init__(
            label=text or emoji_param.name.capitalize(),
            style=ButtonStyle.red,
            emoji=emoji_param.value,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        await discord_close_response(interaction=interaction)


class ButtonView(View):
    @inject
    def __init__(
        self,
        guild_id: int,
        l: Locale = Provide["locale"],
    ):
        super().__init__(timeout=None)
        self.add_item(BookButton(text=l.t(guild_id, "ui.button.book")))
        self.add_item(CancelButton(text=l.t(guild_id, "ui.button.cancel")))
        self.add_item(RotateButton(text=l.t(guild_id, "ui.button.rotate")))
        self.add_item(EntryButton(text=l.t(guild_id, "ui.button.entry")))
        self.add_item(DoneButton(text=l.t(guild_id, "ui.button.done")))
        self.add_item(DeadButton(text=l.t(guild_id, "ui.button.dead")))


class ConfirmationButtonView(View):
    @inject
    def __init__(
        self,
        guild_id: int,
        _main_service: MainService = Provide["main_service"],
        _ui_service: UiService = Provide["ui_service"],
        l: Locale = Provide["locale"],
        yes_emoji: EmojiEnum = EmojiEnum.YES,
        no_emoji: EmojiEnum = EmojiEnum.NO,
        yes_callback=None,
    ):
        super().__init__(timeout=None)
        yes_btn = ConfirmationOkDoneButton(yes_emoji, l.t(guild_id, "ui.button.yes"))
        no_btn = ConfirmationNoCancelButton(no_emoji, l.t(guild_id, "ui.button.no"))

        if yes_callback:
            yes_btn.callback = yes_callback

        self.add_item(yes_btn)
        self.add_item(no_btn)
