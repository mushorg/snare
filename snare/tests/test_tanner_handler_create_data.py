import unittest
from unittest.mock import Mock
import shutil
import os
import asyncio
import argparse
from yarl import URL
from aiohttp import HttpVersion
from aiohttp import web
from aiohttp.http_parser import RawRequestMessage
from snare.tanner_handler import TannerHandler
from snare.utils.page_path_generator import generate_unique_path


class TestCreateData(unittest.TestCase):
    def setUp(self):
        meta = {}
        run_args = argparse.ArgumentParser()
        run_args.add_argument("--tanner")
        run_args.add_argument("--page-dir")
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        page_dir = self.main_page_path.rsplit("/")[-1]
        args = run_args.parse_args(["--page-dir", page_dir])
        args_dict = vars(args)
        args_dict["full_page_path"] = self.main_page_path
        snare_uuid = "9c10172f-7ce2-4fb4-b1c6-abc70141db56".encode("utf-8")
        args.no_dorks = True
        self.handler = TannerHandler(args, meta, snare_uuid)
        headers = {
            "Host": "test_host",
            "status": 200,
            "Cookie": "sess_uuid=prev_test_uuid; test_cookie=test",
        }
        message = RawRequestMessage(
            method="POST",
            path="/",
            version=HttpVersion(major=1, minor=1),
            headers=headers,
            raw_headers=None,
            should_close=None,
            compression=None,
            upgrade=None,
            chunked=None,
            url=URL("http://test_url/"),
        )
        loop = asyncio.get_event_loop()
        RequestHandler = Mock()
        protocol = RequestHandler()
        self.request = web.Request(
            message=message,
            payload=None,
            protocol=protocol,
            payload_writer=None,
            task="POST",
            loop=loop,
        )
        self.request.transport.get_extra_info = Mock(return_value=(["test_ip", "test_port"]))
        self.response_status = "test_status"
        self.data = None
        self.expected_data = {
            "method": "POST",
            "path": "http://test_url/",
            "headers": {
                "Host": "test_host",
                "status": 200,
                "Cookie": "sess_uuid=prev_test_uuid; test_cookie=test",
            },
            "uuid": "9c10172f-7ce2-4fb4-b1c6-abc70141db56",
            "peer": {"ip": "test_ip", "port": "test_port"},
            "status": "test_status",
            "cookies": {"sess_uuid": "prev_test_uuid", " test_cookie": "test"},
        }

    def test_create_data(self):
        self.data = self.handler.create_data(self.request, self.response_status)
        self.assertEqual(self.data, self.expected_data)

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
