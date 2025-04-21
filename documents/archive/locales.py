from discord import app_commands
from discord.app_commands import locale_str, TranslationContextLocation
from pyi18n import PyI18n
import discord
from pyi18n.loaders import PyI18nYamlLoader

###
# Kuri : Archived locales using https://github.com/sectasy0/pyi18n/
# The reason changed that the package have glitch if you put the "Key" = Yes / No
# It will be not loaded on the translation.
###

# Guild Locale on startup, should be guild_local[guild_id] = lang
guild_locale = {}
available_locales = []
default_locale = discord.enums.Locale.american_english.value.lower()


class Locale:
    _instance = None
    _locale = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            for locale in discord.enums.Locale:
                available_locales.append(locale.value.lower())
            loader: PyI18nYamlLoader = PyI18nYamlLoader()
            i18n: PyI18n = PyI18n(
                available_locales=tuple(available_locales), loader=loader
            )
            cls._locale = i18n.gettext

        return cls._instance

    def get_text(self, guild_id: int, string: str, **kwargs) -> str:
        lang = guild_locale.get(guild_id, default_locale)
        return self._instance._locale(lang, string, **kwargs)

    def t(self, guild_id: int, string: str, **kwargs) -> str:
        lang = guild_locale.get(guild_id, default_locale)
        return self._instance._locale(lang, string, **kwargs)

    def text(self, locale: str, string: str) -> str:
        return self._instance._locale(locale, string)


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
        return self.locale.text(lang, f"commands.{command}.name") or string

    def _translate_command_description(self, context, string, lang):
        command = context.data.name
        return self.locale.text(lang, f"commands.{command}.description") or string

    # def _translate_parameter(self, context, string, lang):
    #     command = context.data.command.name
    #     parameter = context.data.name
    #     return i18n.t(f"commands.{command}.params.{parameter}", locale=lang) or string
