import discord
import i18n
from discord import app_commands
from discord.app_commands import locale_str, TranslationContextLocation

from globals import GUILD_LOCALE

available_locales = []
default_locale = discord.enums.Locale.american_english.value


class Locale:
    def __init__(
        self,
        load_path="locales",
        filename_format="{locale}.{format}",
        file_format="yaml",
    ):
        self._locale = i18n
        self._locale.load_path.append(load_path)
        self._locale.set("filename_format", filename_format)
        self._locale.set("file_format", file_format)
        self._locale.load_everything()  # Expensive operation, called only once

    def get_text(self, guild_id: int, text: str, **kwargs) -> str:
        lang = GUILD_LOCALE.get(guild_id, default_locale)
        try:
            return self._locale.t(key=text, locale=lang, **kwargs)
        except (KeyError, ValueError) as e:
            print(f"Fallback to default_locale: {e}")
            return self._locale.t(key=text, locale=default_locale, **kwargs)

    def t(self, guild_id: int, text: str, **kwargs) -> str:
        lang = GUILD_LOCALE.get(guild_id, default_locale)
        try:
            return self._locale.t(key=text, locale=lang, **kwargs)
        except (KeyError, ValueError) as e:
            return self._locale.t(key=text, locale=default_locale, **kwargs)

    def text(self, text: str, lang: str, **kwargs) -> str:
        try:
            return self._locale.t(key=text, locale=lang, **kwargs)
        except (KeyError, ValueError) as e:
            return self._locale.t(key=text, locale=default_locale, **kwargs)

    def nf(self, guild_id: int, text: str):
        lang = GUILD_LOCALE.get(guild_id, default_locale)
        try:
            return self._locale.t(key="message.not_found", locale=lang, input=text)
        except (KeyError, ValueError) as e:
            return self._locale.t(
                key="message.not_found", locale=default_locale, input=text
            )


class DiscordTranslator(app_commands.Translator):
    def __init__(self):
        self.locale = Locale()

    async def translate(
        self,
        string: locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContext,
    ):
        return self._translate_command(context, string, locale.value)

    """
        Kuri Notes on Translation
        if location TranslationContextLocation.command_name or TranslationContextLocation.command_description
        return class Command(Generic[GroupT, P, T]):
            Parameters
            -----------
            name: Union[:class:`str`, :class:`locale_str`]
                The name of the application command.
            description: Union[:class:`str`, :class:`locale_str`]
                The description of the application command. This shows up in the UI to describe
                the application command.
                
        if location TranslationContextLocation.parameter_name or TranslationContextLocation.parameter_description
        return class Parameter:
            Attributes
            -----------
            name: :class:`str`
                The name of the parameter. This is the Python identifier for the parameter.
            display_name: :class:`str`
                The displayed name of the parameter on Discord.
            description: :class:`str`
                The description of the parameter.
            command: :class:`Command`
                The command this parameter is attached to.
    """

    def _translate_command(self, context, string, lang):
        if context.data is None:
            return string

        location_map = {
            TranslationContextLocation.command_name: "commands.{command}.name",
            TranslationContextLocation.command_description: "commands.{command}.description",
            TranslationContextLocation.parameter_name: "commands.{command}.params.{param}.name",
            TranslationContextLocation.parameter_description: "commands.{command}.params.{param}.description",
        }

        try:
            key_template = location_map.get(context.location)
            if not key_template:
                return string

            if context.location in (
                TranslationContextLocation.parameter_name,
                TranslationContextLocation.parameter_description,
            ):
                if not hasattr(context.data, "command") or context.data.command is None:
                    return string
                command = context.data.command.name
                param = context.data.name
                key = key_template.format(command=command, param=param)
            else:
                command = context.data.name
                key = key_template.format(command=command)

            result = self.locale.text(key, lang)
            return result if result is not None else string
        except (KeyError, ValueError, AttributeError) as e:
            return string
