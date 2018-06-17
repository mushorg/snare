import unittest
from unittest.mock import Mock
import asyncio
import argparse
import aiohttp
import shutil
import os
import yarl
from bs4 import BeautifulSoup
from utils.asyncmock import AsyncMock
from snare import HttpRequestHandler
from utils.page_path_generator import generate_unique_path


class TestHandleHtmlContent(unittest.TestCase):
    def setUp(self):
        self.meta = {}
        run_args = argparse.ArgumentParser()
        run_args.add_argument("--tanner")
        run_args.add_argument("--page-dir")
        run_args.add_argument("--no-dorks")
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.page_dir = self.main_page_path.rsplit('/')[-1]
        self.content = '''
                          <html>
                                <body>
                                <p style="color:red;">A paragraph to be tested</p>
                                </body>
                          </html>
                       '''
        self.expected_content = '<html>\n <body>\n  <p style="color: red">\n'
        self.expected_content += '   <a href="test_dork1" style="color:red;text-decoration:none;cursor:text;">\n'
        self.expected_content += '    A\n   </a>\n   paragraph to be tested\n  </p>\n </body>\n</html>\n'
        self.no_dorks_content = '<html>\n <body>\n  <p style="color:red;">\n   A paragraph to be tested\n'
        self.no_dorks_content += '  </p>\n </body>\n</html>\n'
        self.args = run_args.parse_args(['--page-dir', self.page_dir])
        self.loop = asyncio.new_event_loop()
        self.handler = HttpRequestHandler(self.meta, self.args)
        self.handler.dir = self.main_page_path

    def test_handle_content(self):
        self.handler.run_args.no_dorks = False
        self.handler.get_dorks = AsyncMock(return_value=["test_dork1"])

        async def test():
            self.return_content = await self.handler.handle_html_content(self.content)
        self.loop.run_until_complete(test())
        soup = BeautifulSoup(self.return_content, "html.parser")
        self.return_content = soup.decode("utf-8")
        self.assertEquals(self.return_content, self.expected_content)

    def test_handle_content_no_dorks(self):
        self.handler.run_args.no_dorks = True

        async def test():
            self.return_content = await self.handler.handle_html_content(self.content)
        self.loop.run_until_complete(test())
        soup = BeautifulSoup(self.return_content, "html.parser")
        self.return_content = soup.decode("utf-8")
        self.assertEquals(self.return_content, self.no_dorks_content)

    def test_handle_content_exception(self):
        self.handler.run_args.no_dorks = False
        self.handler.get_dorks = AsyncMock(return_value=[])

        async def test():
            self.return_content = await self.handler.handle_html_content(None)
        with self.assertRaises(TypeError):
            self.loop.run_until_complete(test())

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
