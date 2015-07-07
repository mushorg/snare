#!/usr/bin/env python3

import re
import os


from urllib.parse import urlparse

import asyncio

import aiohttp


class Crawler:

    def __init__(self, loop):
        self.connector = aiohttp.TCPConnector(share_cookies=True, loop=loop)

    @asyncio.coroutine
    def get_body(self, root_url):
        domain = root_url.rsplit('/', 1)[1]
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
    loop = asyncio.get_event_loop()

    c = Crawler(loop)
    loop.run_until_complete(c.run('http://page_name'))


if __name__ == '__main__':
    main()
