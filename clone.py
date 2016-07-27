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
import argparse
import aiohttp
import cssutils
from bs4 import BeautifulSoup


class Cloner(object):
    @staticmethod
    def make_new_link(url):
        unquote(url)
        parsed = urlparse(url)

        if parsed.path[1:]:
            new_link = parsed.path
        elif parsed.query:
            new_link = '/' + parsed.query
        else:
            new_link = '/index'
        if new_link[-1] == '/':
            new_link = new_link[:-1]
        if '.' not in new_link:
            new_link += '.html'
        if parsed.fragment:
            new_link += '/#' + parsed.fragment
        if parsed.query:
            new_link += '?' + parsed.query

        return new_link

    def replace_links(self, data, domain, urls):
        soup = BeautifulSoup(data, 'html.parser')
        patt = '.*' + domain + '.*'

        # find all relative links
        for link in soup.findAll(True, attrs={'href': re.compile('^((?!http|\/\/|\.\.).)*$')}):
            if link['href'].startswith('/'):
                link['href'] = link['href'][1:]
            abs_link = 'http://' + domain + link['href']
            urls.append(abs_link)

        # find all absolute links
        for link in soup.findAll(True, attrs={'href': re.compile(patt)}):
            urls.append(link['href'])
            link['href'] = self.make_new_link(link['href'])

        # find all images and scripts
        for elem in soup.findAll(True, attrs={'src': re.compile('^((?!http|\/\/|\.\.).)*$')}):
            abs_link = 'http://' + domain + elem['src']
            urls.append(abs_link)

        # find all action elements
        for act_link in soup.findAll(True, attrs={'action': re.compile(patt)}):
            urls.append(act_link['action'])
            act_link['action'] = self.make_new_link(act_link['action'])

        # prevent redirects
        for redir in soup.findAll(True, attrs={'name': re.compile('redirect.*')}):
            redir['value'] = self.make_new_link(redir['value'])

        urls = list(set(urls))
        return soup

    @asyncio.coroutine
    def get_body(self, root_url, urls, visited_urls):
        if not root_url.startswith("http"):
            root_url = 'http://' + root_url
        visited_urls.append(root_url)
        parsed_url = urlparse(root_url)
        if parsed_url.fragment:
            return
        domain = parsed_url.netloc
        if not domain.endswith('/'):
            domain += '/'
        file_name = self.make_new_link(root_url)

        file_path = ''
        patt = '/.*/.*\.'
        if re.match(patt, file_name):
            file_path, file_name = file_name.rsplit('/', 1)
            file_path += '/'
            # if parsed_url.query:
            # file_name += '?' + parsed_url.query
        print('path: ', file_path, 'name: ', file_name)
        if len(domain) < 4:
            sys.exit('invalid taget {}'.format(root_url))
        page_path = '/opt/snare/pages/{}'.format(domain)

        if not os.path.exists(page_path):
            os.mkdir(page_path)

        if file_path and not os.path.exists(page_path + file_path):
            os.makedirs(page_path + file_path)

        data = None
        try:
            with aiohttp.Timeout(10.0):
                with aiohttp.ClientSession() as session:
                    response = yield from session.get(root_url)
                    data = yield from response.read()
        except Exception as e:
            print(e)
        else:
            response.release()
            session.close()
        if data is not None:
            if re.match(re.compile('.*\.(html|php)'), file_name):
                soup = self.replace_links(data, domain, urls)
                data = str(soup).encode()
            with open(page_path + file_path + file_name, 'wb') as index_fh:
                index_fh.write(data)
            if '.css' in file_name:
                css = cssutils.parseString(data)
                for carved_url in cssutils.getUrls(css):
                    if carved_url.startswith('data'):
                        continue
                    carved_url = os.path.normpath(os.path.join(domain, carved_url))
                    if not carved_url.startswith('http'):
                        if carved_url.startswith('..') or carved_url.startswith('/'):
                            carved_url = 'http://' + domain + carved_url
                        else:
                            carved_url = 'http://' + carved_url
                    if carved_url not in visited_urls:
                        urls.insert(0, carved_url)
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
    c = Cloner()
    loop.run_until_complete(c.run(args.target))


if __name__ == '__main__':
    main()
