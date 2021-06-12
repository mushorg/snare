import unittest
import sys
import os
import shutil
import asyncio
from snare.cloner import Cloner
from snare.utils.page_path_generator import generate_unique_path
from snare.utils.asyncmock import AsyncMock


class TestReplaceLinks(unittest.TestCase):
    def setUp(self):
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.root = "http://example.com"
        self.level = 0
        self.max_depth = sys.maxsize
        self.loop = asyncio.new_event_loop()
        self.css_validate = "false"
        self.handler = Cloner(self.root, self.max_depth, self.css_validate)
        self.content = None
        self.expected_content = None
        self.return_content = None

    def test_replace_relative_links(self):
        self.handler.process_link = AsyncMock(return_value="/test")
        self.root = "http://example.com/test"
        self.content = '\n<html>\n<body>\n<a href="http://example.com/test"></a>\n</body>\n</html>\n'

        self.expected_content = (
            '\n<html>\n<body>\n<a href="/test"></a>\n</body>\n</html>\n'
        )

        async def test():
            self.return_content = await self.handler.replace_links(
                self.content, self.level
            )

        self.loop.run_until_complete(test())
        self.assertEqual(str(self.return_content), self.expected_content)
        self.handler.process_link.assert_called_with(
            self.root, self.level, check_host=True
        )

    def test_replace_image_links(self):
        self.handler.process_link = AsyncMock(return_value="/smiley.png")
        self.root = "http://example.com/smiley.png"
        self.content = '\n<html>\n<body>\n<img src="http://example.com/smiley.png"/>\n</body>\n</html>\n'

        self.expected_content = (
            '\n<html>\n<body>\n<img src="/smiley.png"/>\n</body>\n</html>\n'
        )

        async def test():
            self.return_content = await self.handler.replace_links(
                self.content, self.level
            )

        self.loop.run_until_complete(test())
        self.assertEqual(str(self.return_content), self.expected_content)
        self.handler.process_link.assert_called_with(self.root, self.level)

    def test_replace_action_links(self):
        self.handler.process_link = AsyncMock(return_value="/submit.php")
        self.root = "http://example.com/submit.php"
        self.content = '\n<html>\n<body>\n<form action="http://example.com/submit.php">\n</form>\n</body>\n</html>\n'

        self.expected_content = (
            '\n<html>\n<body>\n<form action="/submit.php">\n</form>\n</body>\n</html>\n'
        )

        async def test():
            self.return_content = await self.handler.replace_links(
                self.content, self.level
            )

        self.loop.run_until_complete(test())
        self.assertEqual(str(self.return_content), self.expected_content)
        self.handler.process_link.assert_called_with(self.root, self.level)

    def test_replace_redirects(self):
        self.root = "http://example.com"
        self.content = (
            '\n<html>\n<body>\n<p name="redirect" value="http://example.com/home.html">Redirecting...</p>\n'
            "</body>\n</html>\n"
        )

        self.expected_content = (
            '\n<html>\n<body>\n<p name="redirect" value="/home.html">Redirecting...</p>\n</body>\n'
            "</html>\n"
        )

        async def test():
            self.return_content = await self.handler.replace_links(
                self.content, self.level
            )

        self.loop.run_until_complete(test())
        self.assertEqual(str(self.return_content), self.expected_content)

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
