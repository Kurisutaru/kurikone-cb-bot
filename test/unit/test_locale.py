import os
import tempfile
from contextvars import ContextVar
from unittest.mock import MagicMock, patch

import discord
import pytest
import yaml
from discord.app_commands import TranslationContextLocation, locale_str

from locales import Locale, DiscordTranslator, default_locale

current_guild_id = ContextVar("current_guild_id", default=None)


# Fixtures
@pytest.fixture
def mock_i18n_t(mocker):
    return mocker.patch("locales.i18n.t")


@pytest.fixture
def mock_load_everything(mocker):
    return mocker.patch("locales.i18n.load_everything")


@pytest.fixture
def locale_instance(mock_load_everything):
    Locale._instance = None
    return Locale()


@pytest.fixture
def translator_instance(locale_instance):
    return DiscordTranslator()


@pytest.fixture
def set_guild_context():
    token = current_guild_id.set(123)
    yield
    current_guild_id.reset(token)


@pytest.fixture
def mock_guild_locale():
    with patch.dict("locales.GUILD_LOCALE", {}, clear=True) as mock_dict:
        yield mock_dict


@pytest.fixture
def temp_translation_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create en-US.yaml
        en_us_content = {
            "en-US": {
                "ui": {"label": {"done_list": "Done List"}},
                "commands": {
                    "install": {
                        "name": "install",
                        "description": "This command will try to uninstall all channel related to the bots and removing data from database",
                    }
                },
                "message": {"not_found": "%{input} not found."},
            }
        }
        en_us_path = os.path.join(tmpdir, "en-US.yaml")
        with open(en_us_path, "w", encoding="utf-8") as f:
            yaml.dump(en_us_content, f, allow_unicode=True)
        # Create ja.yaml
        ja_content = {
            "ja": {
                "ui": {"label": {"done_list": "完了リスト"}},
                "commands": {
                    "install": {
                        "name": "インストール",
                        "description": "このコマンドは、ボットに関連するすべてのチャンネルをアンインストールし、データベースからデータを削除します",
                    }
                },
                "message": {"not_found": "%{input} が見つかりません。"},
            }
        }
        ja_path = os.path.join(tmpdir, "ja.yaml")
        with open(ja_path, "w", encoding="utf-8") as f:
            yaml.dump(ja_content, f, allow_unicode=True)
        # Debug: Verify files exist
        print(
            f"Created files: {en_us_path}={os.path.exists(en_us_path)}, {ja_path}={os.path.exists(ja_path)}"
        )
        yield tmpdir


# Locale Tests
@pytest.mark.parametrize("method_name", ["get_text", "t"])
@pytest.mark.parametrize("guild_locale", ["en-US", "ja"])
def test_locale_methods_with_guild_locale(
    mocker, mock_i18n_t, locale_instance, mock_guild_locale, method_name, guild_locale
):
    mock_guild_locale[123] = guild_locale
    expected = "Done List" if guild_locale == "en-US" else "完了リスト"
    mock_i18n_t.return_value = expected
    method = getattr(locale_instance, method_name)

    result = method(123, "ui.label.done_list")
    mock_i18n_t.assert_called_once_with(key="ui.label.done_list", locale=guild_locale)
    assert result == expected


def test_guild_locale_resolution(
    mocker, mock_i18n_t, locale_instance, mock_guild_locale
):
    mock_guild_locale[123] = "ja"
    mock_i18n_t.return_value = "完了リスト"
    result = locale_instance.get_text(123, "ui.label.done_list")
    mock_i18n_t.assert_called_once_with(key="ui.label.done_list", locale="ja")
    assert result == "完了リスト"


def test_get_text_with_default_locale(
    mocker, mock_i18n_t, locale_instance, mock_guild_locale
):
    mock_i18n_t.return_value = "Done List"
    result = locale_instance.get_text(456, "ui.label.done_list")
    mock_i18n_t.assert_called_once_with(key="ui.label.done_list", locale=default_locale)
    assert result == "Done List"


def test_text_with_default_locale(mocker, mock_i18n_t, locale_instance):
    mock_i18n_t.return_value = "Done List"
    result = locale_instance.text("ui.label.done_list", default_locale)
    mock_i18n_t.assert_called_once_with(key="ui.label.done_list", locale=default_locale)
    assert result == "Done List"


