#!/usr/bin/env python3

"""
Copyright (C) 2015-2016 MushMush Foundation

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import re
import os
import sys

from urllib.parse import urlparse

import asyncio
import argparse
import aiohttp


class Cloner(object):
    def __init__(self, loop):
        self.connector = aiohttp.TCPConnector(share_cookies=True, loop=loop)

    @asyncio.coroutine
    def get_body(self, root_url):
        if '/' in root_url:
            domain = root_url.rstrip('/').rsplit('/', 1)[1]
        else:
            domain = root_url
            root_url = 'http://' + root_url
        if len(domain) < 4:
            sys.exit('invalid taget {}'.format(root_url))
        page_path = '/opt/snare/pages/{}'.format(domain)
        if not os.path.exists(page_path):
            os.mkdir(page_path)
        response = yield from aiohttp.request('GET', root_url)
        data = yield from response.read()
        with open(page_path + '/index.html', 'wb') as index_fh:
            index_fh.write(data)
        urls = re.findall(r'(?i)(href|src)=["\']?([^\s"\'<>]+)', str(data))
        for url in urls:
            url = url[1]
            parsed_url = urlparse(url)
            if '/' in parsed_url.path:
                url_dir, file_name = parsed_url.path.rsplit('/', 1)
                if not os.path.exists(url_dir):
                    if url_dir.startswith('/'):
                        url_dir = url_dir[1:]
                    url_dir = os.path.join(page_path, url_dir)
                    print(url_dir)
                    try:
                        os.makedirs(url_dir, exist_ok=True)
                    except (FileExistsError, NotADirectoryError):
                        pass
                    try:
                        with open(os.path.join(url_dir, file_name), 'wb') as fh:
                            response = yield from aiohttp.request('GET', root_url + parsed_url.path)
                            data = yield from response.read()
                            fh.write(data)
                    except (IsADirectoryError, NotADirectoryError):
                        continue

    @asyncio.coroutine
    def run(self, url):
        return (yield from self.get_body(url))


def main():
    if os.getuid() != 0:
        print('Clone has to be run as root!')
        sys.exit(1)
    if not os.path.exists('/opt/snare'):
        os.mkdir('/opt/snare')
    if not os.path.exists('/opt/snare/pages'):
        os.mkdir('/opt/snare/pages')
    loop = asyncio.get_event_loop()
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", help="domain of the page to be cloned", required=True)
    args = parser.parse_args()
    c = Cloner(loop)
    loop.run_until_complete(c.run(args.target))


if __name__ == '__main__':
    main()
