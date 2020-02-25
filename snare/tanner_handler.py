import re
import os
from urllib.parse import unquote
import mimetypes
import json
import logging
import aiohttp
from bs4 import BeautifulSoup
from snare.html_handler import HtmlHandler


class TannerHandler():
    def __init__(self, run_args, meta, snare_uuid):
        self.run_args = run_args
        self.meta = meta
        self.dir = '/opt/snare/pages/{}'.format(run_args.page_dir)
        self.snare_uuid = snare_uuid
        self.html_handler = HtmlHandler(run_args.no_dorks, run_args.tanner)
        self.logger = logging.getLogger(__name__)

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
            data['path'] = request.path_qs
            if 'Cookie' in header:
                data['cookies'] = {
                    cookie.split('=')[0]: cookie.split('=')[1] for cookie in header['Cookie'].split(';')
                    }
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
                    event_result = await r.json(content_type=None)
                except json.decoder.JSONDecodeError as e:
                    self.logger.error('Error submitting data: {} {}'.format(e, data))
                finally:
                    await r.release()
        except Exception as e:
            self.logger.exception('Exception: %s', e)
            raise e
        return event_result

    async def parse_tanner_response(self, requested_name, detection):
        content_type = None
        content = None
        status_code = 200
        headers = {}
        # Creating a regex object for the pattern of multiple contiguous forward slashes
        p = re.compile('/+')
        # Substituting all occurrences of the pattern with single forward slash
        requested_name = p.sub('/', requested_name)

        if detection['type'] == 1:
            possible_requests = [requested_name]
            query_start = requested_name.find('?')
            if query_start != -1:
                possible_requests.append(requested_name[:query_start])

            file_name = None
            for requested_name in possible_requests:
                if requested_name == '/':
                    requested_name = self.run_args.index_page
                if requested_name[-1] == '/':
                    requested_name = requested_name[:-1]
                requested_name = unquote(requested_name)
                try:
                    file_name = self.meta[requested_name]['hash']
                    content_type = self.meta[requested_name]['content_type']
                except KeyError:
                    pass
                else:
                    break
            if not file_name:
                status_code = 404
            else:
                path = os.path.join(self.dir, file_name)
                if os.path.isfile(path):
                    with open(path, 'rb') as fh:
                        content = fh.read()
                    if content_type:
                        if 'text/html' in content_type:
                            content = await self.html_handler.handle_content(content)

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
                    content_type = r'text/html'

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

        return content, content_type, headers, status_code
