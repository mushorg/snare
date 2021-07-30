import unittest
import asyncio
import sys
import yarl
from unittest import mock
from snare.cloner import BaseCloner


class TestProcessLinks(unittest.TestCase):
    def setUp(self):
        self.root = "http://example.com"
        self.level = 0
        self.max_depth = sys.maxsize
        self.loop = asyncio.new_event_loop()
        self.css_validate = False
        self.handler = BaseCloner(self.root, self.max_depth, self.css_validate)
        self.expected_content = None
        self.return_content = None
        self.return_url = None
        self.return_level = None
        self.return_try_count = 0
        self.qsize = None

    def test_process_link_scheme(self):
        test_urls = [
            "file://images/test.png",
            "data://images/test.txt",
            "javascript://alert(1)/",
        ]

        async def test(url_param):
            if not self.handler:
                raise Exception("Error initializing Cloner!")
            self.return_content = await self.handler.process_link(url_param, self.level)
            self.qsize = self.handler.new_urls.qsize()

        for url in test_urls:

            self.loop.run_until_complete(test(url))
            self.expected_content = url
            self.return_size = 0
            self.assertEqual(self.expected_content, self.return_content)
            self.assertEqual(self.qsize, self.return_size)

    def test_process_link_relative(self):
        self.url = "/foo/путь/"
        self.expected_content = "http://example.com/foo/путь/"

        async def test():
            if not self.handler:
                raise Exception("Error initializing Cloner!")
            self.return_content = await self.handler.process_link(self.url, self.level)
            self.return_url, self.return_level, self.return_try_count = (await self.handler.new_urls.get()).values()

        if not self.handler:
            raise Exception("Error initializing Cloner!")

        self.loop.run_until_complete(test())
        self.assertEqual(self.return_content, "/foo/путь/")
        if not self.return_url:
            raise Exception("URL returned is None!")
        self.assertEqual(yarl.URL(self.return_url).human_repr(), self.expected_content)
        self.assertEqual(self.return_level, self.level + 1)
        self.assertLess(self.return_try_count, 2)

        self.handler.moved_root = yarl.URL("http://example2.com")
        self.expected_content = "http://example2.com/foo/путь/"

        self.loop.run_until_complete(test())
        self.assertEqual(self.return_content, "/foo/путь/")
        self.assertEqual(yarl.URL(self.return_url).human_repr(), self.expected_content)
        self.assertEqual(self.return_level, self.level + 1)

    def test_process_link_absolute(self):
        self.url = "http://domain.com"
        self.expected_content = ""

        async def test():
            if not self.handler:
                raise Exception("Error initializing Cloner!")
            self.return_content = await self.handler.process_link(self.url, self.level)
            self.return_url, self.return_level, self.return_try_count = (await self.handler.new_urls.get()).values()

        self.loop.run_until_complete(test())
        self.assertEqual(self.return_content, self.expected_content)
        self.assertEqual(yarl.URL(self.url), self.return_url)
        self.assertEqual(self.return_level, self.level + 1)
        self.assertLess(self.return_try_count, 2)

    def test_check_host(self):
        self.url = "http://foo.com"
        self.return_size = 0

        async def test():
            if not self.handler:
                raise Exception("Error initializing Cloner!")
            self.return_content = await self.handler.process_link(self.url, self.level, check_host=True)
            self.qsize = self.handler.new_urls.qsize()

        self.loop.run_until_complete(test())
        self.assertEqual(self.return_content, None)
        self.assertEqual(self.qsize, self.return_size)

    @mock.patch("yarl.URL")
    def test_process_link_unicode_error(self, url):

        yarl.URL = mock.Mock(side_effect=UnicodeError)

        async def test():
            if not self.handler:
                raise Exception("Error initializing Cloner!")
            self.return_content = await self.handler.process_link(self.root, self.level)

        self.loop.run_until_complete(test())
        self.assertEqual(self.return_content, self.expected_content)
