import unittest
from unittest.mock import Mock
from unittest.mock import call
import asyncio
import argparse
import aiohttp
import shutil
import os
import json
import yarl
from aiohttp.protocol import HttpVersion
from utils.asyncmock import AsyncMock
from snare import HttpRequestHandler
from utils.page_path_generator import generate_unique_path
from urllib.parse import unquote


class TestParseTannerResponse(unittest.TestCase):
    def setUp(self):
        run_args = argparse.ArgumentParser()
        run_args.add_argument("--tanner")
        run_args.add_argument("--page-dir")
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.page_dir = self.main_page_path.rsplit('/')[-1]
        self.meta_content = {"/index.html": {"hash": "hash_name", "content_type": "text/html"}}
        self.page_content = "<html><body></body></html>"
        self.content_type = "text/html"
        with open(os.path.join(self.main_page_path, "hash_name"), 'w') as f:
            f.write(self.page_content)
        with open(os.path.join(self.main_page_path, "meta.json"), 'w') as f:
            json.dump(self.meta_content, f)
        self.args = run_args.parse_args(['--page-dir', self.page_dir])
        self.requested_name = '/'
        self.loop = asyncio.new_event_loop()
        self.handler = HttpRequestHandler(self.meta_content, self.args)
        self.handler.run_args.index_page = '/index.html'
        self.handler.handle_html_content = AsyncMock(return_value=self.page_content)

    def test_parse_type_one(self):
        self.detection = {"type": 1}
        self.call_content = b'<html><body></body></html>'
        self.expected_content = self.page_content

        async def test():
            (self.res1, self.res2,
             self.res3, self.res4) = await self.handler.parse_tanner_response(self.requested_name, self.detection)
        self.loop.run_until_complete(test())
        real_result = [self.res1, self.res2, self.res3, self.res4]
        expected_result = [self.page_content, self.content_type, {}, 200]
        self.assertCountEqual(real_result, expected_result)

    def test_parse_type_two(self):
        self.detection = {
            "type": 2,
            "payload": {
                "page": "/index.html",
                "value": "test"
            }
        }
        self.expected_content = b'<html><body><div>test</div></body></html>'

        async def test():
            (self.res1, self.res2,
             self.res3, self.res4) = await self.handler.parse_tanner_response(self.requested_name, self.detection)
        self.loop.run_until_complete(test())
        real_result = [self.res1, self.res2, self.res3, self.res4]
        expected_result = [self.expected_content, self.content_type, {}, 200]
        self.assertCountEqual(real_result, expected_result)

    def test_parse_type_three(self):
        self.detection = {
            "type": 3,
            "payload": {
                "page": "/index.html",
                "value": "test",
                "status_code": 200
            }
        }
        self.expected_content = None

        async def test():
            (self.res1, self.res2,
             self.res3, self.res4) = await self.handler.parse_tanner_response(self.requested_name, self.detection)
        self.loop.run_until_complete(test())
        real_result = [self.res1, self.res2, self.res3, self.res4]
        expected_result = [self.expected_content, None, {}, 200]
        self.assertCountEqual(real_result, expected_result)

    def test_call_handle_html(self):
        self.detection = {"type": 1}
        self.call_content = b'<html><body></body></html>'
        self.expected_content = self.page_content

        async def test():
            (self.res1, self.res2,
             self.res3, self.res4) = await self.handler.parse_tanner_response(self.requested_name, self.detection)
        self.loop.run_until_complete(test())
        self.handler.handle_html_content.assert_called_with(self.call_content)

    def test_parse_exception(self):
        self.detection = {}
        self.call_content = b'<html><body></body></html>'
        self.expected_content = self.page_content

        async def test():
            (self.res1, self.res2,
             self.res3, self.res4) = await self.handler.parse_tanner_response(self.requested_name, self.detection)
        with self.assertRaises(KeyError):
            self.loop.run_until_complete(test())

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
