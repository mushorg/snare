import unittest
import sys
from snare.cloner import Cloner
import shutil


class TestClonerInitialization(unittest.TestCase):
    def setUp(self):
        self.root = 'http://example.com'
        self.max_depth = sys.maxsize
        self.css_validate = 'false'
        self.handler = Cloner(self.root, self.max_depth,
                              self.css_validate, default_path='/tmp')

    def test_cloner_init(self):
        self.assertIsInstance(self.handler, Cloner)

    def tearDown(self):
        shutil.rmtree(self.handler.target_path)
