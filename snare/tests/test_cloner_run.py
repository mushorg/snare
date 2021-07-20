import unittest
import sys
from snare.cloner import CloneRunner
import shutil
import asyncio
import os
from unittest.mock import patch

from snare.utils.page_path_generator import generate_unique_path
from snare.utils.asyncmock import AsyncMock


class TestClonerRun(unittest.TestCase):
    def setUp(self):
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.root = "http://example.com"
        self.max_depth = sys.maxsize
        self.css_validate = False
        self.loop = asyncio.new_event_loop()
        self.content = "<html><body>Exampe website</body></html>"

    def test_simple_cloner_run(self):
        patches = []
        patches.append(patch("aiohttp.ClientResponse._headers", new={"Content-Type": "text/html"}))
        patches.append(patch("aiohttp.ClientResponse.read", new=AsyncMock(return_value=self.content)))
        for p in patches:
            p.start()
        self.handler = CloneRunner(self.root, self.max_depth, self.css_validate, default_path="/tmp")
        self.loop.run_until_complete(self.handler.run())
        for p in patches:
            p.stop()

    def test_headless_cloner_run(self):
        self.handler = CloneRunner(self.root, self.max_depth, self.css_validate, default_path="/tmp", headless=True)
        self.loop.run_until_complete(self.handler.run())

    def test_no_cloner_run(self):
        self.handler = CloneRunner(self.root, self.max_depth, self.css_validate, default_path="/tmp", headless=True)
        self.handler.runner = None
        with self.assertRaises(Exception):
            self.loop.run_until_complete(self.handler.run())

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
        self.handler.close()
        self.loop.close()
