import unittest
import sys
import os
import shutil
import asyncio
from snare.cloner import Cloner
from snare.utils.page_path_generator import generate_unique_path


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
        self.content = '''
                          <html>
                                <body>
                                      <a href="http://example.com/test"></a>
                                </body>
                          </html>
                       '''
        self.expected_content = None
        self.return_content = None

    def test_replace_relative_links(self):
        self.expected_content = '\n<html>\n<body>\n<a href="/test"></a>\n</body>\n</html>\n'

        async def test():
            self.return_content = await self.handler.replace_links(self.content, self.level)

        self.loop.run_until_complete(test())
        self.assertEqual(str(self.return_content), self.expected_content)

    def test_replace_image_links(self):
        self.content = '''
                          <html>
                                <body>
                                      <img src="http://example.com/smiley.png">
                                </body>
                          </html>
                       '''

        async def test():
            self.return_content = await self.handler.replace_links(self.content, self.level)

        self.loop.run_until_complete(test())
        self.expected_content = '\n<html>\n<body>\n<img src="/smiley.png"/>\n</body>\n</html>\n'
        self.assertEqual(str(self.return_content), self.expected_content)

    def test_replace_action_links(self):
        self.content = '''
                          <html>
                                <body>
                                      <form action="http://example.com/submit.php" >.....</form>
                                </body>
                          </html>
                       '''

        async def test():
            self.return_content = await self.handler.replace_links(self.content, self.level)

        self.loop.run_until_complete(test())
        self.expected_content = '\n<html>\n<body>\n<form action="/submit.php">.....</form>\n</body>\n</html>\n'
        self.assertEqual(str(self.return_content), self.expected_content)

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
