import argparse
import os
import shutil
import unittest
from unittest.mock import Mock

import multidict
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from snare.server import HttpRequestHandler, MAX_RAW_POST_DATA
from snare.utils.asyncmock import AsyncMock
from snare.utils.page_path_generator import generate_unique_path

# What CVE-2024-4577 exploit attempts send in the request body.
PHP_PAYLOAD = '<?php die(@md5("PHP-CGI")); system("id; uname -a"); ?>'


class TestPostDataRaw(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.page_path = generate_unique_path()
        os.makedirs(self.page_path)
        args = argparse.Namespace(
            tanner="tanner.example.org",
            page_dir=self.page_path.rsplit("/")[-1],
            full_page_path=self.page_path,
            no_dorks=True,
            server_header="test_server",
            slurp_enabled=False,
        )
        self.handler = HttpRequestHandler({}, args, b"9c10172f-7ce2-4fb4-b1c6-abc70141db56")
        self.submitted = []

        async def submit_data(data):
            self.submitted.append(data)
            return dict(response=dict(message=dict(detection={"type": 1}, sess_uuid="test_uuid")))

        self.handler.tanner_handler.submit_data = submit_data
        self.handler.tanner_handler.parse_tanner_response = AsyncMock(
            return_value=("<html></html>", multidict.CIMultiDict([("Content-Type", "text/html")]), 200)
        )
        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", self.handler.handle_request)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        shutil.rmtree(self.page_path, ignore_errors=True)

    async def post(self, body, content_type):
        resp = await self.client.post("/cgi-bin/php", data=body, headers={"Content-Type": content_type})
        self.assertEqual(resp.status, 200)
        return self.submitted[-1]

    async def test_form_encoded_raw_body_is_forwarded(self):
        data = await self.post(PHP_PAYLOAD, "application/x-www-form-urlencoded")
        self.assertEqual(data["post_data_raw"], PHP_PAYLOAD)

    async def test_non_form_content_type_is_not_lost(self):
        # request.post() returns nothing for text/plain, so before this
        # change the payload was not logged at all.
        data = await self.post(PHP_PAYLOAD, "text/plain")
        self.assertEqual(data["post_data"], {})
        self.assertEqual(data["post_data_raw"], PHP_PAYLOAD)

    async def test_normal_form_is_still_parsed(self):
        data = await self.post("user=bob&pass=secret", "application/x-www-form-urlencoded")
        self.assertEqual(data["post_data"], {"user": "bob", "pass": "secret"})
        self.assertEqual(data["post_data_raw"], "user=bob&pass=secret")

    async def test_raw_body_is_capped(self):
        data = await self.post("A" * (MAX_RAW_POST_DATA + 500), "text/plain")
        self.assertEqual(len(data["post_data_raw"]), MAX_RAW_POST_DATA)

    async def test_invalid_utf8_does_not_crash(self):
        data = await self.post(b"\xff\xfe<?php ?>", "text/plain")
        self.assertIn("<?php ?>", data["post_data_raw"])

    async def test_get_request_has_no_raw_body(self):
        resp = await self.client.get("/")
        self.assertEqual(resp.status, 200)
        self.assertNotIn("post_data_raw", self.submitted[-1])


if __name__ == "__main__":
    unittest.main()
