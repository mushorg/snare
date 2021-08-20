import argparse
import json
import logging
import os
import re
from typing import Dict, Tuple, Union
from urllib.parse import unquote

import aiohttp
from aiohttp import web
from bs4 import BeautifulSoup
import multidict

from snare.html_handler import HtmlHandler


class TannerHandler:
    def __init__(self, run_args: argparse.Namespace, meta: Dict, snare_uuid: bytes) -> None:
        """Class for handling Tanner communication

        :param run_args: Runtime CLI arguments
        :type run_args: argparse.Namespace
        :param meta: Meta info from meta.json
        :type meta: Dict
        :param snare_uuid: UUID of Snare instance
        :type snare_uuid: bytes
        """
        self.run_args = run_args
        self.meta = meta
        self.dir = run_args.full_page_path
        self.snare_uuid = snare_uuid
        self.html_handler = HtmlHandler(run_args.no_dorks, run_args.tanner)
        self.logger = logging.getLogger(__name__)

    def create_data(self, request: web.Request, response_status: int) -> Dict:
        """Create data to be sent to Tanner from request

        :param request: Incoming request to Snare server
        :type request: web.Request
        :param response_status: Reponse's status code
        :type response_status: int
        :return: Data to be sent to Tanner
        :rtype: Dict
        """
        data = dict(
            method=None,
            path=None,
            headers=None,
            uuid=self.snare_uuid.decode("utf-8"),
            peer=None,
            status=response_status,
        )
        if request.transport:
            peer = dict(
                ip=request.transport.get_extra_info("peername")[0],
                port=request.transport.get_extra_info("peername")[1],
            )
            data["peer"] = peer
        if request.path:
            # FIXME request.headers is a CIMultiDict, so items with the same
            # key will be overwritten when converting to dictionary
            header = {key: value for (key, value) in request.headers.items()}
            data["method"] = request.method
            data["headers"] = header
            data["path"] = request.path_qs
            if "Cookie" in header:
                data["cookies"] = {cookie.split("=")[0]: cookie.split("=")[1] for cookie in header["Cookie"].split(";")}
        return data

    async def submit_data(self, data: Dict[str, Union[str, int, Dict[str, str]]]) -> Union[None, Dict]:
        """Submit data to Tanner and fetch response

        :param data: Data to be sent to Tanner
        :type data: Dict[str, Union[str, int, Dict[str, str]]]
        :raises e: If there is an error sending data to Tanner
        :return: Response from Tanner
        :rtype: Union[None, Dict]
        """
        event_result = None
        try:
            async with aiohttp.ClientSession() as session:
                r = await session.post(
                    "http://{0}:8090/event".format(self.run_args.tanner),
                    json=data,
                    timeout=10.0,
                )
                try:
                    event_result = await r.json()
                except (
                    json.decoder.JSONDecodeError,
                    aiohttp.client_exceptions.ContentTypeError,
                ) as e:
                    self.logger.error("Error submitting data: {} {}".format(e, data))
                    event_result = {
                        "version": "0.6.0",
                        "response": {
                            "message": {
                                "detection": {
                                    "name": "index",
                                    "order": 1,
                                    "type": 1,
                                    "version": "0.6.0",
                                },
                                "sess_uuid": data["uuid"],
                            }
                        },
                    }
                finally:
                    await r.release()
        except Exception as e:
            self.logger.exception("Exception: %s", e)
            raise e
        return event_result

    async def parse_tanner_response(
        self, requested_name: str, detection: Dict[str, Union[str, int]]
    ) -> Tuple[Union[None, bytes], multidict.CIMultiDict, int]:
        """Parse Tanner's response to prepare Snare's response

        :param requested_name: Requested path
        :type requested_name: str
        :param detection: Tanner detection info
        :type detection: Dict[str, Union[str, int]]
        :raises web.HTTPFound: If page redirects
        :raises web.HTTPFound: If error page redirects
        :return: Response content, headers and status code
        :rtype: Tuple[Union[None, bytes], multidict.CIMultiDict, int]
        """
        content = None
        status_code = 200
        headers = multidict.CIMultiDict()
        # Creating a regex object for the pattern of multiple contiguous forward slashes
        p = re.compile("/+")
        # Substituting all occurrences of the pattern with single forward slash
        requested_name = p.sub("/", requested_name)

        if detection["type"] == 1:
            possible_requests = [requested_name]
            query_start = requested_name.find("?")
            if query_start != -1:
                possible_requests.append(requested_name[:query_start])

            file_name = None
            for requested_name in possible_requests:
                if requested_name == "/":
                    requested_name = self.run_args.index_page
                requested_name = unquote(requested_name)
                try:
                    if self.meta.get(requested_name) and self.meta[requested_name].get("redirect"):
                        raise web.HTTPFound(self.meta[requested_name]["redirect"])
                    file_name = self.meta[requested_name]["hash"]
                    for header in self.meta[requested_name].get("headers", []):
                        for key, value in header.items():
                            headers.add(key, value)
                    # overwrite headers with legacy content-type if present and not none
                    content_type = self.meta[requested_name].get("content_type")
                    if content_type:
                        headers["Content-Type"] = content_type
                except KeyError:
                    pass
                else:
                    break

            if not file_name:
                if self.meta.get("/status_404") and self.meta["/status_404"].get("redirect"):
                    raise web.HTTPFound(self.meta["/status_404"]["redirect"])
                status_code = 404
            else:
                path = os.path.join(self.dir, file_name)
                if os.path.isfile(path):
                    with open(path, "rb") as fh:
                        content = fh.read()
                    if headers.get("Content-Type", "").startswith("text/html"):
                        content = await self.html_handler.handle_content(content)

        elif detection["type"] == 2:
            payload_content = detection["payload"]
            if payload_content["page"]:
                try:
                    file_name = self.meta[payload_content["page"]]["hash"]
                    for header in self.meta[payload_content["page"]].get("headers", []):
                        for key, value in header.items():
                            headers.add(key, value)
                    # overwrite headers with legacy content-type if present and not none
                    content_type = self.meta[payload_content["page"]].get("content_type")
                    if content_type:
                        headers["Content-Type"] = content_type
                    page_path = os.path.join(self.dir, file_name)
                    with open(page_path, encoding="utf-8") as p:
                        content = p.read()
                except KeyError:
                    content = "<html><body></body></html>"
                    headers["Content-Type"] = "text/html"

                soup = BeautifulSoup(content, "html.parser")
                script_tag = soup.new_tag("div")
                script_tag.append(BeautifulSoup(payload_content["value"], "html.parser"))
                soup.body.append(script_tag)
                content = str(soup).encode()
            else:
                content_type = "text/plain"
                if content_type:
                    headers["Content-Type"] = content_type
                content = payload_content["value"].encode("utf-8")

            if "headers" in payload_content:
                # overwrite local headers with the tanner-provided ones
                headers.update(payload_content["headers"])

        else:  # type 3
            payload_content = detection["payload"]
            status_code = payload_content["status_code"]

        return content, headers, status_code
