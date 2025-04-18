import logging
import os
import threading
from dataclasses import field
from datetime import datetime
from logging.handlers import RotatingFileHandler

import attr
import pytz
from attrs import define


@define
class KuriLogger:
    _instance = None
    _lock = None
    _timezone: datetime.tzinfo = field(default=pytz.UTC, init=False)

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(KuriLogger, cls).__new__(cls)
                    cls._instance.init(*args, **kwargs)
        return cls._instance

    def init(self, name='discord', log_file='discord.log', max_bytes=1024 * 1024 * 10,
             backup_count=5, file_level=logging.DEBUG, console_level=logging.INFO,
             timezone='UTC'):
        """
        Initialize the logger.

        Args:
        - name (str): The name of the logger.
        - log_file (str): The path to the log file.
        - max_bytes (int): The maximum size of the log file in bytes. Defaults to 10MB.
        - backup_count (int): The number of backup log files to keep. Defaults to 5.
        - file_level (int): The logging level for the file handler. Defaults to DEBUG.
        - console_level (int): The logging level for the console handler. Defaults to INFO.
        """
        # Set the timezone
        self._timezone = pytz.timezone(timezone)

        # Force log file to be in ./logs/ directory
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)  # Create if it doesn't exist
        full_log_path = os.path.join(log_dir, log_file)  # => logs/discord.log
        self.logger = logging.getLogger(name)
        self.logger.setLevel(min(file_level, console_level))  # Or set it to logging.DEBUG explicitly

        # Create a rotating file handler
        self.file_handler = RotatingFileHandler(full_log_path, maxBytes=max_bytes, backupCount=backup_count)
        self.file_handler.setLevel(file_level)

        # Create a console handler
        self.console_handler = logging.StreamHandler()
        self.console_handler.setLevel(console_level)

        # Create a formatter and attach it to the handlers
        self.file_formatter = TimezoneFormatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S %Z',
            tz=self._timezone
        )

        self.console_formatter = AnsiColorFormatter(
            '%(asctime)s [%(levelname)s] %(name)-20s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S %Z',
            tz=self._timezone
        )
        self.file_handler.setFormatter(self.file_formatter)
        self.console_handler.setFormatter(self.console_formatter)

        # Add the handlers to the logger
        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)

    file_handler: RotatingFileHandler = attr.field(init=False)
    logger: logging.Logger = attr.field(init=False)
    console_handler: logging.StreamHandler = attr.field(init=False)
    file_formatter: logging.Formatter = attr.field(init=False)
    console_formatter: logging.Formatter = attr.field(init=False)

    def debug(self, message, exc_info=None):
        """Log a debug message with optional exception info."""
        self.logger.debug(message, exc_info=exc_info)

    def info(self, message, exc_info=None):
        """Log an info message with optional exception info."""
        self.logger.info(message, exc_info=exc_info)

    def warning(self, message, exc_info=None):
        """Log a warning message with optional exception info."""
        self.logger.warning(message, exc_info=exc_info)

    def error(self, message, exc_info=None):
        """Log an error message with optional exception info."""
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message, exc_info=None):
        """Log a critical message with optional exception info."""
        self.logger.critical(message, exc_info=exc_info)


class TimezoneFormatter(logging.Formatter):
    """Custom formatter that supports timezones with pytz"""
    def __init__(self, fmt=None, datefmt=None, tz=pytz.UTC):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.tz = tz

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, self.tz)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

class AnsiColorFormatter(logging.Formatter):
    """Color formatter with timezone support using pytz"""
    def __init__(self, fmt=None, datefmt=None, tz=pytz.UTC):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.tz = tz

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, self.tz)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

    def format(self, record: logging.LogRecord):
        no_style = '\033[0m'
        bold = '\033[91m'
        grey = '\033[90m'
        yellow = '\033[93m'
        red = '\033[31m'
        red_light = '\033[91m'
        green = '\033[32m'
        start_style = {
            'DEBUG': grey,
            'INFO': green,
            'WARNING': yellow,
            'ERROR': red,
            'CRITICAL': red_light + bold,
        }.get(record.levelname, no_style)
        end_style = no_style
        return f'{start_style}{super().format(record)}{end_style}'