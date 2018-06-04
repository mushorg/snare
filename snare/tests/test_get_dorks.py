import unittest
import asyncio
import shutil
import os
import yarl
import aiohttp
from snare.utils.asyncmock import AsyncMock
from snare.html_handler import HtmlHandler
from snare.utils.page_path_generator import generate_unique_path


class TestGetDorks(unittest.TestCase):
    def setUp(self):
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.dorks = dict(response={'dorks': "test_dorks"})
        self.loop = asyncio.new_event_loop()
        aiohttp.ClientSession.get = AsyncMock(
            return_value=aiohttp.ClientResponse(
                url=yarl.URL("http://www.example.com"), method="GET", writer=None, continue100=1,
                timer=None, request_info=None, auto_decompress=None, traces=None, loop=self.loop,
                session=None
            )
                                              )
        no_dorks = True
        tanner = "tanner.mushmush.org"
        self.handler = HtmlHandler(no_dorks, tanner)
        self.data = None

    def test_get_dorks(self):
        aiohttp.ClientResponse.json = AsyncMock(return_value=dict(response={'dorks': "test_dorks"}))

        async def test():
            self.data = await self.handler.get_dorks()
        self.loop.run_until_complete(test())
        aiohttp.ClientSession.get.assert_called_with('http://tanner.mushmush.org:8090/dorks', timeout=10.0)

    def test_return_dorks(self):
        aiohttp.ClientResponse.json = AsyncMock(return_value=self.dorks)

        async def test():
            self.data = await self.handler.get_dorks()
        self.loop.run_until_complete(test())
        self.assertEquals(self.data, self.dorks['response']['dorks'])

    def test_return_dorks_exception(self):
        aiohttp.ClientResponse.json = AsyncMock(side_effect=Exception())

        async def test():
            self.data = await self.handler.get_dorks()
        with self.assertRaises(Exception):
            self.loop.run_until_complete(test())

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
