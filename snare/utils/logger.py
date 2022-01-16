import logging
import logging.handlers


class LevelFilter(logging.Filter):
    """Filters (lets through) all messages with level < LEVEL"""

    def __init__(self, level: int) -> None:
        """Initialize level filter with level

        :param level: Log level
        :type level: int
        """
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter record by log level

        :param record: Log record
        :type record: logging.LogRecord
        :return: True if record's level is lesser than the set level
        :rtype: bool
        """
        # "<" instead of "<=": since logger.setLevel is inclusive, this should be exclusive
        return record.levelno < self.level


class Logger:
    """Modify built-in logger's format and handlers for Snare and Cloner"""

    @staticmethod
    def create_logger(debug_filename: str, err_filename: str, logger_name: str) -> logging.Logger:
        """Create logger with debugging and error level handlers for Snare

        :param debug_filename: Debug log filename
        :type debug_filename: str
        :param err_filename: Error log filename
        :type err_filename: str
        :param logger_name: Logger name
        :type logger_name: str
        :return: Logger with handlers and format set
        :rtype: logging.Logger
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s:%(name)s:%(funcName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # ERROR log to 'snare.err'
        error_log_handler = logging.handlers.RotatingFileHandler(err_filename, encoding="utf-8")
        error_log_handler.setLevel(logging.ERROR)
        error_log_handler.setFormatter(formatter)
        logger.addHandler(error_log_handler)

        # DEBUG log to 'snare.log'
        debug_log_handler = logging.handlers.RotatingFileHandler(debug_filename, encoding="utf-8")
        debug_log_handler.setLevel(logging.DEBUG)
        debug_log_handler.setFormatter(formatter)
        max_level_filter = LevelFilter(logging.ERROR)
        debug_log_handler.addFilter(max_level_filter)
        logger.addHandler(debug_log_handler)

        return logger

    @staticmethod
    def create_clone_logger(log_filename: str, logger_name: str) -> None:
        """Create logger for Cloner

        :param log_filename: Log filename
        :type log_filename: str
        :param logger_name: Logger name
        :type logger_name: str
        """
        logger = logging.getLogger(logger_name)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s:%(name)s:%(funcName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        # logs to 'clone.err'
        debug_log_handler = logging.handlers.RotatingFileHandler(log_filename, encoding="utf-8")
        debug_log_handler.setLevel(logging.DEBUG)
        debug_log_handler.setFormatter(formatter)
        logger.addHandler(debug_log_handler)
