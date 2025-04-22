import pytest
from unittest.mock import MagicMock
from discord.app_commands import TranslationContextLocation, locale_str
from locales import Locale, DiscordTranslator, default_locale
import discord


# Fixtures with mocked load_everything
@pytest.fixture
def mock_i18n_t(mocker):
    return mocker.patch("locales.i18n.t")


@pytest.fixture
def mock_load_everything(mocker):
    """Prevent i18n from scanning the filesystem"""
    return mocker.patch("locales.i18n.load_everything")


@pytest.fixture
def locale_instance(mock_load_everything):
    # Singleton reset between tests
    Locale._instance = None
    return Locale()


@pytest.fixture
def translator_instance(locale_instance):
    return DiscordTranslator()


# Test cases
def test_singleton_pattern(locale_instance):
    instance1 = Locale()
    instance2 = Locale()
    assert instance1 is instance2


def test_get_text_with_guild_locale(mocker, mock_i18n_t, locale_instance):
    mocker.patch("globals.GUILD_LOCALE", {123: "en-us"})
    mock_i18n_t.return_value = "Hello"

    result = locale_instance.get_text(123, "greeting")
    mock_i18n_t.assert_called_once_with(key="greeting", locale="en-us")
    assert result == "Hello"


def test_get_text_with_default_locale(mocker, mock_i18n_t, locale_instance):
    mocker.patch("globals.GUILD_LOCALE", {})
    mock_i18n_t.return_value = "Default Hello"

    result = locale_instance.get_text(456, "greeting")
    mock_i18n_t.assert_called_once_with(key="greeting", locale=default_locale)
    assert result == "Default Hello"


def test_t_with_guild_locale(mocker, mock_i18n_t, locale_instance):
    mocker.patch("globals.GUILD_LOCALE", {123: "en-us"})
    mock_i18n_t.return_value = "Hello"

    result = locale_instance.t(123, "greeting")
    mock_i18n_t.assert_called_once_with(key="greeting", locale="en-us")
    assert result == "Hello"


def test_t_with_default_locale(mocker, mock_i18n_t, locale_instance):
    mocker.patch("globals.GUILD_LOCALE", {})
    mock_i18n_t.return_value = "Default Hello"

    result = locale_instance.t(456, "greeting")
    mock_i18n_t.assert_called_once_with(key="greeting", locale=default_locale)
    assert result == "Default Hello"


def test_text_with_guild_locale(mocker, mock_i18n_t, locale_instance):
    mocker.patch("globals.GUILD_LOCALE", {123: "en-us"})
    mock_i18n_t.return_value = "Hello"

    result = locale_instance.t(123, "greeting")
    mock_i18n_t.assert_called_once_with(key="greeting", locale="en-us")
    assert result == "Hello"


def test_text_with_default_locale(mocker, mock_i18n_t, locale_instance):
    mocker.patch("globals.GUILD_LOCALE", {})
    mock_i18n_t.return_value = "Default Hello"

    result = locale_instance.text("greeting", "en-us")
    mock_i18n_t.assert_called_once_with(key="greeting", locale=default_locale)
    assert result == "Default Hello"


def test_nf_method(mocker, mock_i18n_t, locale_instance):
    mocker.patch("globals.GUILD_LOCALE", {123: "en"})
    mock_i18n_t.return_value = "Not found: test"

    result = locale_instance.nf(123, "test")
    mock_i18n_t.assert_called_once_with(
        key="message.not_found", locale=default_locale, input="test"
    )
    assert result == "Not found: test"


@pytest.mark.asyncio
async def test_translate_command_name(translator_instance, mocker):
    mocker.patch.object(Locale, "text", return_value="Translated Command Name")

    mock_context = MagicMock()
    mock_context.location = TranslationContextLocation.command_name
    mock_context.data.name = "test_cmd"

    translated = await translator_instance.translate(
        string=locale_str("original"),
        locale=discord.Locale.american_english,
        context=mock_context,
    )

    Locale.text.assert_called_once_with("commands.test_cmd.name", "en-us")
    assert translated == "Translated Command Name"


@pytest.mark.asyncio
async def test_translate_command_description(translator_instance, mocker):
    # Correct return value for COMMAND description
    mocker.patch.object(Locale, "text", return_value="Translated Command Description")

    mock_context = MagicMock()
    mock_context.location = TranslationContextLocation.command_description
    mock_context.data.name = "test_cmd"  # Command name

    translated = await translator_instance.translate(
        string=locale_str("original"),
        locale=discord.Locale.american_english,
        context=mock_context,
    )

    # Assert correct key and language
    Locale.text.assert_called_once_with("commands.test_cmd.description", "en-us")
    assert translated == "Translated Command Description"


@pytest.mark.asyncio
async def test_translate_command_parameter_name(translator_instance, mocker):
    mocker.patch.object(Locale, "text", return_value="Translated Parameter Name")

    mock_context = MagicMock()
    mock_context.location = TranslationContextLocation.parameter_name
    mock_context.data.name = "param1"  # Parameter name
    mock_context.data.command.name = "test_cmd"  # Command name

    translated = await translator_instance.translate(
        string=locale_str("original"),
        locale=discord.Locale.american_english,
        context=mock_context,
    )

    # Correct assertion: Check positional argument for text, keyword for lang
    Locale.text.assert_called_once_with(
        "commands.test_cmd.params.param1.name", "en-us"  # Positional  # Keyword
    )
    assert translated == "Translated Parameter Name"


@pytest.mark.asyncio
async def test_translate_command_parameter_description(translator_instance, mocker):
    # Patch at the CLASS level, not instance level
    mocker.patch.object(
        Locale, "text", return_value="Translated Command Parameter Description"
    )

    mock_context = MagicMock()
    mock_context.location = TranslationContextLocation.parameter_description
    mock_context.data.name = "param1"  # Parameter name
    mock_context.data.command.name = "test_cmd"  # Command name

    translated = await translator_instance.translate(
        string=locale_str("original"),
        locale=discord.Locale.american_english,
        context=mock_context,
    )

    Locale.text.assert_called_once_with(
        "commands.test_cmd.params.param1.description", "en-us"
    )
    assert translated == "Translated Command Parameter Description"


@pytest.mark.asyncio
async def test_translate_command_bypass(translator_instance, mocker):
    mock_context = MagicMock()
    mock_context.location = None
    mock_context.data.name = "test_cmd"

    translated = await translator_instance.translate(
        string=locale_str("original"),
        locale=discord.Locale.american_english,
        context=mock_context,
    )

    assert str(translated) == "original"


@pytest.mark.asyncio
async def test_translate_fallback(translator_instance, mocker):
    # Patch to return None (no translation found)
    mocker.patch.object(Locale, "text", return_value=None)

    mock_context = MagicMock()
    mock_context.location = TranslationContextLocation.command_name
    mock_context.data.name = "test_cmd"

    original_string = locale_str("original")
    translated = await translator_instance.translate(
        string=original_string,
        locale=discord.Locale.american_english,
        context=mock_context,
    )

    assert translated == original_string  # Fallback to original
