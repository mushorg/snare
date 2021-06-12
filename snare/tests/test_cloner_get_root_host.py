import unittest
from unittest import mock
import sys
from snare.cloner import Cloner
import shutil
from yarl import URL
import asyncio
import aiohttp
from snare.utils.asyncmock import AsyncMock


class TestClonerGetRootHost(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()

    def test_moved_root(self):
        self.root = "http://example.com"
        self.max_depth = sys.maxsize
        self.css_validate = "false"
        self.handler = Cloner(self.root, self.max_depth, self.css_validate)
        self.expected_moved_root = URL("http://www.example.com")

        async def test():
            await self.handler.get_root_host()

        self.loop.run_until_complete(test())

        self.assertEqual(self.handler.moved_root, self.expected_moved_root)

    @mock.patch("aiohttp.ClientSession")
    def test_clienterror(self, session):
        self.root = "http://example.com"
        self.max_depth = sys.maxsize
        self.css_validate = "false"
        self.handler = Cloner(self.root, self.max_depth, self.css_validate)

        aiohttp.ClientSession = mock.Mock(side_effect=aiohttp.ClientError)

        async def test():
            await self.handler.get_root_host()

        with self.assertRaises(SystemExit):
            self.loop.run_until_complete(test())
