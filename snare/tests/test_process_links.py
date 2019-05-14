import unittest
import asyncio
import sys
import yarl
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
        arr = ['file://images/test.png', 'data://images/test.txt', 'javascript://alert(1)/']

        for url in arr:
            async def test():
                self.return_content = await self.handler.process_link(url, self.level)

            self.loop.run_until_complete(test())
            self.expected_content = url
            self.assertEqual(self.expected_content, self.return_content)

    def test_process_link_relative(self):
        self.url = '/foo/путь/'
        self.expected_content = 'http://example.com/foo/путь/'

        async def test():
            self.return_content = await self.handler.process_link(self.url, self.level)

        self.loop.run_until_complete(test())
        self.assertEqual(self.return_content, '/foo/путь/')

        async def get_url():
            self.url, self.level = await self.handler.new_urls.get()

        self.loop.run_until_complete(get_url())
        self.assertEqual(yarl.URL(self.url).human_repr(), self.expected_content)
        self.assertEqual(self.level, 1)

    def test_check_host(self):
        self.url = 'http://foo.com'

        async def test():
            self.return_content = await self.handler.process_link(self.url, self.level, check_host=True)

        self.loop.run_until_complete(test())
        self.assertEqual(self.return_content, None)
