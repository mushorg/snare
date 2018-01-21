import logging
import logging.handlers
from time import gmtime


class LevelFilter(logging.Filter):
    '''Filters (lets through) all messages with level < LEVEL'''
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno < self.level  # "<" instead of "<=": since logger.setLevel is inclusive, this should be exclusive


class Logger:
    @staticmethod
    def create_logger(debug_filename, logger_name, level_name):
        logger = logging.getLogger(logger_name)
        level_dict = {'CRITICAL': 50, 'ERROR': 40, 'WARNING': 30, 'INFO': 20, 'DEBUG': 10, 'NOTSET': 0}
        logger.setLevel(level_dict[level_name])
        logger.propagate = False
        formatter = logging.Formatter(fmt='%(hostIP)s - %(user)s [%(time)s]%(message)s\"%(req)s\" %(stat)d %(content_length)s')

        # Log to '/opt/snare/snare.log'
        debug_log_handler = logging.handlers.RotatingFileHandler(debug_filename, encoding='utf-8')
        debug_log_handler.setLevel(level_dict[level_name])
        debug_log_handler.setFormatter(formatter)
        max_level_filter = LevelFilter(logging.ERROR)
        debug_log_handler.addFilter(max_level_filter)
        logger.addHandler(debug_log_handler)

        return logger
