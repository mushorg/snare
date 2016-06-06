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
import cssutils
from bs4 import BeautifulSoup


class Cloner(object):
    def __init__(self, loop):
        self.connector = aiohttp.TCPConnector(share_cookies=True, loop=loop)

    @asyncio.coroutine
    def get_body(self, root_url, urls, visited_urls):
        if not root_url.startswith("http"):
            root_url = 'http://' + root_url
        parsed_url = urlparse(root_url)
        if parsed_url.fragment:
            return

        domain = parsed_url.netloc
        file_name = parsed_url.path if parsed_url.path[1:] else '/index'
        if file_name[-1] == '/':
            file_name = file_name[:-1]
        if '.' not in file_name:
            file_name += '.html'

        file_path = ''
        patt = '/.*/.*\.'
        if re.match(patt, file_name):
            file_path, file_name = file_name.rsplit('/', 1)
        print(file_path, file_name)

        if len(domain) < 4:
            sys.exit('invalid taget {}'.format(root_url))
        page_path = '/opt/snare/pages/{}'.format(domain)
        if not os.path.exists(page_path):
            os.mkdir(page_path)

        if file_path and not os.path.exists(page_path + file_path):
            os.mkdir(page_path + file_path)

        data = None
        try:
            with aiohttp.ClientSession() as session:
                response = yield from session.get(root_url)
                data = yield from response.read()
                session.close()
        except Exception as e:
            pass

        if data is not None:
            soup = BeautifulSoup(data, 'html.parser')
            patt = '.*' + domain + '.*'
            for a in soup.findAll('a'):
                if re.match(patt, a['href']):
                    if a['href'][-1] == '/':
                        a['href'] = a['href'][:-1]
                    urls.append(a['href'])
                new_link = urlparse(a['href']).path
                if not new_link:
                    new_link = '/index'
                a['href'] = new_link + '.html'
            data = str(soup).encode()
        with open(page_path + file_path + file_name, 'wb') as index_fh:
            index_fh.write(data)
        if '.css' in file_name:
            css = cssutils.parseString(data)
            for carved_url in cssutils.getUrls(css):
                carved_url = os.path.normpath(os.path.join(domain, carved_url))
                if not carved_url.startswith('/'):
                    carved_url = '/' + carved_url
                if carved_url not in visited_urls:
                    urls.insert(0, carved_url)
        visited_urls.append(root_url)
        for url in urls:
            urls.remove(url)
            if url in visited_urls:
                continue
            yield from self.get_body(url, urls, visited_urls)

    @asyncio.coroutine
    def run(self, url):
        return (yield from self.get_body(url, [], []))


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
