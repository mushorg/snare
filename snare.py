#!/usr/bin/python3

"""
Copyright (C) 2015 MushMush Foundation

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import os
import sys
import argparse
import mimetypes
import json

import asyncio
from urllib.parse import urlparse, unquote
import aiohttp
from aiohttp.web import StaticRoute

from bs4 import BeautifulSoup

import aioredis


class HttpRequestHandler(aiohttp.server.ServerHttpProtocol):

    def __init__(self, run_args, debug=True, keep_alive=75, **kwargs):
        print(run_args)
        self.run_args = run_args
        self.sroute = StaticRoute(
            name=None, prefix='/',
            directory='/opt/snare/pages/{}'.format(run_args.page_dir)
        )
        super().__init__(debug=debug, keep_alive=keep_alive, **kwargs)

    @asyncio.coroutine
    def handle_request(self, request, payload):
        header = {key: value for (key, value) in request.headers.items()}
        data = dict(
            method=request.method,
            path=request.path,
            headers=header
        )
        r = yield from aiohttp.post('http://localhost:8090/event', data=json.dumps(data))
        ret = yield from r.text()
        print(ret)
        response = aiohttp.Response(
            self.writer, 200, http_version=request.version
        )
        base_path = '/'.join(['/opt/snare/pages', self.run_args.page_dir])
        parsed_url = urlparse(unquote(request.path))
        path = '/'.join(
            [base_path, parsed_url.path[1:]]
        )
        path = os.path.normpath(path)
        if os.path.isfile(path) and path.startswith(base_path):
            with open(path, 'rb') as fh:
                content = fh.read()
            content_type = mimetypes.guess_type(path)[0]
            if content_type:
                if 'text/html' in content_type:
                    print(content_type)
                    soup = BeautifulSoup(content, 'html.parser')
                    for p_elem in soup.find_all('p'):
                        text_list = p_elem.text.split()
                        p_new = soup.new_tag('p', style='color:#000000')
                        for idx, word in enumerate(text_list):
                            word += ' '
                            if idx % 5 == 0:
                                a_tag = soup.new_tag(
                                    'a',
                                    href='http://foo.com',
                                    style='color:#000000;text-decoration:none;cursor:text;'
                                )
                                a_tag.string = word
                                p_new.append(a_tag)
                            else:
                                p_new.append(soup.new_string(word))
                        p_elem.replace_with(p_new)
                    content = str(soup).encode('utf-8')
                    # print(repr(content))
                response.add_header('Content-Type', content_type)
            response.add_header('Content-Length', str(len(content)))
            response.send_headers()
            response.write(content)
        else:
            response.status = 404
            response.send_headers()
        yield from response.write_eof()


def snare_setup():
    if os.getuid() != 0:
        print('Snare has to be started as root!')
        sys.exit(1)
    if not os.path.exists('/opt/snare'):
        os.mkdir('/opt/snare')
    if not os.path.exists('/opt/snare/pages'):
        os.mkdir('/opt/snare/pages')


if __name__ == '__main__':
    snare_setup()
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-dir", help="name of the folder to be served")
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    redis_conn = aioredis.create_connection(('localhost', 6379), loop=loop)
    f = loop.create_server(
        lambda: HttpRequestHandler(args, debug=True, keep_alive=75),
        '0.0.0.0', '8080')
    srv = loop.run_until_complete(f)
    print('serving on', srv.sockets[0].getsockname())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
