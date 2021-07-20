import os
import shutil
import sys
import unittest

import yarl

from snare.cloner import BaseCloner
from snare.utils.page_path_generator import generate_unique_path


class TestCloner(unittest.TestCase):
    def setUp(self):
        self.url = "http://example.com"
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.expected_new_url = yarl.URL("http://example.com")
        self.expected_err_url = yarl.URL("http://example.com/status_404")
        self.max_depth = sys.maxsize
        self.css_validate = False
        self.handler = BaseCloner(self.url, self.max_depth, self.css_validate)

    def test_trailing_slash(self):
        self.url = "http://example.com/"
        if not self.handler:
            raise Exception("Error initializing BaseCloner!")
        new_url, err_url = self.handler.add_scheme(self.url)
        self.assertEqual(new_url, self.expected_new_url)
        self.assertEqual(err_url, self.expected_err_url)

    def test_add_scheme(self):
        if not self.handler:
            raise Exception("Error initializing BaseCloner!")
        new_url, err_url = self.handler.add_scheme(self.url)

        self.assertEqual(new_url, self.expected_new_url)
        self.assertEqual(err_url, self.expected_err_url)

    def test_no_scheme(self):
        self.url = "example.com"
        if not self.handler:
            raise Exception("Error initializing BaseCloner!")
        new_url, err_url = self.handler.add_scheme(self.url)
        self.assertEqual(new_url, self.expected_new_url)
        self.assertEqual(err_url, self.expected_err_url)

    def tearDown(self):
        shutil.rmtree(self.main_page_path)

    def test_no_host(self):
        self.url = "http:/"
        with self.assertRaises(SystemExit):
            BaseCloner(self.url, self.max_depth, self.css_validate)

    def test_limited_length_host(self):
        self.url = "http://aaa"
        with self.assertRaises(SystemExit):
            BaseCloner(self.url, self.max_depth, self.css_validate)
