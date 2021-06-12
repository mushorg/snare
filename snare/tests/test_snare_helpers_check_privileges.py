import unittest
from os.path import expanduser, join

from snare.utils.snare_helpers import check_privileges


class TestStrToBool(unittest.TestCase):
    def test_privileges_in_root(self):
        self.path = "/"
        try:
            check_privileges(self.path)
        except PermissionError as e:
            self.fail(f"failed permissions check: {e}")

    def test_privileges_in_home(self):
        self.path = expanduser("~")
        try:
            check_privileges(self.path)
        except PermissionError as e:
            self.fail(f"failed permissions check: {e}")

    def test_non_existent_root_path(self):
        self.path = "/snare"
        try:
            check_privileges(self.path)
        except PermissionError as e:
            self.fail(f"failed permissions check: {e}")

    def test_non_existent_home_path(self):
        self.path = join(expanduser("~"), "snare")
        try:
            check_privileges(self.path)
        except PermissionError as e:
            self.fail(f"failed permissions check: {e}")
