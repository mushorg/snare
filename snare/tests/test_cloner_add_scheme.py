import unittest
import sys
import os
import yarl
import shutil
from snare.cloner import Cloner
from snare.utils.page_path_generator import generate_unique_path


class TestCloner(unittest.TestCase):
    def setUp(self):
        self.url = 'http://example.com'
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.expected_new_url = yarl.URL('http://example.com')
        self.expected_err_url = yarl.URL('http://example.com/status_404')
        self.max_depth = sys.maxsize
        self.css_validate = 'false'
        self.handler = Cloner(self.url, self.max_depth, self.css_validate)

    def test_trailing_slash(self):
        self.url = 'http://example.com/'
        new_url, err_url = self.handler.add_scheme(self.url)
        self.assertEqual(new_url, self.expected_new_url)
        self.assertEqual(err_url, self.expected_err_url)

    def test_add_scheme(self):
        new_url, err_url = self.handler.add_scheme(self.url)

        self.assertEqual(new_url, self.expected_new_url)
        self.assertEqual(err_url, self.expected_err_url)

    def test_no_scheme(self):
        self.url = 'example.com'
        new_url, err_url = self.handler.add_scheme(self.url)
        self.assertEqual(new_url, self.expected_new_url)
        self.assertEqual(err_url, self.expected_err_url)

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
