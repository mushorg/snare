import unittest
import asyncio
import argparse
import shutil
import os
import json
import yarl
import aiohttp
from json import JSONDecodeError
from snare.utils.asyncmock import AsyncMock
from snare.tanner_handler import TannerHandler
from snare.utils.page_path_generator import generate_unique_path


class TestSubmitData(unittest.TestCase):
    def setUp(self):
        meta = {}
        run_args = argparse.ArgumentParser()
        run_args.add_argument("--tanner")
        run_args.add_argument("--page-dir")
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        page_dir = self.main_page_path.rsplit('/')[-1]
        args = run_args.parse_args(['--page-dir', page_dir])
        self.loop = asyncio.new_event_loop()
        self.data = {
            'method': 'GET',
            'path': '/',
            'headers': {
                'Host': 'test_host',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'test_agent',
                'Accept': 'text/html',
                'Accept-Encoding': 'test_encoding',
                'Accept-Language': 'test_lang',
                'Cookie': 'test_cookie'
                },
            'uuid': 'test_uuid',
            'peer': {
                'ip': '::1',
                'port': 80
            },
            'status': 200,
            'cookies': 'test_cookies',
            'sess_uuid': 'test_uuid'
        }
        aiohttp.ClientSession.post = AsyncMock(
            return_value=aiohttp.ClientResponse(
                url=yarl.URL("http://www.example.com"),
                method="GET",
                writer=None,
                continue100=1,
                timer=None,
                request_info=None,
                traces=None,
                loop=self.loop,
                session=None))
        uuid = "test_uuid"
        args.tanner = "tanner.mushmush.org"
        args.no_dorks = True
        self.handler = TannerHandler(args, meta, uuid)
        self.result = None

    def test_post_data(self):
        aiohttp.ClientResponse.json = AsyncMock(
            return_value=dict(
                detection={
                    'type': 1},
                sess_uuid="test_uuid"))

        async def test():
            self.result = await self.handler.submit_data(self.data)

        self.loop.run_until_complete(test())
        aiohttp.ClientSession.post.assert_called_with(
            'http://tanner.mushmush.org:8090/event', json=self.data, timeout=10.0
        )

    def test_event_result(self):
        aiohttp.ClientResponse.json = AsyncMock(
            return_value=dict(
                detection={
                    'type': 1},
                sess_uuid="test_uuid"))

        async def test():
            self.result = await self.handler.submit_data(self.data)

        self.loop.run_until_complete(test())
        self.assertEqual(
            self.result,
            dict(
                detection={
                    'type': 1},
                sess_uuid="test_uuid"))

    def test_submit_data_error(self):
        aiohttp.ClientResponse.json = AsyncMock(
            side_effect=JSONDecodeError('ERROR', '', 0))

        async def test():
            self.result = await self.handler.submit_data(self.data)

        with self.assertLogs(level='ERROR') as log:
            self.loop.run_until_complete(test())
            self.assertIn(
                'Error submitting data: ERROR: line 1 column 1 (char 0) {}'.format(
                    self.data), log.output[0])

    def test_event_result_exception(self):
        aiohttp.ClientResponse.json = AsyncMock(side_effect=Exception())

        async def test():
            self.result = await self.handler.submit_data(self.data)

        with self.assertRaises(Exception):
            self.loop.run_until_complete(test())

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
