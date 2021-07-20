import unittest

from aiohttp import web

from snare.middlewares import SnareMiddleware


class TestMiddleware(unittest.TestCase):
    def setUp(self):
        self.middleware = SnareMiddleware(
            "error_404.html",
            headers=[{"Content-Type": "text/html; charset=UTF-8"}],
            server_header="nginx",
        )
        self.app = None

    def test_initialization(self):
        self.assertIsInstance(self.middleware, SnareMiddleware)

    def test_middleware_setup(self):
        self.app = web.Application()
        self.assertIsInstance(self.app, web.Application)
        self.middleware.setup_middlewares(self.app)
        self.assertIsNotNone(self.app.middlewares)
