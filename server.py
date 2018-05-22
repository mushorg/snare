import argparse
import asyncio
import configparser
import grp
import json
import mimetypes
import multiprocessing
import os
import pwd
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from urllib.parse import urlparse, unquote, parse_qsl
from versions_manager import VersionManager
import aiohttp
import git
import pip
from aiohttp import MultiDict
import re
import logging
import logger

try:
    from aiohttp.web import StaticResource as StaticRoute
except ImportError:
    from aiohttp.web import StaticResource

from bs4 import BeautifulSoup
import cssutils
import netifaces as ni
from converter import Converter


class HttpRequestHandler(aiohttp.server.ServerHttpProtocol):
    def __init__(self, meta, run_args, snare_uuid, debug=False, keep_alive=75, **kwargs):
        self.dorks = []

        self.run_args = run_args
        self.dir = '/opt/snare/pages/{}'.format(run_args.page_dir)

        self.meta = meta
        self.snare_uuid = snare_uuid
        
        self.logger = logging.getLogger(__name__)

        self.sroute = StaticRoute(
            name=None, prefix='/',
            directory=self.dir
        )
        super().__init__(debug=debug, keep_alive=keep_alive, access_log=None, **kwargs)

    async def get_dorks(self):
        dorks = None
        try:
            with aiohttp.Timeout(10.0):
                with aiohttp.ClientSession() as session:
                    r = await session.get(
                        'http://{0}:8090/dorks'.format(self.run_args.tanner)
                    )
                    try:
                        dorks = await r.json()
                    except json.decoder.JSONDecodeError as e:
                        self.logger.error('Error getting dorks: %s', e)
                    finally:
                        await r.release()
        except asyncio.TimeoutError:
            self.logger.info('Dorks timeout')
        return dorks['response']['dorks'] if dorks else []

    async def submit_slurp(self, data):
        try:
            with aiohttp.Timeout(10.0):
                with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                    r = await session.post(
                        'https://{0}:8080/api?auth={1}&chan=snare_test&msg={2}'.format(
                            self.run_args.slurp_host, self.run_args.slurp_auth, data
                        ), data=json.dumps(data)
                    )
                    assert r.status == 200
                    r.close()
        except Exception as e:
            self.logger.error('Error submitting slurp: %s', e)

    def create_data(self, request, response_status):
        data = dict(
            method=None,
            path=None,
            headers=None,
            uuid=self.snare_uuid.decode('utf-8'),
            peer=None,
            status=response_status
        )
        if self.transport:
            peer = dict(
                ip=self.transport.get_extra_info('peername')[0],
                port=self.transport.get_extra_info('peername')[1]
            )
            data['peer'] = peer
        if request:
            header = {key: value for (key, value) in request.headers.items()}
            data['method'] = request.method
            data['headers'] = header
            data['path'] = request.path
            if ('Cookie' in header):
                data['cookies'] = {cookie.split('=')[0]: cookie.split('=')[1] for cookie in header['Cookie'].split(';')}
        return data

    async def submit_data(self, data):
        event_result = None
        try:
            with aiohttp.Timeout(10.0):
                with aiohttp.ClientSession() as session:
                    r = await session.post(
                        'http://{0}:8090/event'.format(self.run_args.tanner), data=json.dumps(data)
                    )
                    try:
                        event_result = await r.json()
                    except json.decoder.JSONDecodeError as e:
                        self.logger.error('Error submitting data: {} {}'.format(e, data))
                    finally:
                        await r.release()
        except Exception as e:
            raise e
        return event_result

    async def handle_html_content(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        for p_elem in soup.find_all('p'):
            if p_elem.findChildren():
                continue
            css = None
            if 'style' in p_elem.attrs:
                css = cssutils.parseStyle(p_elem.attrs['style'])
            text_list = p_elem.text.split()
            p_new = soup.new_tag('p', style=css.cssText if css else None)
            for idx, word in enumerate(text_list):
                # Fetch dorks if required
                if len(self.dorks) <= 0:
                    self.dorks = await self.get_dorks()
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

    async def handle_request(self, request, payload):
        self.logger.info('Request path: {0}'.format(request.path))
        data = self.create_data(request, 200)
        if request.method == 'POST':
            post_data = await payload.read()
            post_data = MultiDict(parse_qsl(post_data.decode('utf-8')))
            self.logger.info('POST data:')
            for key, val in post_data.items():
                self.logger.info('\t- {0}: {1}'.format(key, val))
            data['post_data'] = dict(post_data)

        # Submit the event to the TANNER service
        event_result = await self.submit_data(data)

        # Log the event to slurp service if enabled
        if self.run_args.slurp_enabled:
            await self.submit_slurp(request.path)

        content, content_type, headers, status_code = await self.parse_tanner_response(
            request.path, event_result['response']['message']['detection'])
        response = aiohttp.Response(
            self.writer, status=status_code, http_version=request.version
        )
        for name, val in headers.items():
            response.add_header(name, val)

        response.add_header('Server', self.run_args.server_header)

        if 'cookies' in data and 'sess_uuid' in data['cookies']:
            previous_sess_uuid = data['cookies']['sess_uuid']
        else:
            previous_sess_uuid = None

        if event_result is not None and ('sess_uuid' in event_result['response']['message']):
            cur_sess_id = event_result['response']['message']['sess_uuid']
            if previous_sess_uuid is None or not previous_sess_uuid.strip() or previous_sess_uuid != cur_sess_id:
                response.add_header('Set-Cookie', 'sess_uuid=' + cur_sess_id)

        if not content_type:
            response.add_header('Content-Type', 'text/plain')
        else:
            response.add_header('Content-Type', content_type)
        if content:
            response.add_header('Content-Length', str(len(content)))
        response.send_headers()
        if content:
            response.write(content)
        await response.write_eof()

    async def parse_tanner_response(self, requested_name, detection):
        content_type = None
        content = None
        status_code = 200
        headers = {}
        p = re.compile('/+') # Creating a regex object for the pattern of multiple contiguous forward slashes
        requested_name = p.sub('/', requested_name) # Substituting all occurrences of the pattern with single forward slash
        
        if detection['type'] == 1:
            query_start = requested_name.find('?')
            if query_start != -1:
                requested_name = requested_name[:query_start]

            if requested_name == '/':
                requested_name = self.run_args.index_page
            try:
                if requested_name[-1] == '/':
                    requested_name = requested_name[:-1]  
                requested_name = unquote(requested_name)
                file_name = self.meta[requested_name]['hash']
                content_type = self.meta[requested_name]['content_type']
            except KeyError:
                status_code = 404
                requested_name = '/status_404'
                file_name = self.meta[requested_name]['hash']
                content_type = 'text/html'
                path = os.path.join(self.dir, file_name)
                with open(path, 'rb') as fh:
                    content = fh.read()
                content = await self.handle_html_content(content)
                
            else:
                path = os.path.join(self.dir, file_name)
                if os.path.isfile(path):
                    with open(path, 'rb') as fh:
                        content = fh.read()
                    if content_type:
                        if 'text/html' in content_type:
                            content = await self.handle_html_content(content)

        elif detection['type'] == 2:
            payload_content = detection['payload']
            if payload_content['page']:
                try:
                    file_name = self.meta[payload_content['page']]['hash']
                    content_type = self.meta[payload_content['page']]['content_type']
                    page_path = os.path.join(self.dir, file_name)
                    with open(page_path, encoding='utf-8') as p:
                        content = p.read()
                except KeyError:
                    content = '<html><body></body></html>'
                    content_type = r'text\html'

                soup = BeautifulSoup(content, 'html.parser')
                script_tag = soup.new_tag('div')
                script_tag.append(BeautifulSoup(payload_content['value'], 'html.parser'))
                soup.body.append(script_tag)
                content = str(soup).encode()
            else:
                content_type = mimetypes.guess_type(payload_content['value'])[0]
                content = payload_content['value'].encode('utf-8')

            if 'headers' in payload_content:
                headers = payload_content['headers']
        else:
            payload_content = detection['payload']
            status_code = payload_content['status_code']

        return (content, content_type, headers, status_code)

    async def handle_error(self, status=500, message=None,
                           payload=None, exc=None, headers=None, reason=None):

        data = self.create_data(message, status)
        data['error'] = exc
        await self.submit_data(data)
        super().handle_error(status, message, payload, exc, headers, reason)

