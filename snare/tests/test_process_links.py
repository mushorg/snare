import unittest
import asyncio
import sys
from snare.cloner import Cloner


class TestProcessLinks(unittest.TestCase):
    def setUp(self):
        self.root = 'http://example.com'
        self.level = 0
        self.max_depth = sys.maxsize
        self.loop = asyncio.new_event_loop()
        self.css_validate = 'false'
        self.handler = Cloner(self.root, self.max_depth, self.css_validate)
        self.expected_content = None
        self.return_content = None

    def test_process_link_scheme(self):
        self.url = 'file://images/test.png'

        async def test():
            self.return_content = await self.handler.process_link(self.url, self.level)

        self.loop.run_until_complete(test())
        self.expected_content = 'file://images/test.png'
        self.assertEqual(self.expected_content, self.return_content)

    def test_process_link_relative(self):
        self.url = '/foo/путь/'

        async def test():
            self.return_content = await self.handler.process_link(self.url, self.level)

        self.loop.run_until_complete(test())
        self.assertEqual(self.return_content, '/foo/путь/')

    def test_check_host(self):
        self.url = 'http://foo.com'

        async def test():
            self.return_content = await self.handler.process_link(self.url, self.level, check_host=True)

        self.loop.run_until_complete(test())
        self.assertEqual(self.return_content, None)
