import unittest
from unittest.mock import Mock
import asyncio
import argparse
import shutil
import os
import aiohttp
from aiohttp.http_parser import RawRequestMessage
from aiohttp import HttpVersion
from aiohttp import web
from yarl import URL
from snare.server import HttpRequestHandler
from snare.utils.asyncmock import AsyncMock
from snare.utils.page_path_generator import generate_unique_path


class TestHandleRequest(unittest.TestCase):
    def setUp(self):
        meta = {}
        run_args = argparse.ArgumentParser()
        run_args.add_argument("--tanner")
        run_args.add_argument("--page-dir")
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.page_dir = self.main_page_path.rsplit('/')[-1]
        args = run_args.parse_args(['--page-dir', self.page_dir])
        args_dict = vars(args)
        args_dict['full_page_path'] = self.main_page_path
        uuid = '9c10172f-7ce2-4fb4-b1c6-abc70141db56'.encode('utf-8')
        args.tanner = 'tanner.mushmush.org'
        args.no_dorks = True
        args.server_header = "test_server"
        args.slurp_enabled = True
        self.handler = HttpRequestHandler(meta, args, uuid)
        self.data = {
            'method': 'GET', 'path': '/',
            'headers': {
                'Host': 'test_host', 'status': 200
            },
            'cookies': {
                'sess_uuid': 'prev_test_uuid'
            }
        }
        self.loop = asyncio.new_event_loop()
        self.content = '<html><body></body></html>'
        self.content_type = 'test_type'
        event_result = dict(
            response=dict(
                message=dict(
                    detection={
                        'type': 1},
                    sess_uuid="test_uuid")))
        RequestHandler = Mock()
        protocol = RequestHandler()
        message = RawRequestMessage(
            method='POST',
            path='/',
            version=HttpVersion(
                major=1,
                minor=1),
            headers=self.data['headers'],
            raw_headers=None,
            should_close=None,
            compression=None,
            upgrade=None,
            chunked=None,
            url=URL('http://test_url/'))
        self.request = web.Request(
            message=message,
            payload=None,
            protocol=protocol,
            payload_writer=None,
            task='POST',
            loop=self.loop)
        self.handler.tanner_handler.create_data = Mock(return_value=self.data)
        self.handler.tanner_handler.submit_data = AsyncMock(
            return_value=event_result)
        self.handler.submit_slurp = AsyncMock()
        web.Response.add_header = Mock()
        web.Response.write = Mock()
        web.Response.send_headers = Mock()
        web.Response.write_eof = AsyncMock()
        aiohttp.streams.EmptyStreamReader.read = AsyncMock(
            return_value=b'con1=test1&con2=test2')
        self.handler.tanner_handler.parse_tanner_response = AsyncMock(
            return_value=(
                self.content,
                self.content_type,
                self.data['headers'],
                self.data['headers']['status']))

    def test_create_request_data(self):
        async def test():
            await self.handler.handle_request(self.request)

        self.loop.run_until_complete(test())
        self.handler.tanner_handler.create_data.assert_called_with(
            self.request, 200)

    def test_submit_request_data(self):
        async def test():
            await self.handler.handle_request(self.request)

        self.loop.run_until_complete(test())
        self.handler.tanner_handler.submit_data.assert_called_with(self.data)

    def test_submit_request_slurp(self):
        async def test():
            await self.handler.handle_request(self.request)

        self.loop.run_until_complete(test())
        self.handler.submit_slurp.assert_called_with(self.request.path_qs)

    def test_parse_response(self):
        async def test():
            await self.handler.handle_request(self.request)

        self.loop.run_until_complete(test())
        self.handler.tanner_handler.parse_tanner_response.assert_called_with(
            self.request.path_qs, {'type': 1})

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
