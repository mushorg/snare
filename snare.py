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
from asyncio.subprocess import PIPE
import pwd
import grp
from urllib.parse import urlparse, unquote

import aiohttp
from aiohttp.web import StaticRoute

from bs4 import BeautifulSoup
import cssutils


class HttpRequestHandler(aiohttp.server.ServerHttpProtocol):
    def __init__(self, run_args, debug=False, keep_alive=75, **kwargs):
        self.dorks = []
        self.run_args = run_args
        self.sroute = StaticRoute(
            name=None, prefix='/',
            directory='/opt/snare/pages/{}'.format(run_args.page_dir)
        )
        super().__init__(debug=debug, keep_alive=keep_alive, **kwargs)

    @asyncio.coroutine
    def get_dorks(self):
        with aiohttp.Timeout(10.0):
            r = yield from aiohttp.get(
                'http://{0}:8090/dorks'.format(self.run_args.tanner)
            )
            dorks = yield from r.json()
        return dorks['response']['dorks']

    @asyncio.coroutine
    def submit_data(self, data):
        with aiohttp.Timeout(4.0):
            r = yield from aiohttp.post(
                'http://{0}:8090/event'.format(self.run_args.tanner), data=json.dumps(data)
            )
            event_result = yield from r.json()
        return event_result

    @asyncio.coroutine
    def handle_html_content(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        for p_elem in soup.find_all('p'):
            css = None
            if 'style' in p_elem.attrs:
                css = cssutils.parseStyle(p_elem.attrs['style'])
            text_list = p_elem.text.split()
            p_new = soup.new_tag('p', style=css.cssText if css else None)
            for idx, word in enumerate(text_list):
                if len(self.dorks) <= 0:
                    self.dorks = yield from self.get_dorks()
                word += ' '
                if idx % 5 == 0:
                    a_tag = soup.new_tag(
                        'a',
                        href=self.dorks.pop(),
                        style='color:{color};text-decoration:none;cursor:text;'.format(
                            color=css.color if css and 'color' in css.keys() else '#000000'
                        )
                    )
                    a_tag.string = word
                    p_new.append(a_tag)
                else:
                    p_new.append(soup.new_string(word))
            p_elem.replace_with(p_new)
        content = soup.encode('utf-8')
        return content

    @asyncio.coroutine
    def handle_request(self, request, payload):
        print(request.path)
        header = {key: value for (key, value) in request.headers.items()}
        data = dict(
            method=request.method,
            path=request.path,
            headers=header
        )
        event_result = yield from self.submit_data(data)
        response = aiohttp.Response(
            self.writer, status=200, http_version=request.version
        )
        if 'payload' in event_result['response']['detection']:
            content = event_result['response']['detection']['payload']
            content_type = mimetypes.guess_type(content)[0]
        else:
            base_path = '/'.join(['/opt/snare/pages', self.run_args.page_dir])
            if request.path == '/':
                parsed_url = self.run_args.index_page
            else:
                parsed_url = urlparse(unquote(request.path)).path
                if parsed_url.startswith('/'):
                    parsed_url = parsed_url[1:]
            path = '/'.join(
                [base_path, parsed_url]
            )
            path = os.path.normpath(path)
            if os.path.isfile(path) and path.startswith(base_path):
                with open(path, 'rb') as fh:
                    content = fh.read()
                content_type = mimetypes.guess_type(path)[0]
                if content_type:
                    if 'text/html' in content_type:
                        content = yield from self.handle_html_content(content)
            else:
                content_type = None
                content = None
                response = aiohttp.Response(
                    self.writer, status=404, http_version=request.version
                )
        if not content_type:
            response.add_header('Content-Type', 'text/plain')
        else:
            response.add_header('Content-Type', content_type)
        if content:
            # content = content.encode('utf-8')
            response.add_header('Content-Length', str(len(content)))
        response.send_headers()
        if content:
            response.write(content)
        yield from response.write_eof()


def snare_setup():
    if os.getuid() != 0:
        print('Snare has to be started as root!')
        sys.exit(1)
    if not os.path.exists('/opt/snare'):
        os.mkdir('/opt/snare')
    if not os.path.exists('/opt/snare/pages'):
        os.mkdir('/opt/snare/pages')


def drop_privileges():
    uid_name = 'nobody'
    wanted_user = pwd.getpwnam(uid_name)
    gid_name = grp.getgrgid(wanted_user.pw_gid).gr_name
    wanted_group = grp.getgrnam(gid_name)
    os.setgid(wanted_group.gr_gid)
    os.setuid(wanted_user.pw_uid)
    new_user = pwd.getpwuid(os.getuid())
    new_group = grp.getgrgid(os.getgid())
    print('Privileges dropped, running as "{}:{}"'.format(new_user.pw_name, new_group.gr_name))


@asyncio.coroutine
def compare_version_info():
    @asyncio.coroutine
    def _run_cmd(cmd):
        proc = yield from asyncio.create_subprocess_exec(*cmd, stdout=PIPE)
        line = yield from proc.stdout.readline()
        return line

    cmd1 = ["git", "log", "--pretty=format:'%h'", "-n", "1"]
    cmd2 = 'git ls-remote https://github.com/mushorg/snare.git HEAD'.split()
    line1 = yield from _run_cmd(cmd1)
    hash1 = line1[1:-1]
    line2 = yield from _run_cmd(cmd2)
    if not line2.startswith(hash1):
        print('you are running an outdated version')
    else:
        print('you are running the latest version')


if __name__ == '__main__':
    snare_setup()
    loop = asyncio.get_event_loop()
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-dir", help="name of the folder to be served", required=True)
    parser.add_argument("--index-page", help="file name of the index page", default='index.html')
    parser.add_argument("--port", help="port to listen on", default='8080')
    parser.add_argument("--interface", help="interface to bind to", default='localhost')
    parser.add_argument("--debug", help="run web server in debug mode", default=False)
    parser.add_argument("--tanner", help="ip of the tanner service", default='tanner.mushmush.org')
    args = parser.parse_args()
    future = loop.create_server(
        lambda: HttpRequestHandler(args, debug=args.debug, keep_alive=75),
        args.interface, args.port)
    srv = loop.run_until_complete(future)
    print('serving on', srv.sockets[0].getsockname())
    loop.run_until_complete(compare_version_info())
    drop_privileges()
    try:
        loop.run_forever()
    except (KeyboardInterrupt, TypeError) as e:
        print(e)
