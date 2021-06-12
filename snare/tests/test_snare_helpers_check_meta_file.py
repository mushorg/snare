import unittest
from snare.utils.snare_helpers import check_meta_file


class TestMetaFile(unittest.TestCase):
    def setUp(self):
        self.correct_meta = {
            "/index.html": {
                "hash": "d1546d731a9f30cc80127d57142a482b",
                "headers": [{"Accept-Ranges": "bytes"}],
            }
        }
        self.incorrect_meta = {
            "/index.html": {
                "not_hash": "d1546d731a9f30cc80127d57142a482b",
                "headers": [{"Accept-Ranges": "bytes"}],
            }
        }

    def test_check_meta_file(self):
        self.assertTrue(check_meta_file(self.correct_meta))
        self.assertFalse(check_meta_file(self.incorrect_meta))