def test_nf_method(mocker, mock_i18n_t, locale_instance, mock_guild_locale):
    mock_guild_locale[123] = "en-US"
    mock_i18n_t.return_value = "test not found."
    result = locale_instance.nf(123, "test")
    mock_i18n_t.assert_called_once_with(
        key="message.not_found", locale="en-US", input="test"
    )
    assert result == "test not found."


@pytest.mark.parametrize(
    "method, args, key, expected",
    [
        ("get_text", (123, "ui.label.done_list"), "ui.label.done_list", "Done List"),
        ("t", (123, "ui.label.done_list"), "ui.label.done_list", "Done List"),
        (
            "text",
            ("ui.label.done_list", "invalid-locale"),
            "ui.label.done_list",
            "Done List",
        ),
        ("nf", (123, "Data"), "message.not_found", "Data not found"),
    ],
)
def test_locale_methods_invalid_locale_fallback(
    mocker, mock_i18n_t, locale_instance, mock_guild_locale, method, args, key, expected
):
    mock_guild_locale[123] = "invalid-locale"
    mock_i18n_t.side_effect = [KeyError("Invalid locale"), expected]
    method_func = getattr(locale_instance, method)
    result = method_func(*args)
    expected_calls = [
        mocker.call(
            key=key,
            locale="invalid-locale",
            input="Data" if method == "nf" else mocker.ANY,
        ),
        mocker.call(
            key=key,
            locale=default_locale,
            input="Data" if method == "nf" else mocker.ANY,
        ),
    ]
    # Remove input from expected calls for non-nf methods
    if method != "nf":
        expected_calls = [
            mocker.call(key=key, locale="invalid-locale"),
            mocker.call(key=key, locale=default_locale),
        ]
    assert (
        mock_i18n_t.call_args_list == expected_calls
    ), f"Expected {expected_calls}, got {mock_i18n_t.call_args_list}"
    assert result == expected
    mock_i18n_t.reset_mock()


def test_get_text_with_kwargs(mocker, mock_i18n_t, locale_instance, mock_guild_locale):
    mock_guild_locale[123] = "en-US"
    mock_i18n_t.return_value = "Alice not found."
    result = locale_instance.get_text(123, "message.not_found", input="Alice")
    mock_i18n_t.assert_called_once_with(
        key="message.not_found", locale="en-US", input="Alice"
    )
    assert result == "Alice not found."


def test_get_text_with_contextvars(
    mocker, mock_i18n_t, locale_instance, set_guild_context, mock_guild_locale
):
    mock_guild_locale[123] = "ja"
    mock_i18n_t.return_value = "完了リスト"
    result = locale_instance.get_text(current_guild_id.get(), "ui.label.done_list")
    mock_i18n_t.assert_called_once_with(key="ui.label.done_list", locale="ja")
    assert result == "完了リスト"


def test_i18n_load_standard_locales(temp_translation_files, mocker):
    print(f"Testing with temp dir: {temp_translation_files}")
    # Clear and set load_path
    import locales

    locales.i18n.load_path.clear()
    locale = Locale(load_path=temp_translation_files)
    result = locale.text("ui.label.done_list", lang="en-US")
    assert result == "Done List", f"Expected 'Done List', got {result}"
    result = locale.text("ui.label.done_list", lang="ja")
    assert result == "完了リスト", f"Expected '完了リスト', got {result}"


