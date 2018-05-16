import unittest
from unittest.mock import Mock
import asyncio
import argparse
import aiohttp
import shutil
import os
import json
import yarl
from snare import HttpRequestHandler


class AsyncMock(Mock):  # custom function defined to mock asyncio coroutines

    def __call__(self, *args, **kwargs):
        sup = super(AsyncMock, self)

        async def coro():
            return sup.__call__(*args, **kwargs)
        return coro()

    def __await__(self):
        return self().__await__()


class TestSubmitData(unittest.TestCase):
    def setUp(self):
        self.meta = {}
        run_args = argparse.ArgumentParser()
        run_args.add_argument("--tanner")
        run_args.add_argument("--page-dir")
        if not os.path.exists("/opt/snare/pages/test"):
            os.makedirs("/opt/snare/pages/test")
        self.args = run_args.parse_args(['--tanner', 'test'])
        self.args = run_args.parse_args(['--page-dir', 'test'])
        self.loop = asyncio.new_event_loop()
        self.data = {
            'method': 'GET', 'path': '/',
            'headers': {
                'Host': 'test_host', 'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1', 'User-Agent': 'test_agent', 'Accept': 'text/html',
                'Accept-Encoding': 'test_encoding', 'Accept-Language': 'test_lang', 'Cookie': 'test_cookie',
                'uuid': 'test_uuid', 'peer': {'ip': '::1', 'port': 80}, 'status': 200,
                'cookies': 'test_cookies', ' sess_uuid': 'test_uuid'
            }
        }
        aiohttp.ClientSession.post = AsyncMock(
            return_value=aiohttp.ClientResponse(url=yarl.URL("http://www.example.com"), method="GET")
                                              )

    def test_post_data(self):
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.handler.run_args.tanner = "tanner.mushmush.org"
        aiohttp.ClientResponse.json = AsyncMock(return_value=dict(detection={'type': 1}, sess_uuid="test_uuid"))

        async def test():
            self.result = await self.handler.submit_data(self.data)
        self.loop.run_until_complete(test())
        aiohttp.ClientSession.post.assert_called_with(
            'http://tanner.mushmush.org:8090/event', data=json.dumps(self.data)
        )

    def test_event_result(self):
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.handler.run_args.tanner = "tanner.mushmush.org"
        aiohttp.ClientResponse.json = AsyncMock(return_value=dict(detection={'type': 1}, sess_uuid="test_uuid"))

        async def test():
            self.result = await self.handler.submit_data(self.data)
        self.loop.run_until_complete(test())
        self.assertEquals(self.result, dict(detection={'type': 1}, sess_uuid="test_uuid"))

    def test_event_result_exception(self):
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.handler.run_args.tanner = "tanner.mushmush.org"
        aiohttp.ClientResponse.json = AsyncMock(side_effect=Exception())

        async def test():
            self.result = await self.handler.submit_data(self.data)
        with self.assertRaises(Exception):
            self.loop.run_until_complete(test())

    def tearDown(self):
        shutil.rmtree("/opt/snare/pages/test")
