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
from server import HttpRequestHandler


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

    if (google_content and soup.find("meta", attrs={"name": "google-site-verification"}) is None):
        google_meta = soup.new_tag('meta')
        google_meta.attrs['name'] = 'google-site-verification'
        google_meta.attrs['content'] = google_content
        soup.head.append(google_meta)
    if (bing_content and soup.find("meta", attrs={"name": "msvalidate.01"}) is None):
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


async def check_tanner():
    vm = VersionManager()
    async with aiohttp.ClientSession() as client:
        req_url = 'http://{}:8090/version'.format(args.tanner)
        try:
            resp = await client.get(req_url)
            result = await resp.json()
            version = result["version"]
            vm.check_compatibility(version)
        except aiohttp.ClientOSError:
            print("Can't connect to tanner host {}".format(req_url))
            exit(1)
        else:
            await resp.release()


if __name__ == '__main__':
    print(r"""
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
    parser.add_argument("--server-header", help="set server-header", default='nignx/1.3.8')
    parser.add_argument("--log-dir", help="path to directory of the log file", default='/opt/snare/')
    args = parser.parse_args()
    base_path = '/opt/snare/'
    base_page_path = '/opt/snare/pages/'
    config = configparser.ConfigParser()
    config.read(os.path.join(base_path, args.config))
    
    log_debug = args.log_dir + "snare.log"
    log_err = args.log_dir + "snare.err"      
    logger.Logger.create_logger(log_debug, log_err, __package__)

    if args.list_pages:
        print('Available pages:\n')
        for page in os.listdir(base_page_path):
            print('\t- {}'.format(page))
        print('\nuse with --page-dir {page_name}\n\n')
        exit()
    full_page_path = os.path.join(base_page_path, args.page_dir)
    if not os.path.exists(full_page_path):
        print("--page-dir: {0} does not exist".format(args.page_dir))
        exit()
    args.index_page = os.path.join("/", args.index_page)

    if not os.path.exists(os.path.join(full_page_path, 'meta.json')):
        conv = Converter()
        conv.convert(full_page_path)
        print("pages was converted. Try to clone again for the better result.")

    with open(os.path.join(full_page_path, 'meta.json')) as meta:
        meta_info = json.load(meta)
    if not os.path.exists(os.path.join(base_page_path, args.page_dir,
                                       os.path.join(meta_info[args.index_page]['hash']))):
        print('can\'t create meta tag')
    else:
        add_meta_tag(args.page_dir, meta_info[args.index_page]['hash'])
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_tanner())

    pool = ProcessPoolExecutor(max_workers=multiprocessing.cpu_count())
    compare_version_fut = None
    if args.auto_update is True:
        timeout = parse_timeout(args.update_timeout)
        compare_version_fut = loop.run_in_executor(pool, compare_version_info, timeout)

    if args.host_ip == 'localhost' and args.interface:
        args.host_ip = ni.ifaddresses(args.interface)[2][0]['addr']

    app = HttpRequestHandler(meta_info, args, snare_uuid, debug=args.debug, keep_alive=75)
    drop_privileges()
    print('serving with uuid {0}'.format(snare_uuid.decode('utf-8')))
    print("Debug logs will be stored in", log_debug)
    print("Error logs will be stored in", log_err)
    try:
        app.start()
    except (KeyboardInterrupt, TypeError) as e:
        print(e)
    finally:
        if compare_version_fut:
            compare_version_fut.cancel()
