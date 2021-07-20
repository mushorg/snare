import logging
import os
import unittest

from snare.utils.logger import LevelFilter, Logger


class TestLogger(unittest.TestCase):
    def setUp(self):
        self.cloner_log_file = "/tmp/cloner.log"
        self.snare_log_file = "/tmp/snare.log"
        self.snare_err_log_file = "/tmp/snare.err"
        self.record_dict = {"levelno": logging.INFO}
        self.logger = Logger.create_logger(self.snare_log_file, self.snare_err_log_file, __name__)

    def test_create_clone_logger(self):
        self.assertIsNone(Logger.create_clone_logger(self.cloner_log_file, __name__))

    def test_create_logger(self):
        self.assertIsInstance(self.logger, logging.Logger)

    def test_filter(self):
        self.assertTrue(LevelFilter(logging.ERROR).filter(logging.makeLogRecord(self.record_dict)))

    def tearDown(self):
        try:
            os.remove(self.cloner_log_file)
            os.remove(self.snare_log_file)
            os.remove(self.snare_err_log_file)
        except FileNotFoundError:
            pass
