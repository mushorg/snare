import unittest
import sys
from snare.cloner import Cloner
import shutil
import asyncio


class TestClonerRun(unittest.TestCase):
    def setUp(self):
        self.root = "http://example.com"
        self.max_depth = sys.maxsize
        self.css_validate = "false"
        self.handler = Cloner(self.root, self.max_depth, self.css_validate, default_path="/tmp")
        self.loop = asyncio.new_event_loop()

    def test_run(self):
        self.loop.run_until_complete(self.handler.run())
