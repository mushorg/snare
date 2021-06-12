import unittest
import asyncio
import shutil
import os
from bs4 import BeautifulSoup
from snare.utils.asyncmock import AsyncMock
from snare.html_handler import HtmlHandler
from snare.utils.page_path_generator import generate_unique_path


class TestHandleHtmlContent(unittest.TestCase):
    def setUp(self):
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.content = """
                          <html>
                                <body>
                                <p style="color:red;">A paragraph to be tested</p>
                                </body>
                          </html>
                       """
        self.expected_content = '<html>\n <body>\n  <p style="color: red">\n'
        self.expected_content += '   <a href="test_dork1" style="color:red;text-decoration:none;cursor:text;">\n'
        self.expected_content += "    A\n   </a>\n   paragraph to be tested\n  </p>\n </body>\n</html>\n"
        self.no_dorks_content = '<html>\n <body>\n  <p style="color:red;">\n   A paragraph to be tested\n'
        self.no_dorks_content += "  </p>\n </body>\n</html>\n"
        self.loop = asyncio.new_event_loop()
        self.return_content = None
        no_dorks = True
        tanner = "tanner.mushmush.org"
        self.handler = HtmlHandler(no_dorks, tanner)

    def test_handle_content(self):
        self.handler.no_dorks = False
        self.handler.get_dorks = AsyncMock(return_value=["test_dork1"])

        async def test():
            self.return_content = await self.handler.handle_content(self.content)

        self.loop.run_until_complete(test())
        soup = BeautifulSoup(self.return_content, "html.parser")
        return_content = soup.decode("utf-8")
        self.assertEqual(return_content, self.expected_content)

    def test_handle_content_no_dorks(self):
        self.handler.no_dorks = True

        async def test():
            self.return_content = await self.handler.handle_content(self.content)

        self.loop.run_until_complete(test())
        soup = BeautifulSoup(self.return_content, "html.parser")
        self.return_content = soup.decode("utf-8")
        self.assertEqual(self.return_content, self.no_dorks_content)

    def test_handle_content_exception(self):
        self.handler.no_dorks = False
        self.handler.get_dorks = AsyncMock(return_value=[])

        async def test():
            self.return_content = await self.handler.handle_content(self.content)

        with self.assertRaises(IndexError):
            self.loop.run_until_complete(test())

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
