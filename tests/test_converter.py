import unittest
import os
import sys
import shutil
import hashlib
from converter import Converter


class TestConverter(unittest.TestCase):

    def setUp(self):
        self.content = '<html><body>sample</body></html>'
        self.page_path = '/tmp/test/'
        if not os.path.exists('/tmp/test'):
            os.mkdir('/tmp/test')
        if not os.path.exists('/tmp/test/depth'):
            os.mkdir('/tmp/test/depth')
        self.hname1 = ""
        self.hname2 = ""
        with open(os.path.join(self.page_path, 'index.html'),   'w') as f:
            f.write(self.content)
        with open(os.path.join(self.page_path, 'depth/page.html'), 'w') as f:
            f.write(self.content)
        self.cnv = Converter()

    def test_converter(self):
        self.cnv.convert(self.page_path)
        with open(os.path.join(self.page_path, 'meta.json'), 'r') as f:
            s = f.read()
        index = s.index('"index.html"') + len('"index.html"') + 12
        self.hname1 = s[index: index + 32]
        index = s.index('"depth/page.html"') + len('"depth/page.html"') + 12
        self.hname2 = s[index: index + 32]
        assert(os.path.exists(self.page_path + self.hname1) and
               os.path.exists(self.page_path + self.hname2))

    def tearDown(self):
        shutil.rmtree('/tmp/test/depth')
        shutil.rmtree('/tmp/test')
