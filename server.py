import asyncio
import json
import mimetypes
import os
import sys
import time
from urllib.parse import unquote
from versions_manager import VersionManager
import aiohttp
from aiohttp import web
import logging
import logger
import multidict
import aiohttp_jinja2
import jinja2

try:
    from aiohttp.web import StaticResource as StaticRoute
except ImportError:
    from aiohttp.web import StaticResource

from bs4 import BeautifulSoup
import cssutils
from middlewares import SnareMiddleware

class HttpRequestHandler():
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

    async def get_dorks(self):
        dorks = None
        try:
            async with aiohttp.ClientSession() as session:
                r = await session.get(
                    'http://{0}:8090/dorks'.format(self.run_args.tanner), timeout=10.0
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
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                r = await session.post(
                    'https://{0}:8080/api?auth={1}&chan=snare_test&msg={2}'.format(
                        self.run_args.slurp_host, self.run_args.slurp_auth, data
                    ), data=json.dumps(data), timeout=10.0
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
        if request.transport:
            peer = dict(
                ip=request.transport.get_extra_info('peername')[0],
                port=request.transport.get_extra_info('peername')[1]
            )
            data['peer'] = peer
        if request.path:
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
            async with aiohttp.ClientSession() as session:
                r = await session.post(
                    'http://{0}:8090/event'.format(self.run_args.tanner), data=json.dumps(data),
					timeout=10.0
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
        if self.run_args.no_dorks is not True:
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

    async def handle_request(self, request):
        self.logger.info('Request path: {0}'.format(request.path))
        data = self.create_data(request, 200)
        if request.method == 'POST':
            post_data = await request.post()
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

        response_headers = multidict.CIMultiDict()
        
        for name, val in headers.items():
            response_headers.add(name, val)

        response_headers.add('Server', self.run_args.server_header)

        if 'cookies' in data and 'sess_uuid' in data['cookies']:
            previous_sess_uuid = data['cookies']['sess_uuid']
        else:
            previous_sess_uuid = None

        if event_result is not None and ('sess_uuid' in event_result['response']['message']):
            cur_sess_id = event_result['response']['message']['sess_uuid']
            if previous_sess_uuid is None or not previous_sess_uuid.strip() or previous_sess_uuid != cur_sess_id:
                response_headers.add('Set-Cookie', 'sess_uuid=' + cur_sess_id)

        if not content_type:
            response_content_type = 'text/plain'
        else:
            response_content_type = content_type
        response = web.Response(
            body=content, status=status_code, headers=response_headers, content_type=response_content_type
        )
        return response

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

    def start(self):
        app = web.Application()
        app.add_routes([web.route('*', '/{tail:.*}', self.handle_request)])
        aiohttp_jinja2.setup(
            app, loader=jinja2.FileSystemLoader(self.dir)
        )
        middleware = SnareMiddleware(self.meta['/status_404']['hash'])
        middleware.setup_middlewares(app)
        web.run_app(app, host=self.run_args.host_ip, port=self.run_args.port)
