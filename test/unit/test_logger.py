import pytest
import re
from unittest.mock import patch
from datetime import datetime
import pytz
import logging
import os
from logger import KuriLogger, AnsiColorFormatter, TimezoneFormatter


@pytest.fixture
def logger(tmpdir, monkeypatch):
    monkeypatch.chdir(tmpdir)
    return KuriLogger(timezone="Asia/Tokyo")


def create_record(created):
    """
    Creates a LogRecord with the specified 'created' timestamp.
    """
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test_path",
        lineno=123,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.created = created
    return record


def test_log_directory_creation(logger):
    assert os.path.exists("logs")


def test_handlers_initialized(logger):
    assert len(logger.logger.handlers) == 2


@pytest.mark.parametrize(
    "level,level_name",
    [
        (lambda l: l.info, "INFO"),
        (lambda l: l.debug, "DEBUG"),
        (lambda l: l.warning, "WARNING"),
        (lambda l: l.error, "ERROR"),
        (lambda l: l.critical, "CRITICAL"),
    ],
)
def test_file_log_format(logger, level, level_name):
    level(logger)("Test message")
    log_file = os.path.join("logs", "discord.log")
    with open(log_file, "r") as f:
        content = f.read().strip()
    assert re.match(
        rf"\d{{4}}-\d{{2}}-\d{{2}} \d{{2}}:\d{{2}}:\d{{2}} JST \[{level_name}] discord\s+: Test message",
        content,
    )


@pytest.mark.parametrize(
    "input_name,expected_name",
    [
        ("discord.log.2024-03-01", "discord.2024-03-01.log"),
        ("discord.log", "discord.log"),
    ],
)
def test_namer_function(logger, input_name, expected_name):
    default_rotated_name = os.path.join("logs", input_name)
    new_name = logger.file_handler.namer(default_rotated_name)
    assert new_name == os.path.join("logs", expected_name)


def test_ansi_console_log(mocker, logger):
    mock_print = mocker.patch("logging.StreamHandler.emit")
    logger.info("Test message")
    args, _ = mock_print.call_args
    record = args[1]
    formatted = logger.console_formatter.format(record)
    assert "\033[32m" in formatted  # Green ANSI code for INFO
    assert "JST" in formatted  # Timezone abbreviation for Asia/Tokyo
    assert "Test message" in formatted
    assert "[INFO]" in formatted  # Log level
    assert "discord" in formatted  # Logger name


@pytest.mark.parametrize("timezone", ["UTC", "Asia/Tokyo"])
def test_ansi_format_time_without_datefmt_uses_isoformat(timezone):
    tz = pytz.timezone(timezone)
    formatter = AnsiColorFormatter(tz=tz)
    created_time = 1620000000
    record = create_record(created=created_time)
    result = formatter.formatTime(record, datefmt=None)
    expected = datetime.fromtimestamp(created_time, tz).isoformat()
    assert result == expected


@pytest.mark.parametrize(
    "timezone,datefmt",
    [
        ("UTC", "%Y-%m-%d %H:%M:%S"),
        ("Asia/Tokyo", "%Y-%m-%d %H:%M:%S %Z"),
    ],
)
def test_ansi_format_time_with_datefmt_uses_strftime(timezone, datefmt):
    tz = pytz.timezone(timezone)
    formatter = AnsiColorFormatter(tz=tz)
    created_time = 1620000000
    record = create_record(created=created_time)
    result = formatter.formatTime(record, datefmt=datefmt)
    expected = datetime.fromtimestamp(created_time, tz).strftime(datefmt)
    assert result == expected


@pytest.mark.parametrize("timezone", ["UTC", "Asia/Tokyo"])
def test_timezone_format_time_without_datefmt_uses_isoformat(timezone):
    tz = pytz.timezone(timezone)
    formatter = TimezoneFormatter(tz=tz)
    created_time = 1620000000
    record = create_record(created=created_time)
    result = formatter.formatTime(record, datefmt=None)
    expected = datetime.fromtimestamp(created_time, tz).isoformat()
    assert result == expected


@pytest.mark.parametrize(
    "timezone,datefmt",
    [
        ("UTC", "%Y-%m-%d %H:%M:%S"),
        ("Asia/Tokyo", "%Y-%m-%d %H:%M:%S %Z"),
    ],
)
def test_timezone_format_time_with_datefmt_uses_strftime(timezone, datefmt):
    tz = pytz.timezone(timezone)
    formatter = TimezoneFormatter(tz=tz)
    created_time = 1620000000
    record = create_record(created=created_time)
    result = formatter.formatTime(record, datefmt=datefmt)
    expected = datetime.fromtimestamp(created_time, tz).strftime(datefmt)
    assert result == expected


# Add missing tests (e.g., DI, async, rotation) as needed