# DiscordTranslator Tests
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "discord_locale, expected_locale",
    [
        (discord.Locale.american_english, "en-US"),
        (discord.Locale.japanese, "ja"),
    ],
)
async def test_discord_translator_standard_locales(
    translator_instance, mocker, discord_locale, expected_locale
):
    mocker.patch.object(
        Locale,
        "text",
        return_value="install" if expected_locale == "en-US" else "インストール",
    )
    mock_context = MagicMock()
    mock_context.location = TranslationContextLocation.command_name
    mock_context.data.name = "install"

    translated = await translator_instance.translate(
        string=locale_str("original"),
        locale=discord_locale,
        context=mock_context,
    )
    Locale.text.assert_called_once_with("commands.install.name", expected_locale)
    assert translated == ("install" if expected_locale == "en-US" else "インストール")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "location, key_prefix, expected_key",
    [
        (TranslationContextLocation.command_name, "commands.install.name", "install"),
        (
            TranslationContextLocation.command_description,
            "commands.install.description",
            "This command will try to uninstall all channel related to the bots and removing data from database",
        ),
    ],
)
async def test_translate_contexts(
    translator_instance, mocker, location, key_prefix, expected_key
):
    mocker.patch.object(Locale, "text", return_value=expected_key)
    mock_context = MagicMock()
    mock_context.location = location
    mock_context.data.name = "install"

    translated = await translator_instance.translate(
        string=locale_str("original"),
        locale=discord.Locale.american_english,
        context=mock_context,
    )
    Locale.text.assert_called_once_with(key_prefix, "en-US")
    assert translated == expected_key


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "location, key_prefix, expected_key",
    [
        (
            TranslationContextLocation.parameter_name,
            "commands.install.params.param.name",
            "param",  # Translated parameter name
        ),
        (
            TranslationContextLocation.parameter_description,
            "commands.install.params.param.description",
            "Parameter description",  # Translated description
        ),
    ],
)
async def test_translate_contexts_param(
    translator_instance, mocker, location, key_prefix, expected_key
):
    mocker.patch.object(Locale, "text", return_value=expected_key)
    mock_context = MagicMock()
    mock_context.location = location
    mock_context.data = MagicMock()
    mock_context.data.name = "param"
    mock_context.data.command = MagicMock()
    mock_context.data.command.name = "install"
    translated = await translator_instance.translate(
        string=locale_str("original"),
        locale=discord.Locale.american_english,
        context=mock_context,
    )
    Locale.text.assert_called_once_with(key_prefix, "en-US")
    assert translated == expected_key


@pytest.mark.asyncio
async def test_translate_invalid_context_data(translator_instance, mocker):
    mocker.patch.object(Locale, "text", return_value=None)
    mock_context = MagicMock()
    mock_context.location = TranslationContextLocation.command_name
    mock_context.data = None

    original_string = locale_str("original")
    translated = await translator_instance.translate(
        string=original_string,
        locale=discord.Locale.american_english,
        context=mock_context,
    )
    assert translated == original_string


@pytest.mark.asyncio
async def test_translate_locale_text_exception(translator_instance, mocker):
    mocker.patch.object(Locale, "text", side_effect=KeyError("Invalid key"))
    mock_context = MagicMock()
    mock_context.location = TranslationContextLocation.command_name
    mock_context.data.name = "install"

    original_string = locale_str("original")
    translated = await translator_instance.translate(
        string=original_string,
        locale=discord.Locale.american_english,
        context=mock_context,
    )
    assert translated == original_string


@pytest.mark.asyncio
async def test_translate_command_bypass(translator_instance, mocker):
    mock_context = MagicMock()
    mock_context.location = None
    mock_context.data.name = "install"

    translated = await translator_instance.translate(
        string=locale_str("original"),
        locale=discord.Locale.american_english,
        context=mock_context,
    )
    assert str(translated) == "original"


@pytest.mark.asyncio
async def test_translate_fallback(translator_instance, mocker):
    mocker.patch.object(Locale, "text", return_value=None)
    mock_context = MagicMock()
    mock_context.location = TranslationContextLocation.command_name
    mock_context.data.name = "install"

    original_string = locale_str("original")
    translated = await translator_instance.translate(
        string=original_string,
        locale=discord.Locale.american_english,
        context=mock_context,
    )
    assert translated == original_string


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "location, data_setup",
    [
        (TranslationContextLocation.parameter_name, {"command": None}),
        (TranslationContextLocation.parameter_description, {}),
    ],
)
async def test_translate_missing_command_fallback(
    translator_instance, mocker, location, data_setup
):
    mocker.patch.object(Locale, "text", return_value="should_not_be_called")
    mock_context = MagicMock()
    mock_context.location = location
    mock_context.data = MagicMock(spec=["name", "command"])  # Restrict attributes
    mock_context.data.name = "param"
    # Explicitly apply data_setup
    if "command" in data_setup:
        mock_context.data.command = data_setup["command"]
    else:
        del mock_context.data.command
    original_string = locale_str("original")
    translated = await translator_instance.translate(
        string=original_string,
        locale=discord.Locale.american_english,
        context=mock_context,
    )
    Locale.text.assert_not_called()
    assert (
        translated == original_string
    ), f"Expected {original_string}, got {translated}"
