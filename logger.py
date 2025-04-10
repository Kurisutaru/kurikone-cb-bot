import logging
import traceback
from logging.handlers import RotatingFileHandler
import threading
import attr
from attrs import define


@define
class KuriLogger:
    _instance = None
    _lock = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(KuriLogger, cls).__new__(cls)
                    cls._instance.init(*args, **kwargs)
        return cls._instance

    def init(self, name='discord', log_file='discord.log', max_bytes=1024 * 1024 * 10, backup_count=5,
             file_level=logging.DEBUG, console_level=logging.INFO):
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
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Create a rotating file handler
        self.file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        self.file_handler.setLevel(file_level)

        # Create a console handler
        self.console_handler = logging.StreamHandler()
        self.console_handler.setLevel(console_level)

        # Create a formatter and attach it to the handlers
        self.file_formatter = logging.Formatter('%(asctime)s [%(threadName)s] [%(levelname)s] %(name): %(message)s',
                                           datefmt='%Y-%m-%d %H:%M:%S')
        self.console_formatter = logging.Formatter('%(asctime)s [%(threadName)s] [%(levelname)s] %(name)-20s: %(message)s',
                                           datefmt='%Y-%m-%d %H:%M:%S')
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

    def debug(self, message):
        """Log a debug message."""
        self.logger.debug(message)

    def info(self, message):
        """Log an info message."""
        self.logger.info(message)

    def warning(self, message):
        """Log a warning message."""
        self.logger.warning(message)

    def error(self, message):
        """Log an error message."""
        self.logger.error(message)
        self.logger.error(traceback.print_exc())

    def critical(self, message):
        """Log a critical message."""
        self.logger.critical(message)
