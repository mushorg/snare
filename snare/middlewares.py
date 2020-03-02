import aiohttp_jinja2
import multidict
from aiohttp import web


class SnareMiddleware():

    def __init__(self, error_404, error_500=None, headers=[], server_header=''):
        self.error_404 = error_404
        self.error_500 = error_500 if error_500 else '500.html'

        self.headers = multidict.CIMultiDict()
        for header in headers:
            for key, value in header.items():
                self.headers.add(key, value)

        if server_header:
            self.headers['Server'] = server_header

    async def handle_404(self, request):
        return aiohttp_jinja2.render_template(self.error_404, request, {})

    async def handle_500(self, request):
        return aiohttp_jinja2.render_template(self.error_500, request, {})

    def create_error_middleware(self, overrides):

        @web.middleware
        async def error_middleware(request, handler):
            try:
                response = await handler(request)
                status = response.status
                override = overrides.get(status)
                if override:
                    response = await override(request)
                    response.headers.update(self.headers)
                    response.set_status(status)
                    return response
                return response
            except web.HTTPException as ex:
                override = overrides.get(ex.status)
                if override:
                    return await override(request)
                raise

        return error_middleware

    def setup_middlewares(self, app):
        error_middleware = self.create_error_middleware({
            404: self.handle_404,
            500: self.handle_500,
        })
        app.middlewares.append(error_middleware)
