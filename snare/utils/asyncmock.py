from unittest.mock import Mock


class AsyncMock(Mock):
    """Custom class defined to mock asyncio coroutines"""

    def __call__(self, *args, **kwargs):
        sup = super(AsyncMock, self)

        async def coro():
            return sup.__call__(*args, **kwargs)

        return coro()

    def __await__(self):
        return self().__await__()
