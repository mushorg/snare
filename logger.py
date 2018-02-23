import logging
import logging.handlers

class LevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno < self.level

class Logger:
    @staticmethod
    def create_logger(log_filename, logger_name, level_name):
        logger = logging.getLogger(logger_name)
        logging_levels = {'CRITICAL': 50, 'ERROR': 40, 'WARNING': 30, 'INFO': 20, 'DEBUG': 10, 'NOTSET': 0}
        logger.setLevel(logging_levels[level_name])
        logger.propagate = False
        formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s:%(name)s:%(funcName)s: %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')


        # Log to 'snare.log'
        log_handler = logging.handlers.RotatingFileHandler(log_filename, encoding='utf-8')
        log_handler.setLevel(logging_levels[level_name])
        log_handler.setFormatter(formatter)
        max_level_filter = LevelFilter(logging.ERROR)
        log_handler.addFilter(max_level_filter)
        logger.addHandler(log_handler)

        return logger
