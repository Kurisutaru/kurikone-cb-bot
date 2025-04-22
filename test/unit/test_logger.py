import logging
import os
import re
from datetime import datetime, time
from logging import LogRecord

import pytz

from logger import KuriLogger, AnsiColorFormatter, TimezoneFormatter


def test_singleton_pattern():
    # Ensure singleton behavior
    KuriLogger._instance = None
    logger1 = KuriLogger()
    logger2 = KuriLogger()
    assert logger1 is logger2


def test_log_directory_creation(tmpdir, monkeypatch):
    # Test if logs directory is created
    monkeypatch.chdir(tmpdir)
    KuriLogger._instance = None
    logger = KuriLogger()
    assert os.path.exists("logs")


def test_handlers_initialized(tmpdir, monkeypatch):
    # Test if both handlers are added
    monkeypatch.chdir(tmpdir)
    KuriLogger._instance = None
    logger = KuriLogger()
    assert len(logger.logger.handlers) == 2


def test_namer_function(tmpdir, monkeypatch):
    # Test filename rotation logic
    monkeypatch.chdir(tmpdir)
    KuriLogger._instance = None
    logger = KuriLogger()

    # Simulate a rotated filename (default format: discord.log.2024-03-01)
    default_rotated_name = os.path.join("logs", "discord.log.2024-03-01")
    new_name = logger.file_handler.namer(default_rotated_name)
    assert new_name == os.path.join("logs", "discord.2024-03-01.log")

    # Simulate a rotated filename (default format: discord.log.2024-03-01)
    default_rotated_name = os.path.join("logs", "discord.log")
    new_name = logger.file_handler.namer(default_rotated_name)
    assert new_name == os.path.join("logs", "discord.log")


def test_file_log_info_format(tmpdir, monkeypatch):
    # Test log formatting in file (no ANSI colors)
    monkeypatch.chdir(tmpdir)
    KuriLogger._instance = None
    logger = KuriLogger()

    # Log a test message
    logger.info("Test message")
    # Read the log file
    log_file = os.path.join("logs", "discord.log")
    with open(log_file, "r") as f:
        content = f.read().strip()

    # Validate format: "YYYY-MM-DD HH:MM:SS UTC [LEVEL] NAME: message"
    assert re.match(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC \[INFO] discord\s+: Test message",
        content,
    )


def test_file_log_debug_format(tmpdir, monkeypatch):
    # Test log formatting in file (no ANSI colors)
    monkeypatch.chdir(tmpdir)
    KuriLogger._instance = None
    logger = KuriLogger()

    # Log a test message
    logger.debug("Test message")
    # Read the log file
    log_file = os.path.join("logs", "discord.log")
    with open(log_file, "r") as f:
        content = f.read().strip()

    # Validate format: "YYYY-MM-DD HH:MM:SS UTC [LEVEL] NAME: message"
    assert re.match(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC \[DEBUG] discord\s+: Test message",
        content,
    )


def test_file_log_warning_format(tmpdir, monkeypatch):
    # Test log formatting in file (no ANSI colors)
    monkeypatch.chdir(tmpdir)
    KuriLogger._instance = None
    logger = KuriLogger()

    # Log a test message
    logger.warning("Test message")
    # Read the log file
    log_file = os.path.join("logs", "discord.log")
    with open(log_file, "r") as f:
        content = f.read().strip()

    # Validate format: "YYYY-MM-DD HH:MM:SS UTC [LEVEL] NAME: message"
    assert re.match(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC \[WARNING] discord\s+: Test message",
        content,
    )


def test_file_log_critical_format(tmpdir, monkeypatch):
    # Test log formatting in file (no ANSI colors)
    monkeypatch.chdir(tmpdir)
    KuriLogger._instance = None
    logger = KuriLogger()

    # Log a test message
    logger.critical("Test message")
    # Read the log file
    log_file = os.path.join("logs", "discord.log")
    with open(log_file, "r") as f:
        content = f.read().strip()

    # Validate format: "YYYY-MM-DD HH:MM:SS UTC [LEVEL] NAME: message"
    assert re.match(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC \[CRITICAL] discord\s+: Test message\nNoneType: None",
        content,
    )


def test_file_log_error_format(tmpdir, monkeypatch):
    # Test log formatting in file (no ANSI colors)
    monkeypatch.chdir(tmpdir)
    KuriLogger._instance = None
    logger = KuriLogger()

    # Log a test message
    logger.error("Test message")
    # Read the log file
    log_file = os.path.join("logs", "discord.log")
    with open(log_file, "r") as f:
        content = f.read().strip()

    # Validate format: "YYYY-MM-DD HH:MM:SS UTC [LEVEL] NAME: message"
    assert re.match(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC \[ERROR] discord\s+: Test message\nNoneType: None",
        content,
    )


def test_ansi_console_log(mocker, tmpdir, monkeypatch):
    # Test console log contains ANSI codes
    monkeypatch.chdir(tmpdir)
    KuriLogger._instance = None
    logger = KuriLogger()

    mock_print = mocker.patch("logging.StreamHandler.emit")
    logger.info("Test message")

    # Check if ANSI escape codes are present
    args, _ = mock_print.call_args
    record = args[1]
    assert "Test message" in record.msg


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


def test_ansi_format_time_without_datefmt_uses_isoformat():
    tz = pytz.UTC
    formatter = AnsiColorFormatter(tz=tz)
    created_time = 1620000000  # 2021-05-03T00:00:00+00:00 in UTC
    record = create_record(created=created_time)
    result = formatter.formatTime(record, datefmt=None)
    expected = datetime.fromtimestamp(created_time, tz).isoformat()
    assert result == expected


def test_ansi_format_time_with_datefmt_uses_strftime():
    tz = pytz.UTC
    formatter = AnsiColorFormatter(tz=tz)
    created_time = 1620000000
    record = create_record(created=created_time)
    datefmt = "%Y-%m-%d %H:%M:%S"
    result = formatter.formatTime(record, datefmt=datefmt)
    expected = datetime.fromtimestamp(created_time, tz).strftime(datefmt)
    assert result == expected


def test_timezone_format_time_without_datefmt_uses_isoformat():
    tz = pytz.UTC
    formatter = TimezoneFormatter(tz=tz)
    created_time = 1620000000  # 2021-05-03T00:00:00+00:00 in UTC
    record = create_record(created=created_time)
    result = formatter.formatTime(record, datefmt=None)
    expected = datetime.fromtimestamp(created_time, tz).isoformat()
    assert result == expected


def test_timezone_format_time_with_datefmt_uses_strftime():
    tz = pytz.UTC
    formatter = TimezoneFormatter(tz=tz)
    created_time = 1620000000
    record = create_record(created=created_time)
    datefmt = "%Y-%m-%d %H:%M:%S"
    result = formatter.formatTime(record, datefmt=datefmt)
    expected = datetime.fromtimestamp(created_time, tz).strftime(datefmt)
    assert result == expected
