import unittest
from argparse import ArgumentTypeError
from os.path import expanduser

from snare.utils.page_path_generator import generate_unique_path
from snare.utils.snare_helpers import check_privileges


class TestStrToBool(unittest.TestCase):

    def test_privileges_in_root(self):
        self.path = '/'
        try:
            check_privileges(self.path)
            self.privileges = True
        except PermissionError:
            self.privileges = False
        assert self.privileges is False

    def test_privileges_in_home(self):
        self.path = expanduser('~')
        try:
            check_privileges(self.path)
            self.privileges = True
        except PermissionError:
            self.privileges = False
        assert self.privileges is True
