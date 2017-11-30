import logging
import logging.handlers


class LevelFilter(logging.Filter):
    '''Filters (lets through) all messages with level < LEVEL'''
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno < self.level  # "<" instead of "<=": since logger.setLevel is inclusive, this should be exclusive


class Logger:
    @staticmethod
    def create_logger(debug_filename, logger_name):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s:%(name)s:%(funcName)s: %(message)s',
                                      datefmt='%Y-%m-%d %H:%M')

        # DEBUG log to '/opt/snare/snare.log'
        debug_log_handler = logging.handlers.RotatingFileHandler(debug_filename, encoding='utf-8')
        debug_log_handler.setLevel(logging.INFO)
        debug_log_handler.setFormatter(formatter)
        max_level_filter = LevelFilter(logging.ERROR)
        debug_log_handler.addFilter(max_level_filter)
        logger.addHandler(debug_log_handler)

        return logger
