from pyi18n import PyI18n
import discord

# Guild Locale on startup, should be guild_local[guild_id] = lang
guild_locale = {}
default_locale = discord.enums.Locale.american_english.value.lower()

class Locale:
    _instance = None
    _locale = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            available_locales = []
            for locale in discord.enums.Locale:
                available_locales.append(locale.value.lower())
            i18n: PyI18n = PyI18n(available_locales=tuple(available_locales))
            cls._locale = i18n.gettext

        return cls._instance

    def get_text(self, guild_id: int, string: str, **kwargs) -> str:
        lang = guild_locale.get(guild_id, default_locale)
        return self._instance._locale(lang, string, **kwargs)

    def t(self, guild_id: int, string: str, **kwargs) -> str:
        lang = guild_locale.get(guild_id, default_locale)
        return self._instance._locale(lang, string, **kwargs)
