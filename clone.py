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
import logger
import logging


class Cloner(object):
    def __init__(self, root, max_depth):
        self.visited_urls = []
        self.root, self.error_page  = self.add_scheme(root)
        self.max_depth = max_depth
        self.moved_root = None
        if len(self.root.host) < 4:
            sys.exit('invalid taget {}'.format(self.root.host))
        self.target_path = '/opt/snare/pages/{}'.format(self.root.host)

        if not os.path.exists(self.target_path):
            os.mkdir(self.target_path)
            
        self.new_urls = Queue()
        self.meta = {}
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def add_scheme(url):
        if yarl.URL(url).scheme:
            new_url = yarl.URL(url)
        else:
            new_url = yarl.URL('http://' + url)
        err_url = yarl.URL('http://' + url + '/status_404')
        return new_url, err_url

    async def process_link(self, url, level, check_host=False):
        try:
            url = yarl.URL(url)
        except UnicodeError:
            return None
        if url.scheme == ("data" or "javascript" or "file"):
            return url.human_repr()
        if not url.is_absolute():
            if self.moved_root is None:
                url = self.root.join(url)
            else:
                url = self.moved_root.join(url)

        host = url.host

        if check_host:
            if (host != self.root.host and self.moved_root is None) or \
                    url.fragment or \
                    (self.moved_root is not None and host != self.moved_root.host):
                return None

        if url.human_repr() not in self.visited_urls and (level + 1) <= self.max_depth:
            await self.new_urls.put((url, level + 1))

        res = None
        try:
            res = url.relative().human_repr()
        except ValueError:
            self.logger.error(url)
        return res

    async def replace_links(self, data, level):
        soup = BeautifulSoup(data, 'html.parser')

        # find all relative links
        for link in soup.findAll(href=True):
            res = await self.process_link(link['href'], level, check_host=True)
            if res is not None:
                link['href'] = res

        # find all images and scripts
        for elem in soup.findAll(src=True):
            res = await self.process_link(elem['src'], level)
            if res is not None:
                elem['src'] = res

        # find all action elements
        for act_link in soup.findAll(action=True):
            res = await self.process_link(act_link['action'], level)
            if res is not None:
                act_link['action'] = res

        # prevent redirects
        for redir in soup.findAll(True, attrs={'name': re.compile('redirect.*')}):
            if redir['value'] != "":
                redir['value'] = yarl.URL(redir['value']).relative().human_repr()

        return soup

    def _make_filename(self, url):
        host = url.host
        if url.is_absolute():
            file_name = url.relative().human_repr()
        else:
            file_name = url.human_repr()
        if not file_name.startswith('/'):
            file_name = "/" + file_name

        if file_name == '/' or file_name == "":
            if host == self.root.host or (self.moved_root is not None and self.moved_root.host == host):
                file_name = '/index.html'
            else:
                file_name = host
        m = hashlib.md5()
        m.update(file_name.encode('utf-8'))
        hash_name = m.hexdigest()
        return file_name, hash_name

    async def get_body(self, session):
        while not self.new_urls.empty():
            current_url, level = await self.new_urls.get()
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
                    response = await session.get(current_url, headers={'Accept': 'text/html'})
                    content_type = response.content_type
                    data = await response.read()
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as client_error:
                self.logger.error(client_error)
            else:
                await response.release()
            if data is not None:
                self.meta[file_name]['hash'] = hash_name
                self.meta[file_name]['content_type'] = content_type
                if content_type == 'text/html':
                    soup = await self.replace_links(data, level)
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
                        if carved_url.human_repr() not in self.visited_urls:
                            await self.new_urls.put((carved_url, level+1))

    async def get_root_host(self):
        try:
            with aiohttp.ClientSession() as session:
                resp = await session.get(self.root)
                if resp._url_obj.host != self.root.host:
                    self.moved_root = resp._url_obj
                resp.close()
        except aiohttp.errors.ClientError as err:
            self.logger.error("Can\'t connect to target host.")
            exit(-1)

    async def run(self):
        session = aiohttp.ClientSession()
        try:
            await self.new_urls.put((self.root, 0))
            await self.new_urls.put((self.error_page,0))
            await self.get_body(session)
        except KeyboardInterrupt:
            raise
        finally:
            with open(os.path.join(self.target_path, 'meta.json'), 'w') as mj:
                json.dump(self.meta, mj)
            await session.close()


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
    parser.add_argument("--target", help="domain of the site to be cloned", required=True)
    parser.add_argument("--max-depth", help="max depth of the cloning", required=False, default=sys.maxsize)
    parser.add_argument("--log_path", help="path to the error log file")
    args = parser.parse_args()
    if args.log_path:
        log_err = args.log_path + "clone.err"
    else:
        log_err = "/opt/snare/clone.err"	
    logger.Logger.create_clone_logger(log_err, __package__)
    print("Error logs will be stored in {}\n".format(log_err))
    try:
        cloner = Cloner(args.target, int(args.max_depth))
        loop.run_until_complete(cloner.get_root_host())
        loop.run_until_complete(cloner.run())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    print("""
    ______ __      ______ _   ____________
   / ____// /     / __  // | / / ____/ __ \\
  / /    / /     / / / //  |/ / __/ / /_/ /
 / /___ / /____ / /_/ // /|  / /___/ _, _/
/_____//______//_____//_/ |_/_____/_/ |_|
    
    """)
    main()
