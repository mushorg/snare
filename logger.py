import logging
import logging.handlers


class Logger:

    @staticmethod
    def create_logger(log_filename, logger_name, level_name):
        logger = logging.getLogger(logger_name)
        logger.setLevel(level_name)
        formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s:%(name)s:%(funcName)s: %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        # Log to 'snare.log'
        log_handler = logging.handlers.RotatingFileHandler(
            log_filename, encoding='utf-8')
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)

        return logger
