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
        self.root = 'http://example.com'
        self.level = 0
        self.max_depth = sys.maxsize
        self.loop = asyncio.new_event_loop()
        self.css_validate = 'false'
        self.handler = Cloner(self.root, self.max_depth, self.css_validate)
        self.content = None

    def test_replace_relative_links(self):
        self.handler.process_link = AsyncMock(return_value="/test")
        self.root = 'http://example.com/test'
        self.content = '''
                          <html>
                                <body>
                                      <a href="http://example.com/test"></a>
                                </body>
                          </html>
                       '''

        async def test():
            await self.handler.replace_links(self.content, self.level)

        self.loop.run_until_complete(test())
        self.handler.process_link.assert_called_with(self.root, self.level, check_host=True)

    def test_replace_image_links(self):
        self.handler.process_link = AsyncMock(return_value="/smiley.png")
        self.root = "http://example.com/smiley.png"
        self.content = '''
                          <html>
                                <body>
                                      <img src="http://example.com/smiley.png">
                                </body>
                          </html>
                       '''

        async def test():
            await self.handler.replace_links(self.content, self.level)

        self.loop.run_until_complete(test())
        self.handler.process_link.assert_called_with(self.root, self.level)

    def test_replace_action_links(self):
        self.handler.process_link = AsyncMock(return_value="/submit.php")
        self.root = "http://example.com/submit.php"
        self.content = '''
                          <html>
                                <body>
                                      <form action="http://example.com/submit.php" >.....</form>
                                </body>
                          </html>
                       '''

        async def test():
            await self.handler.replace_links(self.content, self.level)

        self.loop.run_until_complete(test())
        self.handler.process_link.assert_called_with(self.root, self.level)

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
