import asyncio
import os
import shutil
import sys
import unittest

import aiohttp
from pyppeteer import launch
from pyppeteer.browser import Browser
from pyppeteer.errors import BrowserError
import yarl

from snare.cloner import BaseCloner, HeadlessCloner, SimpleCloner
from snare.utils.asyncmock import AsyncMock
from snare.utils.page_path_generator import generate_unique_path


class TestCloner(unittest.TestCase):
    def setUp(self):
        self.url = yarl.URL("http://example.com")
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.expected_new_url = yarl.URL("http://example.com")
        self.expected_err_url = yarl.URL("http://example.com/status_404")
        self.max_depth = sys.maxsize
        self.css_validate = False
        self.loop = asyncio.get_event_loop()
        self.base_handler = BaseCloner(self.url, self.max_depth, self.css_validate)
        self.simple_handler = SimpleCloner(self.url, self.max_depth, self.css_validate)
        self.headless_handler = HeadlessCloner(self.url, self.max_depth, self.css_validate)

    def test_basecloner_fetch_data(self):
        async def test():
            with self.assertRaises(NotImplementedError):
                await self.base_handler.fetch_data(None, self.url, 0, 0)

        self.loop.run_until_complete(test())

    def test_simplecloner_fetch_data(self):
        async def test():
            session = None
            try:
                session = aiohttp.ClientSession()
                await self.simple_handler.fetch_data(session, self.url, 0, 0)
            finally:
                if session:
                    await session.close()

        self.loop.run_until_complete(test())

    def test_headlesscloner_fetch_data(self):
        async def test():
            browser = None
            try:
                browser = await launch()
                await self.headless_handler.fetch_data(browser, self.url, 0, 0)
            finally:
                if browser:
                    await browser.close()

        self.loop.run_until_complete(test())

    def test_headlesscloner_fetch_data_exception(self):
        Browser.newPage = AsyncMock(side_effect=BrowserError("Failed to create new page"))

        async def test():
            await self.headless_handler.fetch_data(Browser, self.url, 0, 0)

        with self.assertLogs(level="ERROR") as log:
            self.loop.run_until_complete(test())
            self.assertIn("ERROR:snare.cloner:Failed to create new page", "".join(log.output))

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
