import unittest
import sys
from snare.cloner import BaseCloner, HeadlessCloner, SimpleCloner, CloneRunner
import shutil


class TestClonerInitialization(unittest.TestCase):
    def setUp(self):
        self.root = "http://example.com"
        self.max_depth = sys.maxsize
        self.css_validate = False
        self.target_path = None
        self.handler = None

    def test_base_cloner_init(self):
        self.handler = BaseCloner(self.root, self.max_depth, self.css_validate, default_path="/tmp")
        self.target_path = self.handler.target_path
        self.assertIsInstance(self.handler, BaseCloner)

    def test_simple_cloner_init(self):
        self.handler = SimpleCloner(self.root, self.max_depth, self.css_validate, default_path="/tmp")
        self.assertIsInstance(self.handler, SimpleCloner)

    def test_headless_cloner_init(self):
        self.handler = HeadlessCloner(self.root, self.max_depth, self.css_validate, default_path="/tmp")
        self.assertIsInstance(self.handler, HeadlessCloner)

    def test_clone_runner_init(self):
        self.handler = CloneRunner(self.root, self.max_depth, self.css_validate, default_path="/tmp")
        self.assertIsInstance(self.handler, CloneRunner)

    def tearDown(self):
        if self.target_path:
            shutil.rmtree(self.target_path)
