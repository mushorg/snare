import argparse
import logging
from typing import Dict

import aiohttp
from aiohttp import web
from aiohttp.web import StaticResource as StaticRoute
import aiohttp_jinja2
import jinja2

from snare.middlewares import SnareMiddleware
from snare.tanner_handler import TannerHandler


class HttpRequestHandler:
    def __init__(
        self,
        meta: Dict,
        run_args: argparse.Namespace,
        snare_uuid: bytes,
        debug: bool = False,
        keep_alive: int = 75,
        **kwargs: Dict[str, str]
    ) -> None:
        """HTTP request handler class

        :param meta: Meta info from `meta.json`
        :type meta: Dict
        :param run_args: Runtime CLI arguments
        :type run_args: argparse.Namespace
        :param snare_uuid: UUID of Snare instance
        :type snare_uuid: bytes
        :param debug: Enable debugging with verbose logs, defaults to False
        :type debug: bool, optional
        :param keep_alive: HTTP connection persistence duration, defaults to 75
        :type keep_alive: int, optional
        """
        self.run_args = run_args
        self.dir = run_args.full_page_path
        self.meta = meta
        self.snare_uuid = snare_uuid
        self.logger = logging.getLogger(__name__)
        self.sroute = StaticRoute(name=None, prefix="/", directory=self.dir)
        self.tanner_handler = TannerHandler(run_args, meta, snare_uuid)

    async def submit_slurp(self, data: str) -> None:
        """Log request URL to Slurp service

        :param data: Request URL
        :type data: str
        """
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                r = await session.post(
                    "https://{0}:8080/api?auth={1}&chan=snare_test&msg={2}".format(
                        self.run_args.slurp_host, self.run_args.slurp_auth, data
                    ),
                    json=data,
                    timeout=10.0,
                )
                assert r.status == 200
                r.close()
        except Exception as e:
            self.logger.error("Error submitting slurp: %s", e)

    async def handle_request(self, request: web.Request) -> web.Response:
        """Communicate with Tanner to prepare response to incoming requests

        :param request: Incoming request
        :type request: web.Request
        :raises web.HTTPNotFound: If requested URL/page cannot be found (Status code: 404)
        :return: Response
        :rtype: web.Response
        """
        self.logger.info("Request path: {0}".format(request.path_qs))
        data = self.tanner_handler.create_data(request, 200)
        if request.method == "POST":
            post_data = await request.post()
            self.logger.info("POST data:")
            for key, val in post_data.items():
                self.logger.info("\t- {0}: {1}".format(key, val))
            data["post_data"] = dict(post_data)

        # Submit the event to the TANNER service
        event_result = await self.tanner_handler.submit_data(data)

        # Log the event to slurp service if enabled
        if self.run_args.slurp_enabled:
            await self.submit_slurp(request.path_qs)

        content, headers, status_code = await self.tanner_handler.parse_tanner_response(
            request.path_qs, event_result["response"]["message"]["detection"]
        )

        if self.run_args.server_header:
            headers["Server"] = self.run_args.server_header

        if "cookies" in data and "sess_uuid" in data["cookies"]:
            previous_sess_uuid = data["cookies"]["sess_uuid"]
        else:
            previous_sess_uuid = None

        if event_result is not None and "sess_uuid" in event_result["response"]["message"]:
            cur_sess_id = event_result["response"]["message"]["sess_uuid"]
            if previous_sess_uuid is None or not previous_sess_uuid.strip() or previous_sess_uuid != cur_sess_id:
                headers.add("Set-Cookie", "sess_uuid=" + cur_sess_id)

        if status_code == 404 and not content:
            raise web.HTTPNotFound()

        return web.Response(body=content, status=status_code, headers=headers)

    @staticmethod
    async def remove_default_server_header(_: web.Request, response: web.Response) -> None:
        """Remove the default aiohttp server header (anti-fingerprinting defense)

        :param _: Incoming request
        :type _: web.Request
        :param response: Response to be sent
        :type response: web.Response
        """
        if response.headers.get("Server") and "aiohttp" in response.headers["Server"]:
            del response.headers["Server"]

    async def start(self) -> None:
        """Start Snare web server"""
        app = web.Application()
        app.add_routes([web.route("*", "/{tail:.*}", self.handle_request)])
        app.on_response_prepare.append(self.remove_default_server_header)
        aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(self.dir))
        middleware = SnareMiddleware(
            error_404=self.meta["/status_404"].get("hash") if self.meta.get("/status_404") else None,
            headers=self.meta["/status_404"].get("headers", []) if self.meta.get("/status_404") else [],
            server_header=self.run_args.server_header,
        )
        middleware.setup_middlewares(app)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.run_args.host_ip, self.run_args.port)

        await site.start()
        names = sorted(str(s.name) for s in self.runner.sites)
        print("======== Running on {} ========\n" "(Press CTRL+C to quit)".format(", ".join(names)))

    async def stop(self) -> None:
        """Clean up and close connections"""
        await self.runner.cleanup()
