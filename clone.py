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

import asyncio
from asyncio import Queue
import argparse
import aiohttp
import cssutils
import yarl
from bs4 import BeautifulSoup


class Cloner(object):
    def __init__(self, root):
        self.visited_urls = []
        self.root = self.add_scheme(root)
        self.error_page = self.add_scheme(root + "/error_404")
        if len(self.root.host) < 4:
            sys.exit('invalid taget {}'.format(self.root.host))
        self.target_path = '/opt/snare/pages/{}'.format(self.root.host)

        if not os.path.exists(self.target_path):
            os.mkdir(self.target_path)

        self.new_urls = Queue()

    @staticmethod
    def add_scheme(url):
        if yarl.URL(url).scheme:
            new_url = yarl.URL(url)
        else:
            new_url = yarl.URL('http://' + url)
        return new_url

    @asyncio.coroutine
    def process_link(self, url, check_host=False):
        url = yarl.URL(url)
        if check_host:
            if (url.host != self.root.host or url.fragment
                            or url in self.visited_urls):
                return None
        if not url.is_absolute():
            url = self.root.join(url)

        yield from self.new_urls.put(url)
        return url.relative().human_repr()

    @asyncio.coroutine
    def replace_links(self, data):
        soup = BeautifulSoup(data, 'html.parser')

        # find all relative links
        for link in soup.findAll(href=True):
            res = yield from self.process_link(link['href'], check_host=True)
            if res is not None:
                link['href'] = res

        # find all images and scripts
        for elem in soup.findAll(src=True):
            res = yield from self.process_link(elem['src'])
            if res is not None:
                elem['src'] = res

        # find all action elements
        for act_link in soup.findAll(action=True):
            res = yield from self.process_link(act_link['action'])
            if res is not None:
                act_link['action'] = res

        # prevent redirects
        for redir in soup.findAll(True, attrs={'name': re.compile('redirect.*')}):
            redir['value'] = yarl.URL(redir['value']).relative().human_repr()

        return soup

    @asyncio.coroutine
    def get_body(self):
        while not self.new_urls.empty():
            current_url = yield from self.new_urls.get()
            if current_url in self.visited_urls:
                continue
            self.visited_urls.append(current_url)
            if current_url.name:
                file_name = current_url.name
            elif current_url.raw_path != '/':
                file_name = current_url.path.rsplit('/')[1]
            else:
                file_name = 'index.html'
            file_path = os.path.dirname(current_url.path)
            if file_path == '/':
                file_path = self.target_path
            else:
                file_path = os.path.join(self.target_path, file_path[1:])

            print('path: ', file_path, 'name: ', file_name)

            if file_path and not os.path.exists(file_path):
                os.makedirs(file_path)

            data = None
            try:
                with aiohttp.Timeout(10.0):
                    with aiohttp.ClientSession() as session:
                        response = yield from session.get(current_url)
                        data = yield from response.read()
            except aiohttp.ClientError as client_error:
                print(client_error)
            else:
                response.release()
                session.close()
            if data is not None:
                if re.match(re.compile('.*\.(html|php)'), file_name):
                    soup = yield from self.replace_links(data)
                    data = str(soup).encode()
                with open(os.path.join(file_path, file_name), 'wb') as index_fh:
                    index_fh.write(data)
                if '.css' in file_name:
                    css = cssutils.parseString(data)
                    for carved_url in cssutils.getUrls(css):
                        if carved_url.startswith('data'):
                            continue
                        carved_url = yarl.URL(carved_url)
                        if not carved_url.is_absolute():
                            carved_url = self.root.join(carved_url)
                        if carved_url not in self.visited_urls:
                            yield from self.new_urls.put(carved_url)

    @asyncio.coroutine
    def run(self):
        yield from self.new_urls.put(self.root)
        # Force 404 Page
        yield from self.new_urls.put(self.error_page)
        return (yield from self.get_body())


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
    cloner = Cloner(args.target)
    loop.run_until_complete(cloner.run())


if __name__ == '__main__':
    main()
