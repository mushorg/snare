import argparse
import asyncio
import configparser
import grp
import json
import mimetypes
import multiprocessing
import os
import pwd
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from urllib.parse import urlparse, unquote, parse_qsl
import aiohttp
import git
import pip
from aiohttp import web
import re
import logging
import multidict
import aiohttp_jinja2
import jinja2

try:
    from aiohttp.web import StaticResource as StaticRoute
except ImportError:
    from aiohttp.web import StaticResource

from bs4 import BeautifulSoup
import cssutils
import netifaces as ni
from middlewares import SnareMiddleware
from tanner_handler import TannerHandler

class HttpRequestHandler():
    def __init__(self, meta, run_args, snare_uuid, debug=False, keep_alive=75, **kwargs):
        self.run_args = run_args
        self.dir = '/opt/snare/pages/{}'.format(run_args.page_dir)
        self.meta = meta
        self.snare_uuid = snare_uuid        
        self.logger = logging.getLogger(__name__)
        self.sroute = StaticRoute(
            name=None, prefix='/',
            directory=self.dir
        )
        self.tanner_handler = TannerHandler(run_args, meta, snare_uuid)

    async def handle_request(self, request):
        self.logger.info('Request path: {0}'.format(request.path))
        data = self.tanner_handler.create_data(request, 200)
        if request.method == 'POST':
            post_data = await request.post()
            self.logger.info('POST data:')
            for key, val in post_data.items():
                self.logger.info('\t- {0}: {1}'.format(key, val))
            data['post_data'] = dict(post_data)

        # Submit the event to the TANNER service
        event_result = await self.tanner_handler.submit_data(data)

        # Log the event to slurp service if enabled
        if self.run_args.slurp_enabled:
            await self.tanner_handler.submit_slurp(request.path)

        content, content_type, headers, status_code = await self.tanner_handler.parse_tanner_response(
            request.path, event_result['response']['message']['detection'])

        response_headers = multidict.CIMultiDict()
        
        for name, val in headers.items():
            response_headers.add(name, val)

        response_headers.add('Server', self.run_args.server_header)

        if 'cookies' in data and 'sess_uuid' in data['cookies']:
            previous_sess_uuid = data['cookies']['sess_uuid']
        else:
            previous_sess_uuid = None

        if event_result is not None and ('sess_uuid' in event_result['response']['message']):
            cur_sess_id = event_result['response']['message']['sess_uuid']
            if previous_sess_uuid is None or not previous_sess_uuid.strip() or previous_sess_uuid != cur_sess_id:
                response_headers.add('Set-Cookie', 'sess_uuid=' + cur_sess_id)

        if not content_type:
            response_content_type = 'text/plain'
        else:
            response_content_type = content_type
        response = web.Response(
            body=content, status=status_code, headers=response_headers, content_type=response_content_type
        )
        return response

    def start(self):
        app = web.Application()
        app.add_routes([web.route('*', '/{tail:.*}', self.handle_request)])
        aiohttp_jinja2.setup(
            app, loader=jinja2.FileSystemLoader(self.dir)
        )
        middleware = SnareMiddleware(self.meta['/status_404']['hash'])
        middleware.setup_middlewares(app)
        web.run_app(app, host=self.run_args.host_ip)
