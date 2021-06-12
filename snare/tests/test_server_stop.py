import unittest
from unittest.mock import Mock
import asyncio
import argparse
import shutil
import os
from snare.server import HttpRequestHandler
from snare.utils.asyncmock import AsyncMock
from snare.utils.page_path_generator import generate_unique_path


class TestServerStop(unittest.TestCase):
    def setUp(self):
        meta = {
            "/status_404": {
                "hash": "bacfa45149ffbe8dbff34609bf56d748",
                "headers": [{"Content-Type": "text/html; charset=UTF-8"}],
            }
        }
        run_args = argparse.ArgumentParser()
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        args = run_args.parse_args([])
        args_dict = vars(args)
        args_dict["full_page_path"] = self.main_page_path
        uuid = "9c10172f-7ce2-4fb4-b1c6-abc70141db56".encode("utf-8")
        args.tanner = "tanner.mushmush.org"
        args.no_dorks = True
        args.host_ip = "127.0.0.1"
        args.port = "80"
        self.handler = HttpRequestHandler(meta, args, uuid)
        self.loop = asyncio.new_event_loop()

    def test_handler_stop(self):
        self.handler.runner = AsyncMock()

        async def test():
            await self.handler.stop()

        self.loop.run_until_complete(test())

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
