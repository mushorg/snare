import unittest
import os
from bs4 import BeautifulSoup
import snare
import shutil
import configparser


class TestAddMetaTag(unittest.TestCase):

    def setUp(self):
        if not os.path.exists("/opt/snare"):
            os.mkdir("/opt/snare")
        if not os.path.exists("/opt/snare/pages"):
            os.mkdir("/opt/snare/pages")
        if not os.path.exists("/opt/snare/pages/test"):
            os.mkdir("/opt/snare/pages/test")
        self.content = '<html><head>title</head><body>sample</body></html>'
        self.page_dir = "test"
        self.index_page = "index.html"
        self.main_page_path = '/opt/snare/pages/test'
        with open(os.path.join(self.main_page_path, 'index.html'), 'w') as f:
            f.write(self.content)

    def test_add_meta_tag(self):
        snare.config = configparser.ConfigParser()
        snare.config['WEB-TOOLS'] = dict(google='test google content', bing='test bing content')
        snare.add_meta_tag(self.page_dir, self.index_page)
        with open(os.path.join(self.main_page_path, 'index.html'), 'r') as main:
            main_page = main.read()
        soup = BeautifulSoup(main_page, 'html.parser')
        assert(soup.find("meta", attrs={"name": "google-site-verification"}) and
               soup.find("meta", attrs={"name": "msvalidate.01"}))

    def tearDown(self):
        shutil.rmtree("/opt/snare/pages/test")
