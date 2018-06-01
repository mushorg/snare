import unittest
from unittest.mock import Mock
import asyncio
import argparse
import aiohttp
import shutil
import yarl
import os
from utils.asyncmock import AsyncMock
from snare import HttpRequestHandler
from utils.page_path_generator import generate_unique_path


class TestGetDorks(unittest.TestCase):
    def setUp(self):
        self.meta = {}
        run_args = argparse.ArgumentParser()
        run_args.add_argument("--tanner")
        run_args.add_argument("--page-dir")
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.page_dir = self.main_page_path.rsplit('/')[-1]
        self.args = run_args.parse_args(['--page-dir', self.page_dir])
        self.dorks = dict(response={'dorks': "test_dorks"})
        self.loop = asyncio.new_event_loop()
        aiohttp.ClientSession.get = AsyncMock(
            return_value=aiohttp.ClientResponse(url=yarl.URL("http://www.example.com"), method="GET")
                                             )
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.handler.run_args.tanner = "tanner.mushmush.org"

    def test_get_dorks(self):
        aiohttp.ClientResponse.json = AsyncMock(return_value=dict(response={'dorks': "test_dorks"}))

        async def test():
            self.data = await self.handler.get_dorks()
        self.loop.run_until_complete(test())
        aiohttp.ClientSession.get.assert_called_with('http://tanner.mushmush.org:8090/dorks')

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
