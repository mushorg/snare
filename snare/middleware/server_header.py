from aiohttp import web

@web.middleware
async def server_header_middleware(request, handler):
    response = await handler(request)

    # REMOVE aiohttp server header
    if "Server" in response.headers:
        del response.headers["Server"]

    # ADD FAKE REALISTIC SERVER
    response.headers["Server"] = "nginx"

    return response
