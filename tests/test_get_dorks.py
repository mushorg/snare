import unittest
from unittest.mock import Mock
import asyncio
import argparse
import aiohttp
import shutil
import yarl
import os
from snare import HttpRequestHandler


class AsyncMock(Mock):  # custom function defined to mock asyncio coroutines

    def __call__(self, *args, **kwargs):
        sup = super(AsyncMock, self)

        async def coro():
            return sup.__call__(*args, **kwargs)
        return coro()

    def __await__(self):
        return self().__await__()


class TestGetDorks(unittest.TestCase):
    def setUp(self):
        self.meta = {}
        run_args = argparse.ArgumentParser()
        run_args.add_argument("--tanner")
        run_args.add_argument("--page-dir")
        if not os.path.exists("/opt/snare/pages/test"):
            os.makedirs("/opt/snare/pages/test")
        self.args = run_args.parse_args(['--tanner', 'test'])
        self.args = run_args.parse_args(['--page-dir', 'test'])
        self.dorks = dict(response={'dorks': "test_dorks"})
        self.loop = asyncio.new_event_loop()
        aiohttp.ClientSession.get = AsyncMock(
            return_value=aiohttp.ClientResponse(url=yarl.URL("http://www.example.com"), method="GET")
                                             )

    def test_get_dorks(self):
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.handler.run_args.tanner = "tanner.mushmush.org"
        aiohttp.ClientResponse.json = AsyncMock(return_value=dict(response={'dorks': "test_dorks"}))

        async def test():
            self.data = await self.handler.get_dorks()
        self.loop.run_until_complete(test())
        aiohttp.ClientSession.get.assert_called_with('http://tanner.mushmush.org:8090/dorks')

    def test_return_dorks(self):
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.handler.run_args.tanner = "tanner.mushmush.org"
        aiohttp.ClientResponse.json = AsyncMock(return_value=self.dorks)

        async def test():
            self.data = await self.handler.get_dorks()
        self.loop.run_until_complete(test())
        self.assertEquals(self.data, self.dorks['response']['dorks'])

    def test_return_dorks_exception(self):
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.handler.run_args.tanner = "tanner.mushmush.org"
        aiohttp.ClientResponse.json = AsyncMock(side_effect=Exception())

        async def test():
            self.data = await self.handler.get_dorks()
        with self.assertRaises(Exception):
            self.loop.run_until_complete(test())

    def tearDown(self):
        shutil.rmtree("/opt/snare/pages/test")
