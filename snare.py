#!/usr/bin/python3

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
import configparser
import grp
import json
import multiprocessing
import os
import pwd
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from urllib.parse import urlparse, unquote, parse_qsl

import aiohttp
import git
import mimetypes
import pip
from aiohttp import MultiDict

try:
    from aiohttp.web import StaticResource as StaticRoute
except ImportError:
    from aiohttp.web import StaticResource

from bs4 import BeautifulSoup
import cssutils
import netifaces as ni

import logger

class HttpRequestHandler(aiohttp.server.ServerHttpProtocol):
    def __init__(self, run_args, debug=False, keep_alive=75, **kwargs):
        self.dorks = []
        self.run_args = run_args
        self.sroute = StaticRoute(
            name=None, prefix='/',
            directory='/opt/snare/pages/{}'.format(run_args.page_dir)
        )
        super().__init__(debug=debug, keep_alive=keep_alive, access_log=None, **kwargs)

    @asyncio.coroutine
    def get_dorks(self):
        dorks = None
        try:
            with aiohttp.Timeout(10.0):
                with aiohttp.ClientSession() as session:
                    r = yield from session.get(
                        'http://{0}:8090/dorks'.format(self.run_args.tanner)
                    )
                    try:
                        dorks = yield from r.json()
                    except json.decoder.JSONDecodeError as e:
                        print(e)
                    finally:
                        r.release()
        except:
            print('Dorks timeout')
        return dorks['response']['dorks'] if dorks else []

    @asyncio.coroutine
    def submit_slurp(self, data):
        try:
            with aiohttp.Timeout(10.0):
                with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                    r = yield from session.post(
                        'https://{0}:8080/api?auth={1}&chan=snare_test&msg={2}'.format(
                            self.run_args.slurp_host, self.run_args.slurp_auth, data
                        ), data=json.dumps(data)
                    )
                    assert r.status == 200
                    r.close()
        except Exception as e:
            print(e)

    def create_data(self, request, response_status):
        data = dict(
            method=None,
            path=None,
            headers=None,
            uuid=snare_uuid.decode('utf-8'),
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
                data['cookies'] = {cookie.split('=')[0]: cookie.split('=')[1] for cookie in header['Cookie'].split('; ')}
        return data

    @asyncio.coroutine
    def submit_data(self, data):
        event_result = None
        try:
            with aiohttp.Timeout(10.0):
                with aiohttp.ClientSession() as session:
                    r = yield from session.post(
                        'http://{0}:8090/event'.format(self.run_args.tanner), data=json.dumps(data)
                    )
                    try:
                        event_result = yield from r.json()
                    except json.decoder.JSONDecodeError as e:
                        print(e, data)
                    finally:
                        r.release()
        except Exception as e:
            raise e
        return event_result

    @asyncio.coroutine
    def handle_html_content(self, content):
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
                    self.dorks = yield from self.get_dorks()
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

    @asyncio.coroutine
    def handle_request(self, request, payload):
        print('Request path: {0}'.format(request.path))
        data = self.create_data(request, 200)
        if request.method == 'POST':
            post_data = yield from payload.read()
            post_data = MultiDict(parse_qsl(post_data.decode('utf-8')))
            print('POST data:')
            for key, val in post_data.items():
                print('\t- {0}: {1}'.format(key, val))
            data['post_data'] = dict(post_data)

        # Submit the event to the TANNER service
        event_result = yield from self.submit_data(data)

        #Log the URL to /opt/snare/snare.log
        ip=self.transport.get_extra_info('peername')[0]
        self.logger.info('Source IP %s - - Requested path %s', ip, self.run_args.page_dir + request.path)
        
        # Log the event to slurp service if enabled
        if self.run_args.slurp_enabled:
            yield from self.submit_slurp(request.path)
        response = aiohttp.Response(
            self.writer, status=200, http_version=request.version
        )
        content_type = None
        mimetypes.add_type('text/html','.php')
        mimetypes.add_type('text/html', '.aspx')
        base_path = os.path.join('/opt/snare/pages', self.run_args.page_dir)
        if event_result is not None and ('payload' in event_result['response']['message']['detection'] and event_result['response']['message']['detection']['payload'] is not None):
            payload_content = event_result['response']['message']['detection']['payload']
            if type(payload_content) == dict:
                if payload_content['page'].startswith('/'):
                    payload_content['page'] = payload_content['page'][1:]
                page_path = os.path.join(base_path, payload_content['page'])
                content = '<html><body></body></html>'
                if os.path.exists(page_path):
                    content_type = mimetypes.guess_type(page_path)[0]
                    with open(page_path, encoding='utf-8') as p:
                        content = p.read()
                soup = BeautifulSoup(content, 'html.parser')
                script_tag = soup.new_tag('div')
                script_tag.append(BeautifulSoup(payload_content['value'], 'html.parser'))
                soup.body.append(script_tag)
                content = str(soup).encode()

            else:
                content_type = mimetypes.guess_type(payload_content)[0]
                content = payload_content.encode('utf-8')
        else:
            query = None
            if request.path == '/':
                parsed_url = self.run_args.index_page
            else:
                parsed_url = urlparse(unquote(request.path))
                if parsed_url.query:
                    query = '?' + parsed_url.query
                parsed_url = parsed_url.path
                if parsed_url.startswith('/'):
                    parsed_url = parsed_url[1:]
            path = os.path.normpath(os.path.join(base_path, parsed_url))
            if os.path.isfile(path) and path.startswith(base_path):
                content_type = mimetypes.guess_type(path)[0]
                with open(path, 'rb') as fh:
                    content = fh.read()
                if content_type:
                    if 'text/html' in content_type:
                        content = yield from self.handle_html_content(content)
            else:
                content_type = None
                content = None
                response = aiohttp.Response(
                    self.writer, status=404, http_version=request.version
                )
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
        yield from response.write_eof()

    def handle_error(self, status=500, message=None,
                     payload=None, exc=None, headers=None, reason=None):
        super().handle_error(status, message, payload, exc, headers, reason)

        data = self.create_data(message, status)
        data['error'] = exc
        self.submit_data(data)


def create_initial_config():
    cfg = configparser.ConfigParser()
    cfg['WEB-TOOLS'] = dict(google='', bing='')
    with open('/opt/snare/snare.cfg', 'w') as configfile:
        cfg.write(configfile)


def snare_setup():
    if os.getuid() != 0:
        print('Snare has to be started as root!')
        sys.exit(1)
    # Create folders
    if not os.path.exists('/opt/snare'):
        os.mkdir('/opt/snare')
    if not os.path.exists('/opt/snare/pages'):
        os.mkdir('/opt/snare/pages')
    # Write pid to pid file
    with open('/opt/snare/snare.pid', 'wb') as pid_fh:
        pid_fh.write(str(os.getpid()).encode('utf-8'))
    # Config file
    if not os.path.exists('/opt/snare/snare.cfg'):
        create_initial_config()
    # Read or create the sensor id
    uuid_file_path = '/opt/snare/snare.uuid'
    if os.path.exists(uuid_file_path):
        with open(uuid_file_path, 'rb') as uuid_fh:
            snare_uuid = uuid_fh.read()
        return snare_uuid
    else:
        with open(uuid_file_path, 'wb') as uuid_fh:
            snare_uuid = str(uuid.uuid4()).encode('utf-8')
            uuid_fh.write(snare_uuid)
        return snare_uuid


def drop_privileges():
    uid_name = 'nobody'
    wanted_user = pwd.getpwnam(uid_name)
    gid_name = grp.getgrgid(wanted_user.pw_gid).gr_name
    wanted_group = grp.getgrnam(gid_name)
    os.setgid(wanted_group.gr_gid)
    os.setuid(wanted_user.pw_uid)
    new_user = pwd.getpwuid(os.getuid())
    new_group = grp.getgrgid(os.getgid())
    print('privileges dropped, running as "{}:{}"'.format(new_user.pw_name, new_group.gr_name))


def add_meta_tag(page_dir, index_page):
    google_content = config['WEB-TOOLS']['google']
    bing_content = config['WEB-TOOLS']['bing']

    if not google_content and not bing_content:
        return

    main_page_path = os.path.join('/opt/snare/pages/', page_dir, index_page)
    with open(main_page_path) as main:
        main_page = main.read()
    soup = BeautifulSoup(main_page, 'html.parser')

    if (google_content and
                soup.find("meta", attrs={"name": "google-site-verification"}) is None):
        google_meta = soup.new_tag('meta')
        google_meta.attrs['name'] = 'google-site-verification'
        google_meta.attrs['content'] = google_content
        soup.head.append(google_meta)
    if (bing_content and
                soup.find("meta", attrs={"name": "msvalidate.01"}) is None):
        bing_meta = soup.new_tag('meta')
        bing_meta.attrs['name'] = 'msvalidate.01'
        bing_meta.attrs['content'] = bing_content
        soup.head.append(bing_meta)

    html = soup.prettify("utf-8")
    with open(main_page_path, "wb") as file:
        file.write(html)


def compare_version_info(timeout):
    while True:
        repo = git.Repo(os.getcwd())
        try:
            rem = repo.remote()
            res = rem.fetch()
            diff_list = res[0].commit.diff(repo.heads.master)
        except TimeoutError:
            print('timeout fetching the repository version')
        else:
            if diff_list:
                print('you are running an outdated version, SNARE will be updated and restarted')
                repo.git.reset('--hard')
                repo.heads.master.checkout()
                repo.git.clean('-xdf')
                repo.remotes.origin.pull()
                pip.main(['install', '-r', 'requirements.txt'])
                os.execv(sys.executable, [sys.executable, __file__] + sys.argv[1:])
                return
            else:
                print('you are running the latest version')
            time.sleep(timeout)


def parse_timeout(timeout):
    result = None
    timeouts_coeff = {
        'M': 60,
        'H': 3600,
        'D': 86400
    }

    form = timeout[-1]
    if form not in timeouts_coeff.keys():
        print('Bad timeout format, default will be used')
        parse_timeout('24H')
    else:
        result = int(timeout[:-1])
        result *= timeouts_coeff[form]
    return result


@asyncio.coroutine
def check_tanner_connection():
    with aiohttp.ClientSession() as client:
        req_url = 'http://{}:8090'.format(args.tanner)
        try:
            resp = yield from client.get(req_url)
        except aiohttp.errors.ClientOSError:
            print("Can't connect to tanner host {}".format(req_url))
            exit(1)
        else:
            yield from resp.release()


if __name__ == '__main__':
    print("""
   _____ _   _____    ____  ______
  / ___// | / /   |  / __ \/ ____/
  \__ \/  |/ / /| | / /_/ / __/
 ___/ / /|  / ___ |/ _, _/ /___
/____/_/ |_/_/  |_/_/ |_/_____/

    """)
    snare_uuid = snare_setup()
    parser = argparse.ArgumentParser()
    page_group = parser.add_mutually_exclusive_group(required=True)
    page_group.add_argument("--page-dir", help="name of the folder to be served")
    page_group.add_argument("--list-pages", help="list available pages", action='store_true')
    parser.add_argument("--index-page", help="file name of the index page", default='index.html')
    parser.add_argument("--port", help="port to listen on", default='8080')
    parser.add_argument("--interface", help="interface to bind to")
    parser.add_argument("--host-ip", help="host ip to bind to", default='localhost')
    parser.add_argument("--debug", help="run web server in debug mode", default=False)
    parser.add_argument("--tanner", help="ip of the tanner service", default='tanner.mushmush.org')
    parser.add_argument("--skip-check-version", help="skip check for update", action='store_true')
    parser.add_argument("--slurp-enabled", help="enable nsq logging", action='store_true')
    parser.add_argument("--slurp-host", help="nsq logging host", default='slurp.mushmush.org')
    parser.add_argument("--slurp-auth", help="nsq logging auth", default='slurp')
    parser.add_argument("--config", help="snare config file", default='snare.cfg')
    parser.add_argument("--auto-update", help="auto update SNARE if new version available ", default=True)
    parser.add_argument("--update-timeout", help="update snare every timeout ", default='24H')
    parser.add_argument("--server-header", help="set server-header", default='nginx')
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read('/opt/snare/' + args.config)

    if args.list_pages:
        print('Available pages:\n')
        for page in os.listdir('/opt/snare/pages/'):
            print('\t- {}'.format(page))
        print('\nuse with --page-dir {page_name}\n\n')
        exit()
    if not os.path.exists('/opt/snare/pages/' + args.page_dir):
        print("--page-dir: {0} does not exist".format(args.page_dir))
        exit()
    if not os.path.exists('/opt/snare/pages/' + args.page_dir + "/" + args.index_page):
        print('can\'t crate meta tag')
    else:
        add_meta_tag(args.page_dir, args.index_page)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_tanner_connection())

    pool = ProcessPoolExecutor(max_workers=multiprocessing.cpu_count())
    compare_version_fut = None
    if args.auto_update is True:
        timeout = parse_timeout(args.update_timeout)
        compare_version_fut = loop.run_in_executor(pool, compare_version_info, timeout)

    if args.host_ip == 'localhost' and args.interface:
        host_ip = ni.ifaddresses(args.interface)[2][0]['addr']
    else:
        host_ip = args.host_ip
    future = loop.create_server(
        lambda: HttpRequestHandler(args, debug=args.debug, keep_alive=75),
        args.interface, int(args.port))
    srv = loop.run_until_complete(future)

    #log info
    info_log_file_name = '/opt/snare/snare.log'
    logger.Logger.create_logger(info_log_file_name, __package__)
    print("Info logs will be stored in", info_log_file_name)

    drop_privileges()
    print('serving on {0} with uuid {1}'.format(srv.sockets[0].getsockname()[:2], snare_uuid.decode('utf-8')))
    try:
        loop.run_forever()
    except (KeyboardInterrupt, TypeError) as e:
        print(e)
    finally:
        if compare_version_fut:
            compare_version_fut.cancel()
        srv.close()
        loop.run_until_complete(srv.wait_closed())
        loop.close()
