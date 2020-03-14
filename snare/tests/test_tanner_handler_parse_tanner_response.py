import unittest
import asyncio
import argparse
import shutil
import os
import json
import multidict
from snare.utils.asyncmock import AsyncMock
from snare.utils.page_path_generator import generate_unique_path
from snare.tanner_handler import TannerHandler


class TestParseTannerResponse(unittest.TestCase):
    def setUp(self):
        run_args = argparse.ArgumentParser()
        run_args.add_argument("--tanner")
        run_args.add_argument("--page-dir")
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        page_dir = self.main_page_path.rsplit('/')[-1]
        meta_content = {"/index.html": {"hash": "hash_name", "headers": [{"Content-Type": "text/html"}]}}
        self.page_content = "<html><body></body></html>"
        self.headers = multidict.CIMultiDict([("Content-Type", "text/html")])
        self.status_code = 200
        self.content_type = "text/html"
        with open(os.path.join(self.main_page_path, "hash_name"), 'w') as f:
            f.write(self.page_content)
        with open(os.path.join(self.main_page_path, "meta.json"), 'w') as f:
            json.dump(meta_content, f)
        self.args = run_args.parse_args(['--page-dir', page_dir])
        self.args.index_page = '/index.html'
        self.args.no_dorks = True
        self.args.tanner = "tanner.mushmush.org"
        self.uuid = "test_uuid"
        self.handler = TannerHandler(self.args, meta_content, self.uuid)
        self.requested_name = '/'
        self.loop = asyncio.get_event_loop()
        self.handler.html_handler.handle_content = AsyncMock(
            return_value=self.page_content)
        self.res1 = None
        self.res2 = None
        self.res3 = None
        self.detection = None
        self.expected_content = None
        self.call_content = None

    def test_parse_type_one(self):
        self.detection = {"type": 1}

        async def test():
            (self.res1, self.res2, self.res3) = \
                await self.handler.parse_tanner_response(
                    self.requested_name, self.detection)

        self.loop.run_until_complete(test())
        real_result = [self.res1, self.res2, self.res3]
        expected_result = [self.page_content, self.headers, self.status_code]
        self.assertCountEqual(real_result, expected_result)

    def test_parse_type_one_query(self):
        self.requested_name = '/?'
        self.detection = {"type": 1}

        async def test():
            (self.res1, self.res2, self.res3) = \
                await self.handler.parse_tanner_response(
                    self.requested_name, self.detection)

        self.loop.run_until_complete(test())
        real_result = [self.res1, self.res2, self.res3]
        expected_result = [self.page_content, self.headers, self.status_code]
        self.assertCountEqual(real_result, expected_result)

    def test_parse_type_one_error(self):
        self.requested_name = 'something/'
        self.detection = {"type": 1}
        self.expected_content = None
        self.headers = multidict.CIMultiDict()
        self.status_code = 404

        async def test():
            (self.res1, self.res2, self.res3) = \
                await self.handler.parse_tanner_response(
                    self.requested_name, self.detection)

        self.loop.run_until_complete(test())
        real_result = [self.res1, self.res2, self.res3]
        expected_result = [self.expected_content, self.headers, self.status_code]
        self.assertCountEqual(real_result, expected_result)

    def test_parse_type_two(self):
        self.detection = {
            "type": 2,
            "payload": {
                "page": "/index.html",
                "value": "test",
            },
        }
        self.expected_content = b'<html><body><div>test</div></body></html>'

        async def test():
            (self.res1, self.res2, self.res3) = \
                await self.handler.parse_tanner_response(
                    self.requested_name, self.detection)

        self.loop.run_until_complete(test())
        real_result = [self.res1, self.res2, self.res3]
        expected_result = [self.expected_content, self.headers, self.status_code]
        self.assertCountEqual(real_result, expected_result)

    def test_parse_type_two_with_headers(self):
        self.detection = {
            "type": 2,
            "payload": {
                "page": "",
                "value": "test.png",
                "headers": {
                    "content-type": "multipart/form-data",
                },
            },
        }
        self.expected_content = b'test.png'
        self.content_type = 'image/png'
        self.headers = multidict.CIMultiDict([("Content-Type", "multipart/form-data")])

        async def test():
            (self.res1, self.res2, self.res3) = \
                await self.handler.parse_tanner_response(
                    self.requested_name, self.detection)

        self.loop.run_until_complete(test())
        real_result = [self.res1, self.res2, self.res3]
        expected_result = [self.expected_content, self.headers, self.status_code]

        self.assertCountEqual(real_result, expected_result)

    def test_parse_type_two_error(self):
        self.detection = {
            "type": 2,
            "payload": {
                "page": "/something",
                "value": "test",
            },
        }
        self.expected_content = b'<html><body><div>test</div></body></html>'
        self.content_type = r'text/html'

        async def test():
            (self.res1, self.res2, self.res3) = \
                await self.handler.parse_tanner_response(
                    self.requested_name, self.detection)

        self.loop.run_until_complete(test())
        real_result = [self.res1, self.res2, self.res3]
        expected_result = [self.expected_content, self.headers, self.status_code]
        self.assertCountEqual(real_result, expected_result)

    def test_parse_type_three(self):
        self.detection = {
            "type": 3,
            "payload": {
                "page": "/index.html",
                "value": "test",
                "status_code": 200,
            },
        }
        self.expected_content = None
        self.headers = multidict.CIMultiDict()

        async def test():
            (self.res1, self.res2, self.res3) = \
                await self.handler.parse_tanner_response(
                    self.requested_name, self.detection)

        self.loop.run_until_complete(test())
        real_result = [self.res1, self.res2, self.res3]
        expected_result = [self.expected_content, self.headers, self.status_code]
        self.assertCountEqual(real_result, expected_result)

    def test_call_handle_html(self):
        self.detection = {"type": 1}
        self.call_content = b'<html><body></body></html>'
        self.expected_content = self.page_content

        async def test():
            (self.res1, self.res2, self.res3) = \
                await self.handler.parse_tanner_response(
                    self.requested_name, self.detection)

        self.loop.run_until_complete(test())
        self.handler.html_handler.handle_content.assert_called_with(
            self.call_content)

    def test_parse_exception(self):
        self.detection = {}
        self.expected_content = self.page_content

        async def test():
            (self.res1, self.res2, self.res3) = \
                await self.handler.parse_tanner_response(
                    self.requested_name, self.detection)

        with self.assertRaises(KeyError):
            self.loop.run_until_complete(test())

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
