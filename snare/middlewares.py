from aiohttp import web
import aiohttp_jinja2
import multidict


class SnareMiddleware:
    def __init__(self, error_404, headers=[], server_header=""):
        self.error_404 = error_404

        self.headers = multidict.CIMultiDict()
        for header in headers:
            for key, value in header.items():
                self.headers.add(key, value)

        if server_header:
            self.headers["Server"] = server_header

    async def handle_404(self, request):
        if not self.error_404:
            raise web.HTTPNotFound(headers=self.headers)
        response = aiohttp_jinja2.render_template(self.error_404, request, {}, status=404)
        for key, val in self.headers.items():
            response.headers[key] = val
        return response

    async def handle_500(self, _):
        raise web.HTTPInternalServerError(headers=self.headers)

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
        error_middleware = self.create_error_middleware(
            {
                404: self.handle_404,
                500: self.handle_500,
            }
        )
        app.middlewares.append(error_middleware)
