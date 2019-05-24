import unittest
from argparse import ArgumentTypeError
from snare.utils.snare_helpers import str_to_bool


class TestStrToBool(unittest.TestCase):

    def setUp(self):
        self.v = None

    def test_str_to_bool_true(self):
        self.v = 'true'
        assert str_to_bool(self.v) is True

    def test_str_to_bool_false(self):
        self.v = 'false'
        assert str_to_bool(self.v) is False

    def test_str_to_bool_error(self):
        self.v = 'twz'
        with self.assertRaises(ArgumentTypeError):
            str_to_bool(self.v)
