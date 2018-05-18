import unittest
from unittest.mock import Mock
import asyncio
import argparse
import aiohttp
import shutil
import os
from utils.asyncmock import AsyncMock
from snare import HttpRequestHandler


class TestHandleError(unittest.TestCase):
    def setUp(self):
        self.meta = {}
        run_args = argparse.ArgumentParser()
        run_args.add_argument("--tanner")
        run_args.add_argument("--page-dir")
        if not os.path.exists("/opt/snare/pages/test"):
            self.path_exists = False
            os.makedirs("/opt/snare/pages/test")
        else:
            self.path_exists = True

        self.args = run_args.parse_args(['--page-dir', 'test'])
        self.loop = asyncio.new_event_loop()
        self.status = 500
        self.message = "test"
        self.payload = "test"
        self.exc = "[Errno 0] test"
        self.headers = "test"
        self.reason = "test"
        self.data = dict(
            method='GET',
            path='/',
            headers="test_headers",
            uuid="test_uuid",
            peer="test_peer",
            status="test_status",
            error=self.exc
        )
        aiohttp.server.ServerHttpProtocol.handle_error = Mock()
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.handler.create_data = Mock(return_value=self.data)
        self.handler.submit_data = AsyncMock()

    def test_create_error_data(self):

        async def test():
            await self.handler.handle_error(
                self.status, self.message, self.payload, self.exc, self.headers, self.reason)
        self.loop.run_until_complete(test())
        self.handler.create_data.assert_called_with(self.message, self.status)

    def test_submit_error_data(self):

        async def test():
            await self.handler.handle_error(
                self.status, self.message, self.payload, self.exc, self.headers, self.reason)
        self.loop.run_until_complete(test())
        self.handler.submit_data.assert_called_with(self.data)

    def test_handle_error_data(self):

        async def test():
            await self.handler.handle_error(
                self.status, self.message, self.payload, self.exc, self.headers, self.reason)
        self.loop.run_until_complete(test())
        aiohttp.server.ServerHttpProtocol.handle_error.assert_called_with(
            self.status, self.message, self.payload, self.exc, self.headers, self.reason)

    def tearDown(self):
        if not self.path_exists:
            shutil.rmtree("/opt/snare/pages/test")
