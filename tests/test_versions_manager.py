import unittest
from versions_manager import VersionManager


class TestVersion(unittest.TestCase):
 
    def setUp(self):
        self.vm = VersionManager()
        self.vm.version = "0.1.0"

    def test_check_compatibilty_fails(self):
        with self.assertRaises(RuntimeError):
            self.vm.check_compatibility("0.0.0")
    
    def test_check_compatibilty_ok(self):
        self.vm.check_compatibility("0.3.0")
