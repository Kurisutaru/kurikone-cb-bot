import discord
import i18n
from attrs import define
from discord import app_commands
from discord.app_commands import locale_str, TranslationContextLocation

# Guild Locale on startup, should be guild_local[guild_id] = lang
guild_locale = {}
available_locales = []
default_locale = discord.enums.Locale.american_english.value.lower()


@define
class Locale:
    _instance = None
    _locale = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            i18n.load_path.append("locales")
            i18n.set("filename_format", "{locale}.{format}")
            i18n.set("file_format", "yaml")
            i18n.load_everything()
            cls._locale = i18n
        return cls._instance

    def get_text(self, guild_id: int, text: str, **kwargs) -> str:
        lang = guild_locale.get(guild_id, default_locale)
        return self._locale.t(key=text, locale=lang, **kwargs)

    def t(self, guild_id: int, text: str, **kwargs) -> str:
        lang = guild_locale.get(guild_id, default_locale)
        return self._locale.t(key=text, locale=lang, **kwargs)

    def text(self, text: str, lang: str, **kwargs) -> str:
        return self._locale.t(key=text, locale=lang, **kwargs)

    def nf(self, guild_id: int, text: str):
        lang = guild_locale.get(guild_id, default_locale)
        return self._locale.t(key="message.not_found", locale=lang, input=text)


class DiscordTranslator(app_commands.Translator):
    def __init__(self):
        self.locale = Locale()

    async def translate(
        self,
        string: locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContext,
    ):
        # Handle different translation contexts
        if context.location == TranslationContextLocation.command_name:
            return self._translate_command(context, string, locale.value.lower())

        elif context.location == TranslationContextLocation.command_description:
            return self._translate_command_description(
                context, string, locale.value.lower()
            )

        # elif context.location == TranslationContextLocation.parameter_name:
        #     return self._translate_parameter(context, string, locale.value.lower())

        # Add other context types as needed

        return string  # Fallback to original string

    def _translate_command(self, context, string, lang):
        command = context.data.name
        return self.locale.text(text=f"commands.{command}.name", lang=lang) or string

    def _translate_command_description(self, context, string, lang):
        command = context.data.name
        return (
            self.locale.text(text=f"commands.{command}.description", lang=lang)
            or string
        )

    # def _translate_parameter(self, context, string, lang):
    #     command = context.data.command.name
    #     parameter = context.data.name
    #     return i18n.t(f"commands.{command}.params.{parameter}", locale=lang) or string


l = Locale()
