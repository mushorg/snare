import shutil
import sys
import unittest
from unittest.mock import patch

from snare.cloner import CloneRunner


class TestClonerInitialization(unittest.TestCase):
    def setUp(self):
        self.root = "http://example.com"
        self.max_depth = sys.maxsize
        self.css_validate = False
        self.target_path = None
        self.handler = None

    def test_clone_runner_init_error(self):
        p = patch("snare.cloner.SimpleCloner", return_value=None)
        p.start()

        with self.assertRaises(Exception):
            self.handler = CloneRunner(self.root, self.max_depth, self.css_validate, default_path="/tmp")

        p.stop()

    def tearDown(self):
        if self.target_path:
            shutil.rmtree(self.target_path)
