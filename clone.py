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

from urllib.parse import urlparse, unquote

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
        self.root = self.make_abs_url(root)
        if len(self.root.host) < 4:
            sys.exit('invalid taget {}'.format(self.root.host))
        self.target_path = '/opt/snare/pages/{}'.format(self.root.host)

        if not os.path.exists(self.target_path):
            os.mkdir(self.target_path)

        self.new_urls = Queue()

    def make_abs_url(self, url):
        if yarl.URL(url).is_absolute():
            root = yarl.URL(url)
        else:
            root = yarl.URL('http://' + url)
        return root

    def make_new_link(self, url, abs):
        if url.path == '/':
            url.joun(yarl.URL('index.html'))
        if not abs:
            url = url.relative()
        else:
            url = url.with_host(self.root.host)
        return url.human_repr()

    @asyncio.coroutine
    def replace_links(self, data):
        soup = BeautifulSoup(data, 'html.parser')
        base_url = yarl.URL(self.root)

        # find all relative links
        for link in soup.findAll(href=True):
            abs=False
            url = yarl.URL(link['href'])
            if url.is_absolute():
                abs=True
            else:
                url = self.root.join(url)
            if (url.host != self.root.host or url.fragment or
                        url in self.visited_urls):
                continue

            yield from self.new_urls.put(url)
            link['href'] = url.relative()

        # find all images and scripts
        for elem in soup.findAll(src=True):
            abs = False
            url = yarl.URL(elem['src'])
            if url.is_absolute():
                abs = True
            else:
                url = self.root.join(url)

            yield from self.new_urls.put(url)
            elem['src']=url.relative()

        # find all action elements
        for act_link in soup.findAll(action=True):
            abs = False
            url = yarl.URL(act_link['action'])
            if url.is_absolute():
                abs = True
            else:
                url = self.root.join(url)

            yield from self.new_urls.put(url)
            act_link['action'] = url.relative()

        # prevent redirects
        for redir in soup.findAll(True, attrs={'name': re.compile('redirect.*')}):
            redir['value'] = yarl.URL(redir['value']).relative()

        return soup

    @asyncio.coroutine
    def get_body(self):
        while not self.new_urls.empty():
            current_url = yield from self.new_urls.get()
            self.visited_urls.append(current_url)
            file_name = current_url.name if current_url.name else 'index.html'
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
            except Exception as e:
                print(e)
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
    c = Cloner(args.target)
    loop.run_until_complete(c.run())


if __name__ == '__main__':
    main()
