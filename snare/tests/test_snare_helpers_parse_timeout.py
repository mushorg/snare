import unittest
from snare.utils.snare_helpers import parse_timeout


class TestParseTimeout(unittest.TestCase):

    def test_parse_timeout(self):
        assert parse_timeout('20H') == 20 * 60 * 60
        assert parse_timeout('10M') == 10 * 60
        assert parse_timeout('1D') == 24 * 60 * 60

        # Default 24H format is used.
        assert parse_timeout('24Y') == 24 * 60 * 60
