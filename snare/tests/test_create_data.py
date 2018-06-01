import unittest
from unittest.mock import Mock
import asyncio
import argparse
import aiohttp
import shutil
import os
import json
from aiohttp.protocol import HttpVersion
from utils.asyncmock import AsyncMock
from snare import HttpRequestHandler
import snare
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
        snare.snare_uuid = ('9c10172f-7ce2-4fb4-b1c6-abc70141db56').encode('utf-8')
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.headers = {
            'Host': 'test_host', 'status': 200,
            'Cookie': 'sess_uuid=prev_test_uuid; test_cookie=test'
        }
        self.request = aiohttp.protocol.RawRequestMessage(
            method='POST', path='/', version=HttpVersion(major=1, minor=1), headers=self.headers,
            raw_headers=None, should_close=None, compression=None)
        self.response_status = "test_status"
        self.expected_data = {
            'method': 'POST', 'path': '/',
                              'headers': {'Host': 'test_host', 'status': 200,
                                          'Cookie': 'sess_uuid=prev_test_uuid; test_cookie=test'},
                              'uuid': '9c10172f-7ce2-4fb4-b1c6-abc70141db56',
                              'peer': {'ip': 'test_ip', 'port': 'test_port'},
                              'status': 'test_status',
                              'cookies': {'sess_uuid': 'prev_test_uuid', ' test_cookie': 'test'}
        }
        asyncio.BaseTransport = Mock()
        self.handler.transport = asyncio.BaseTransport()
        self.handler.transport.get_extra_info = Mock(return_value=['test_ip', 'test_port'])

    def test_create_data(self):
        self.data = self.handler.create_data(self.request, self.response_status)
        self.assertEquals(self.data, self.expected_data)

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
