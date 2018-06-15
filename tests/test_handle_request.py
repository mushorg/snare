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


class TestHandleRequest(unittest.TestCase):
    def setUp(self):
        self.meta = {}
        run_args = argparse.ArgumentParser()
        run_args.add_argument("--tanner")
        run_args.add_argument("--page-dir")
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.page_dir = self.main_page_path.rsplit('/')[-1]
        self.args = run_args.parse_args(['--page-dir', self.page_dir])
        self.loop = asyncio.new_event_loop()
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.handler.run_args.server_header = "test_server"
        self.handler.run_args.slurp_enabled = True
        self.data = {
            'method': 'GET', 'path': '/',
            'headers': {
                'Host': 'test_host', 'status': 200
            },
            'cookies': {
                'sess_uuid': 'prev_test_uuid'
            }
        }
        self.content = '<html><body></body></html>'
        self.content_type = 'test_type'
        self.event_result = dict(response=dict(message=dict(detection={'type': 1}, sess_uuid="test_uuid")))
        self.request = aiohttp.protocol.RawRequestMessage(
            method='POST', path='/', version=HttpVersion(major=1, minor=1), headers=self.data['headers'],
            raw_headers=None, should_close=None, compression=None)
        self.handler.create_data = Mock(return_value=self.data)
        self.handler.submit_data = AsyncMock(return_value=self.event_result)
        self.handler.submit_slurp = AsyncMock()
        self.payload = aiohttp.streams.EmptyStreamReader()
        aiohttp.Response.add_header = Mock()
        aiohttp.Response.write = Mock()
        aiohttp.Response.send_headers = Mock()
        aiohttp.Response.write_eof = AsyncMock()
        aiohttp.streams.EmptyStreamReader.read = AsyncMock(return_value=b'con1=test1&con2=test2')
        self.handler.parse_tanner_response = AsyncMock(
            return_value=(self.content, self.content_type, self.data['headers'], self.data['headers']['status']))

    def test_create_request_data(self):

        async def test():
            await self.handler.handle_request(self.request, self.payload)
        self.loop.run_until_complete(test())
        self.handler.create_data.assert_called_with(self.request, 200)

    def test_submit_request_data(self):

        async def test():
            await self.handler.handle_request(self.request, self.payload)
        self.loop.run_until_complete(test())
        self.handler.submit_data.assert_called_with(self.data)

    def test_submit_request_slurp(self):

        async def test():
            await self.handler.handle_request(self.request, self.payload)
        self.loop.run_until_complete(test())
        self.handler.submit_slurp.assert_called_with(self.request.path)

    def test_parse_response(self):

        async def test():
            await self.handler.handle_request(self.request, self.payload)
        self.loop.run_until_complete(test())
        self.handler.parse_tanner_response.assert_called_with(self.request.path, {'type': 1})

    def test_handle_response(self):
        calls = [call('status', 200), call('Host', 'test_host'), call('Server', 'test_server'),
                 call('Set-Cookie', 'sess_uuid=test_uuid'), call('Content-Type', 'test_type'),
                 call('Content-Length', str(len(self.content)))]

        async def test():
            await self.handler.handle_request(self.request, self.payload)
        self.loop.run_until_complete(test())
        aiohttp.Response.add_header.assert_has_calls(calls)
        aiohttp.Response.send_headers.assert_called_with()
        aiohttp.Response.write.assert_called_with(self.content)
        aiohttp.Response.write_eof.assert_called_with()

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
