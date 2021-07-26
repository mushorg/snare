import asyncio
import os
import shutil
import sys
import unittest
from unittest.mock import patch

from snare.cloner import CloneRunner
from snare.utils.asyncmock import AsyncMock
from snare.utils.page_path_generator import generate_unique_path


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
        temp_runner = self.handler.runner
        self.handler.runner = None
        with self.assertRaises(Exception):
            self.loop.run_until_complete(self.handler.run())
        # set runner back to normal
        self.handler.runner = temp_runner

    def test_no_cloner_close(self):
        self.handler = CloneRunner(self.root, self.max_depth, self.css_validate, default_path="/tmp", headless=True)
        temp_runner = self.handler.runner
        self.handler.runner = None
        with self.assertRaises(Exception):
            self.loop.run_until_complete(self.handler.close())
        # set runner back to normal
        self.handler.runner = temp_runner

    def tearDown(self):
        shutil.rmtree(self.main_page_path)

        async def close():
            await self.handler.close()

        self.loop.run_until_complete(close())
        self.loop.close()
