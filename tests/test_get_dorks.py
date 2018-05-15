import unittest
import asyncio
import argparse
import aiohttp
import shutil
import os
from snare import HttpRequestHandler


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
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.data = []
        self.loop = asyncio.new_event_loop()

    def test_get_dorks(self):
        self.handler.run_args.tanner = "tanner.mushmush.org"
        try:
            async def test():
                self.data = await self.handler.get_dorks()
            self.loop.run_until_complete(test())
        except aiohttp.errors.ClientOSError:
            self.fail("Test failed")

    def tearDonw(self):
        shutil.rmtree("/opt/snare/pages/test")
