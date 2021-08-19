from aiohttp import web
import aiohttp_jinja2
import multidict
from typing import Callable, Dict, List, Union


class SnareMiddleware:
    def __init__(self, error_404: Union[None, str], headers: List[Dict[str, str]] = [], server_header: str = "") -> None:
        """Middleware class for Snare's aiohttp web server

        :param error_404: 404 page's file name (hash)
        :type error_404: Union[None, str]
        :param headers: 404 page headers, defaults to []
        :type headers: List[Dict[str, str]], optional
        :param server_header: Server header/banner, defaults to ""
        :type server_header: str, optional
        """
        self.error_404 = error_404

        self.headers = multidict.CIMultiDict()
        for header in headers:
            for key, value in header.items():
                self.headers.add(key, value)

        if server_header:
            self.headers["Server"] = server_header

    async def handle_404(self, request: web.Request) -> web.Response:
        """404 Handler (Page not found)

        :param request: Incoming request
        :type request: web.Request
        :raises web.HTTPNotFound: With correct headers from meta if 404 file is not found
        :return: Templated 404 response
        :rtype: web.Response
        """
        if not self.error_404:
            raise web.HTTPNotFound(headers=self.headers)
        response = aiohttp_jinja2.render_template(self.error_404, request, {}, status=404)
        for key, val in self.headers.items():
            response.headers[key] = val
        return response

    async def handle_500(self, _: web.Request) -> None:
        """500 handler

        :param _: Incoming request
        :type _: web.Request
        :raises web.HTTPInternalServerError: With correct headers from meta
        """
        raise web.HTTPInternalServerError(headers=self.headers)

    def create_error_middleware(self, overrides: Dict) -> Callable[[web.Request, Callable[[web.Request], web.Response]], web.Response]:
        """Create middleware for given errors

        :param overrides: Status codes and their handlers
        :type overrides: Dict
        :return: Middleware function to prepare response from handlers
        :rtype: web.middleware
        """
        @web.middleware
        async def error_middleware(request: web.Request, handler: Callable[[web.Request], web.Response]) -> web.Response:
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

    def setup_middlewares(self, app: web.Application) -> None:
        """Setup middlware

        :param app: Snare's aiohttp web application
        :type app: web.Application
        """
        error_middleware = self.create_error_middleware(
            {
                404: self.handle_404,
                500: self.handle_500,
            }
        )
        app.middlewares.append(error_middleware)
