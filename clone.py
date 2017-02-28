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

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from asyncio import Queue

import aiohttp
import cssutils
import yarl
from bs4 import BeautifulSoup


class Cloner(object):
    def __init__(self, root):
        self.visited_urls = []
        self.root = self.add_scheme(root)
        if len(self.root.host) < 4:
            sys.exit('invalid taget {}'.format(self.root.host))
        self.target_path = '/opt/snare/pages/{}'.format(self.root.host)

        if not os.path.exists(self.target_path):
            os.mkdir(self.target_path)

        self.new_urls = Queue()
        self.meta = {}

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
        if url.scheme == ("data" or "javascript"):
            return url.human_repr()
        if not url.is_absolute():
            url = self.root.join(url)
        #get subdomains
        host = url.host
        if host is not None:
            host_parts = host.split(".")

            if len(host_parts) > 2:
                host = host_parts[-2]+"."+host_parts[-1]

        if check_host:
            if host != self.root.host or url.fragment:
                return None

        if url.human_repr() not in self.visited_urls:
            yield from self.new_urls.put(url)

        try:
            res = url.relative().human_repr()
        except ValueError:
            print(url)
        return res

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
            if redir['value'] != "":
                redir['value'] = yarl.URL(redir['value']).relative().human_repr()

        return soup

    def _make_filename(self, url):
        host  = url.host
        file_name = url.relative().human_repr()
        if file_name == '/' or file_name == "":
            if host == self.root.host:
                file_name = 'index.html'
            else:
                file_name = host
        m = hashlib.md5()
        m.update(file_name.encode('utf-8'))
        hash_name = m.hexdigest()
        return file_name, hash_name

    @asyncio.coroutine
    def get_body(self, session):
        while not self.new_urls.empty():
            current_url = yield from self.new_urls.get()
            if current_url.human_repr() in self.visited_urls:
                continue
            self.visited_urls.append(current_url.human_repr())
            file_name, hash_name = self._make_filename(current_url)
            print('name: ', file_name)
            self.meta[file_name] = {}

            data = None
            content_type = None
            try:
                with aiohttp.Timeout(10.0):
                    response = yield from session.get(current_url)
                    content_type = response.content_type
                    data = yield from response.read()
            except (aiohttp.ClientError, asyncio.TimeoutError) as client_error:
                print(client_error)
            else:
                yield from response.release()
            if data is not None:
                self.meta[file_name]['hash'] = hash_name
                self.meta[file_name]['content_type'] = content_type
                if content_type == 'text/html':
                    soup = yield from self.replace_links(data)
                    data = str(soup).encode()
                with open(os.path.join(self.target_path, hash_name), 'wb') as index_fh:
                    index_fh.write(data)
                if content_type == 'text/css':
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
        session = aiohttp.ClientSession()
        try:
            yield from self.new_urls.put(self.root)
            yield from self.get_body(session)
        except KeyboardInterrupt:
            raise
        finally:
            with open(os.path.join(self.target_path, 'meta.json'), 'w') as mj:
                json.dump(self.meta, mj)
            yield from session.close()


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
    try:
        cloner = Cloner(args.target)
        loop.run_until_complete(cloner.run())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
