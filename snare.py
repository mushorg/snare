#!/usr/bin/python3

import os
import sys

import asyncio
from aiohttp import web

import redis


@asyncio.coroutine
def handle(request):
    print(dir(request))
    path = request.match_info.get('path', '/')
    return web.Response(body=path.encode('utf-8'))


@asyncio.coroutine
def init(inner_loop, page_name):
    app = web.Application(loop=inner_loop)
    app.router.add_static('/', path='/opt/snare/pages/{}'.format(page_name))
    app.router.add_route('*', '/{path:.*}', handle)

    srv = yield from loop.create_server(
        app.make_handler(),
        '127.0.0.1', 8080
    )
    print("Server started at http://127.0.0.1:8080")
    return srv


if __name__ == '__main__':
    if os.getuid() != 0:
        print('Snare has to be started as root!')
        sys.exit(1)
    if not os.path.exists('/opt/snare'):
        os.mkdir('/opt/snare')
    if not os.path.exists('/opt/snare/pages'):
        os.mkdir('/opt/snare/pages')
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop, 'page_name'))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('Bye\n')
