import os
import sys
import logging
import asyncio
from asyncio import Queue
import hashlib
import json
import re
import aiohttp
import cssutils
import yarl
from bs4 import BeautifulSoup
animation = "|/-\\"


class Cloner(object):
    def __init__(self, root, max_depth, css_validate):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.visited_urls = []
        self.root, self.error_page = self.add_scheme(root)
        self.max_depth = max_depth
        self.moved_root = None
        if (self.root.host is None) or (len(self.root.host) < 4):
            sys.exit('invalid target {}'.format(self.root.host))
        self.target_path = '/opt/snare/pages/{}'.format(self.root.host)
        if not os.path.exists(self.target_path):
            os.mkdir(self.target_path)
        self.css_validate = css_validate
        self.new_urls = Queue()
        self.meta = {}

        self.counter = 0
        self.itr = 0

    @staticmethod
    def add_scheme(url):
        new_url = yarl.URL(url)
        if not new_url.scheme:
            new_url = yarl.URL('http://' + url)
        err_url = new_url.with_path('/status_404').with_query(None).with_fragment(None)
        return new_url, err_url

    @staticmethod
    def get_headers(response):
        ignored_headers_lowercase = [
            'age',
            'cache-control',
            'connection',
            'content-encoding',
            'content-length',
            'date',
            'etag',
            'expires',
            'x-cache',
        ]

        headers = []
        for key, value in response.headers.items():
            if key.lower() not in ignored_headers_lowercase:
                headers.append({key: value})
        return headers

    async def process_link(self, url, level, check_host=False):
        try:
            url = yarl.URL(url)
        except UnicodeError:
            return None
        if url.scheme in ["data", "javascript", "file"]:
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
            self.logger.error("ValueError while processing the %s link", url)
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
            print(animation[self.itr % len(animation)], end="\r")
            self.itr = self.itr + 1
            current_url, level = await self.new_urls.get()
            if current_url.human_repr() in self.visited_urls:
                continue
            self.visited_urls.append(current_url.human_repr())
            file_name, hash_name = self._make_filename(current_url)
            self.logger.debug('Cloned file: %s', file_name)
            self.meta[file_name] = {}
            data = None
            content_type = None
            try:
                response = await session.get(current_url, headers={'Accept': 'text/html'}, timeout=10.0)
                headers = self.get_headers(response)
                content_type = response.content_type
                data = await response.read()
            except (aiohttp.ClientError, asyncio.TimeoutError) as client_error:
                self.logger.error(client_error)
            else:
                await response.release()

            if data is not None:
                self.meta[file_name]['hash'] = hash_name
                self.meta[file_name]['headers'] = headers
                self.counter = self.counter + 1

                if content_type == 'text/html':
                    soup = await self.replace_links(data, level)
                    data = str(soup).encode()
                elif content_type == 'text/css':
                    css = cssutils.parseString(data, validate=self.css_validate)
                    for carved_url in cssutils.getUrls(css):
                        if carved_url.startswith('data'):
                            continue
                        carved_url = yarl.URL(carved_url)
                        if not carved_url.is_absolute():
                            carved_url = self.root.join(carved_url)
                        if carved_url.human_repr() not in self.visited_urls:
                            await self.new_urls.put((carved_url, level + 1))

                with open(os.path.join(self.target_path, hash_name), 'wb') as index_fh:
                    index_fh.write(data)

    async def get_root_host(self):
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.get(self.root)
                if resp.host != self.root.host:
                    self.moved_root = resp.url
                resp.close()
        except aiohttp.ClientError as err:
            self.logger.error("Can\'t connect to target host: %s", err)
            exit(-1)

    async def run(self):
        session = aiohttp.ClientSession()
        try:
            await self.new_urls.put((self.root, 0))
            await self.new_urls.put((self.error_page, 0))
            await self.get_body(session)
        except KeyboardInterrupt:
            raise
        finally:
            with open(os.path.join(self.target_path, 'meta.json'), 'w') as mj:
                json.dump(self.meta, mj)
            await session.close()
