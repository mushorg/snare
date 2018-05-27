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
import json
import mimetypes
import multiprocessing
import os
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from urllib.parse import urlparse, unquote, parse_qsl
import aiohttp
import git
import pip
import re
import logging

try:
    from aiohttp.web import StaticResource as StaticRoute
except ImportError:
    from aiohttp.web import StaticResource

from bs4 import BeautifulSoup
import cssutils
import netifaces as ni
from server import HttpRequestHandler
from startup import StartUp
from utils.logger import Logger
from utils.tag_adder import add_meta_tag
from utils.timeout_parser import parse_timeout
from utils.converter import Converter
from utils.versions_manager import VersionManager

if __name__ == '__main__':
    print(r"""
   _____ _   _____    ____  ______
  / ___// | / /   |  / __ \/ ____/
  \__ \/  |/ / /| | / /_/ / __/
 ___/ / /|  / ___ |/ _, _/ /___
/____/_/ |_/_/  |_/_/ |_/_____/

    """)
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
    parser.add_argument("--no-dorks", help="disable the use of dorks", action='store_true')
    parser.add_argument("--log-dir", help="path to directory of the log file", default='/opt/snare/')
    args = parser.parse_args()
    base_path = '/opt/snare/'
    base_page_path = '/opt/snare/pages/'
    startup = StartUp(args)
    snare_uuid = startup.snare_setup()
    config = configparser.ConfigParser()
    config.read(os.path.join(base_path, args.config))
    
    log_debug = args.log_dir + "snare.log"
    log_err = args.log_dir + "snare.err"      
    Logger.create_logger(log_debug, log_err, __package__)

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
        add_meta_tag(args.page_dir, meta_info[args.index_page]['hash'], config)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(startup.check_tanner())

    pool = ProcessPoolExecutor(max_workers=multiprocessing.cpu_count())
    compare_version_fut = None
    if args.auto_update is True:
        timeout = startup.parse_timeout(args.update_timeout)
        compare_version_fut = loop.run_in_executor(pool, startup.compare_version_info, timeout)

    if args.host_ip == 'localhost' and args.interface:
        args.host_ip = ni.ifaddresses(args.interface)[2][0]['addr']

    app = HttpRequestHandler(meta_info, args, snare_uuid, debug=args.debug, keep_alive=75)
    startup.drop_privileges()
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
