import unittest
from snare.utils.snare_helpers import parse_timeout


class TestParseTimeout(unittest.TestCase):

    def test_parse_timeout(self):
        assert parse_timeout('20H') == 72000
        assert parse_timeout('10M') == 600
        assert parse_timeout('1D') == 86400

        assert parse_timeout('24Y') == 86400  # Default 24H format is used.
