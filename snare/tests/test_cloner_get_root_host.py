import asyncio
import sys
import unittest
from unittest import mock

import aiohttp
import yarl

from snare.cloner import BaseCloner
from snare.utils.asyncmock import AsyncMock


class TestClonerGetRootHost(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()

    def test_moved_root(self):
        self.root = "http://example.com"
        self.max_depth = sys.maxsize
        self.css_validate = False
        self.handler = BaseCloner(self.root, self.max_depth, self.css_validate)
        self.expected_moved_root = yarl.URL("http://www.example.com")

        p = mock.patch(
            "aiohttp.ClientSession.get",
            new=AsyncMock(
                return_value=aiohttp.ClientResponse(
                    url=yarl.URL("http://www.example.com"),
                    method="GET",
                    writer=None,
                    continue100=1,
                    timer=None,
                    request_info=None,
                    traces=None,
                    loop=self.loop,
                    session=None,
                )
            ),
        )
        p.start()

        async def test():
            if not self.handler:
                raise Exception("Error initializing Cloner!")
            await self.handler.get_root_host()

        self.loop.run_until_complete(test())

        if not self.handler:
            raise Exception("Error initializing Cloner!")

        self.assertEqual(self.handler.moved_root, self.expected_moved_root)
        p.stop()

    @mock.patch("aiohttp.ClientSession")
    def test_clienterror(self, session):
        self.root = "http://example.com"
        self.max_depth = sys.maxsize
        self.css_validate = False
        self.handler = BaseCloner(self.root, self.max_depth, self.css_validate)

        aiohttp.ClientSession = mock.Mock(side_effect=aiohttp.ClientError)

        async def test():
            if not self.handler:
                raise Exception("Error initializing Cloner!")
            await self.handler.get_root_host()

        with self.assertRaises(SystemExit):
            self.loop.run_until_complete(test())
