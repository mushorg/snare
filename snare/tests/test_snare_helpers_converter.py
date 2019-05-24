import unittest
import os
import shutil
import json
from snare.utils.snare_helpers import Converter


class TestConverter(unittest.TestCase):
    def setUp(self):
        self.content = '<html><body></body></html>'
        self.page_path = '/tmp/test/'
        if not os.path.exists('/tmp/test/depth'):
            os.makedirs('/tmp/test/depth')
        self.hname1 = ""
        self.hname2 = ""
        with open(os.path.join(self.page_path, 'index.html'), 'w') as f:
            f.write(self.content)
        with open(os.path.join(self.page_path, 'depth/page.html'), 'w') as f:
            f.write(self.content)
        self.cnv = Converter()

    def test_converter(self):
        self.cnv.convert(self.page_path)
        with open(os.path.join(self.page_path, 'meta.json')) as f:
            s = json.load(f)
        self.hname1 = s['index.html']['hash']
        self.hname2 = s['depth/page.html']['hash']
        assert (os.path.exists(self.page_path + self.hname1) and
                os.path.exists(self.page_path + self.hname2))

    def tearDown(self):
        shutil.rmtree('/tmp/test')
