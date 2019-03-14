import unittest
import os
import shutil
import configparser
from bs4 import BeautifulSoup
from snare.utils.snare_helpers import add_meta_tag
from snare.utils.page_path_generator import generate_unique_path


class TestAddMetaTag(unittest.TestCase):

    def setUp(self):
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.content = '<html><head>title</head><body>sample</body></html>'
        self.page_dir = self.main_page_path.rsplit('/')[-1]
        self.index_page = "index.html"
        with open(os.path.join(self.main_page_path, 'index.html'), 'w') as f:
            f.write(self.content)

    def test_add_meta_tag(self):
        config = configparser.ConfigParser()
        config['WEB-TOOLS'] = dict(google='test google content', bing='test bing content')
        add_meta_tag(self.page_dir, self.index_page, config)
        with open(os.path.join(self.main_page_path, 'index.html')) as main:
            main_page = main.read()
        soup = BeautifulSoup(main_page, 'html.parser')
        assert(soup.find("meta", attrs={"name": "google-site-verification"}) and
               soup.find("meta", attrs={"name": "msvalidate.01"}))

    def test_add_meta_tag_with_empty_tags(self):
        config = configparser.ConfigParser()
        config['WEB-TOOLS'] = dict(google='', bing='')
        assert add_meta_tag(self.page_dir, self.index_page, config) is None

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
