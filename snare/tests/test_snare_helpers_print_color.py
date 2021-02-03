import unittest
from snare.utils.snare_helpers import print_color


class TestPrintColor(unittest.TestCase):
    def test_print_color(self):
        self.assertIsNone(print_color('testing print_color()', 'INFO'))
        self.assertIsNone(print_color('testing print_color()', 'WRONG_MODE'))
