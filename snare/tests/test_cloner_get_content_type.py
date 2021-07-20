import unittest
import sys
import os
import yarl
import shutil
from snare.cloner import HeadlessCloner
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
        self.handler = HeadlessCloner(self.url, self.max_depth, self.css_validate)

    def test_content_type_header(self):
        self.headers = [{"Content-Type": "text/html"}, {"Transfer-Encoding": "chunked"}, {"Vary": "Accept-Encoding"}]
        self.expected_content_type = "text/html"
        self.return_content_type = self.handler.get_content_type(self.headers)
        self.assertEqual(self.expected_content_type, self.return_content_type)

    def test_content_type_header_absent(self):
        self.headers = [{"Transfer-Encoding": "chunked"}, {"Vary": "Accept-Encoding"}]
        self.expected_content_type = None
        self.return_content_type = self.handler.get_content_type(self.headers)
        self.assertEqual(self.expected_content_type, self.return_content_type)

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
