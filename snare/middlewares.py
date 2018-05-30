import aiohttp_jinja2
from aiohttp import web


class SnareMiddleware():

    def __init__(self, file_name):
        self.error_404 = file_name

    async def handle_404(self, request):
        return aiohttp_jinja2.render_template(self.error_404, request, {})

    async def handle_500(self, request):
        return aiohttp_jinja2.render_template('500.html', request, {})

    def create_error_middleware(self, overrides):

        @web.middleware
        async def error_middleware(request, handler):
            try:
                response = await handler(request)
                override = overrides.get(response.status)
                if override:
                    return await override(request)
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
           500: self.handle_500
        })
        app.middlewares.append(error_middleware)
