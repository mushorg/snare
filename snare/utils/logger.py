import logging
import logging.handlers


class LevelFilter(logging.Filter):
    """Filters (lets through) all messages with level < LEVEL"""

    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno < self.level

    # "<" instead of "<=": since logger.setLevel is inclusive, this should be exclusive


class Logger:
    @staticmethod
    def create_logger(debug_filename, err_filename, logger_name):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s:%(name)s:%(funcName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # ERROR log to 'snare.err'
        error_log_handler = logging.handlers.RotatingFileHandler(
            err_filename, encoding="utf-8"
        )
        error_log_handler.setLevel(logging.ERROR)
        error_log_handler.setFormatter(formatter)
        logger.addHandler(error_log_handler)

        # DEBUG log to 'snare.log'
        debug_log_handler = logging.handlers.RotatingFileHandler(
            debug_filename, encoding="utf-8"
        )
        debug_log_handler.setLevel(logging.DEBUG)
        debug_log_handler.setFormatter(formatter)
        max_level_filter = LevelFilter(logging.ERROR)
        debug_log_handler.addFilter(max_level_filter)
        logger.addHandler(debug_log_handler)

        return logger

    @staticmethod
    def create_clone_logger(log_filename, logger_name):
        logger = logging.getLogger(logger_name)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s:%(name)s:%(funcName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        # logs to 'clone.err'
        debug_log_handler = logging.handlers.RotatingFileHandler(
            log_filename, encoding="utf-8"
        )
        debug_log_handler.setLevel(logging.DEBUG)
        debug_log_handler.setFormatter(formatter)
        logger.addHandler(debug_log_handler)
