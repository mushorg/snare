import unittest
from snare.middlewares import SnareMiddleware


class TestMiddleware(unittest.TestCase):

    def setUp(self):
        self.middleware = SnareMiddleware('error_404.html', headers=[
                                          {"Content-Type": "text/html; charset=UTF-8"}], server_header='nginx')

    def test_initialization(self):
        self.assertIsInstance(self.middleware, SnareMiddleware)
