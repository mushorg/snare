import unittest
import sys
import os
import shutil
import yarl
import asyncio
from snare.cloner import Cloner
from snare.utils.page_path_generator import generate_unique_path


class TestMakeFilename(unittest.TestCase):
    def setUp(self):
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.url = yarl.URL('http://foo.com')
        self.root = 'http://example.com'
        self.max_depth = sys.maxsize
        self.loop = asyncio.new_event_loop()
        self.css_validate = 'false'
        self.handler = Cloner(self.root, self.max_depth, self.css_validate)
        self.filename = None
        self.hashname = None

    def test_make_filename(self):
        self.filename, self.hashname = self.handler._make_filename(self.url)
        self.assertEqual(self.filename, 'foo.com')
        self.assertEqual(self.hashname, '167a0418dd8ce3bf0ef00dfb6195f038')

    def test_make_filename_same_host(self):
        self.filename, self.hashname = self.handler._make_filename(
            yarl.URL(self.root))
        self.assertEqual(self.filename, '/index.html')
        self.assertEqual(self.hashname, 'd1546d731a9f30cc80127d57142a482b')

    def test_make_filename_relative(self):
        self.url = yarl.URL('/images')
        self.filename, self.hashname = self.handler._make_filename(self.url)
        self.assertEqual(self.filename, '/images')
        self.assertEqual(self.hashname, '41389bcf7f7427468d8c8675db2d4f98')

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
