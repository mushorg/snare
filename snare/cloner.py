import asyncio
from asyncio import Queue
from collections import defaultdict
import hashlib
import json
import logging
import os
import re
import sys
from typing import Dict, List, Tuple, Union

import aiohttp
from bs4 import BeautifulSoup
import cssutils
import pyppeteer
from pyppeteer.errors import NetworkError, PageError, TimeoutError
import yarl

from snare.utils.snare_helpers import print_color

animation = "|/-\\"


class BaseCloner:
    def __init__(self, root: str, max_depth: int, css_validate: bool, default_path: str = "/opt/snare") -> None:
        """Base class for all core functions of the cloner

        :param root: Website root URL
        :type root: str
        :param max_depth: Max depth of cloning
        :type max_depth: int
        :param css_validate: Whether CSS validation is enabled
        :type css_validate: bool
        :param default_path: Storage path for site files, defaults to "/opt/snare"
        :type default_path: str, optional
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.visited_urls = []
        self.root, self.error_page = self.add_scheme(root)
        self.max_depth = max_depth
        self.moved_root = None
        self.default_path = default_path
        if (self.root.host is None) or (len(self.root.host) < 4):
            sys.exit("invalid target {}".format(self.root.host))
        self.target_path = "{}/pages/{}".format(self.default_path, self.root.host)

        if not os.path.exists(self.target_path):
            os.makedirs(self.target_path)

        self.css_validate = css_validate
        self.css_logger = logging.getLogger(__name__ + ".__handle")
        cssutils.log.setLog(self.css_logger)
        if not css_validate:
            self.css_logger.setLevel(logging.CRITICAL)

        self.new_urls = Queue()
        self.meta = defaultdict(dict)

        self.itr = 0

    @staticmethod
    def add_scheme(url: str) -> Tuple[yarl.URL, yarl.URL]:
        """Generate root and 404 URLs with proper schemes

        :param url: Raw website root URL
        :type url: str
        :return: root URL, 404 page URL
        :rtype: Tuple[yarl.URL, yarl.URL]
        """
        new_url = yarl.URL(url)
        if not new_url.scheme:
            new_url = yarl.URL("http://" + url)
        err_url = new_url.with_path("/status_404").with_query(None).with_fragment(None)
        return new_url, err_url

    @staticmethod
    def get_headers(
        response: Union[aiohttp.ClientResponse, pyppeteer.network_manager.Response]
    ) -> Tuple[List[Dict[str, str]], Union[str, None]]:
        """Filter response headers, convert them to a list of dictionaries of each header
        and return them along with the content type

        :param response: Response object from aiohttp or Pyppeteer
        :type response: Union[aiohttp.ClientResponse, pyppeteer.network_manager.Response]
        :return: Response headers, Content-type
        :rtype: Tuple[List[Dict[str, str]], str]
        """
        ignored_headers_lowercase = [
            "age",
            "cache-control",
            "connection",
            "content-encoding",
            "content-length",
            "date",
            "etag",
            "expires",
            "transfer-encoding",
            "x-cache",
        ]

        content_type = None
        headers = []
        for key, value in response.headers.items():
            if key.lower() == "content-type":
                content_type = str(value)
            elif key.lower() not in ignored_headers_lowercase:
                headers.append({key: value})
        return headers, content_type

    async def process_link(self, url: str, level: int, check_host: bool = False) -> Union[str, None]:
        """Process (relative and absolute) links to make them suitable for serving and add new URLs to the queue

        :param url: Page URL
        :type url: str
        :param level: Page depth
        :type level: int
        :param check_host: Whether to check the host while processing, defaults to False
        :type check_host: bool, optional
        :return: Processed link
        :rtype: Union[str, None]
        """
        try:
            url = yarl.URL(url)
        except UnicodeError:
            return None
        if url.scheme in ["data", "javascript", "file"]:
            return url.human_repr()
        if not url.is_absolute():
            if self.moved_root is None:
                url = self.root.join(url)
            else:
                url = self.moved_root.join(url)

        host = url.host

        if check_host:
            if (
                (host != self.root.host and self.moved_root is None)
                or url.fragment
                or (self.moved_root is not None and host != self.moved_root.host)
            ):
                return None
        if url.with_scheme("http").human_repr() not in self.visited_urls and (level + 1) <= self.max_depth:
            await self.new_urls.put({"url": url, "level": level + 1, "try_count": 0})

        res = None
        try:
            res = url.relative().human_repr()
        except ValueError:
            self.logger.error("ValueError while processing the %s link", url)
        return res

    async def replace_links(self, data: Union[bytes, str], level: int) -> BeautifulSoup:
        """Replace website links to make them suitable for serving

        :param data: Page data
        :type data: Union[bytes, str]
        :param level: Page depth
        :type level: int
        :return: BeautifulSoup object
        :rtype: BeautifulSoup
        """
        soup = BeautifulSoup(data, "html.parser")

        # find all relative links
        for link in soup.findAll(href=True):
            res = await self.process_link(link["href"], level, check_host=True)
            if res is not None:
                link["href"] = res

        # find all images and scripts
        for elem in soup.findAll(src=True):
            res = await self.process_link(elem["src"], level)
            if res is not None:
                elem["src"] = res

        # find all action elements
        for act_link in soup.findAll(action=True):
            res = await self.process_link(act_link["action"], level)
            if res is not None:
                act_link["action"] = res

        # prevent redirects
        for redir in soup.findAll(True, attrs={"name": re.compile("redirect.*")}):
            if redir["value"] != "":
                redir["value"] = yarl.URL(redir["value"]).relative().human_repr()

        return soup

    def _make_filename(self, url: yarl.URL) -> Tuple[str, str]:
        """Generate file name and its hash for meta info and file storage

        :param url: Site URL
        :type url: yarl.URL
        :return: File name, its MD5 hash
        :rtype: Tuple[str, str]
        """
        if url.is_absolute():
            file_name = url.relative().human_repr()
        else:
            file_name = url.human_repr()

        if not file_name.startswith("/"):
            file_name = "/" + file_name

        host = url.host
        if file_name == "/" and (host != self.root.host or (self.moved_root and host != self.moved_root.host)):
            file_name = host

        m = hashlib.md5()
        m.update(file_name.encode("utf-8"))
        hash_name = m.hexdigest()
        return file_name, hash_name

    async def fetch_data(self, driver: None, current_url: None, level: None, try_count: None) -> None:
        """Abstract method to fetch data from the given URL

        :param driver: Driver object
        :type driver: None
        :param current_url: URL of the page to clone
        :type current_url: None
        :param level: Depth of the URL
        :type level: None
        :param try_count: Try count of the URL
        :type try_count: None
        :raises NotImplementedError: Abstract method
        """
        raise NotImplementedError

    async def get_body(self, driver: Union[aiohttp.ClientSession, pyppeteer.browser.Browser]) -> None:
        """Get page body of URLs in queue

        :param driver: Driver object to fetch data
        :type driver: Union[aiohttp.ClientSession, pyppeteer.browser.Browser]
        """
        while not self.new_urls.empty():
            print(animation[self.itr], end="\r")
            self.itr = (self.itr + 1) % len(animation)
            current_url, level, try_count = (await self.new_urls.get()).values()
            if try_count > 2:
                continue
            if current_url.with_scheme("http").human_repr() in self.visited_urls:
                continue
            self.visited_urls.append(current_url.with_scheme("http").human_repr())
            redirect_url, data, headers, content_type = await self.fetch_data(driver, current_url, level, try_count)

            if not data:
                continue

            if redirect_url:
                file_name, hash_name = self._make_filename(redirect_url)
                old_file_name, _ = self._make_filename(current_url)
                if old_file_name != file_name:
                    self.meta[old_file_name]["redirect"] = file_name
                    self.visited_urls.append(redirect_url.with_scheme("http").human_repr())
            else:
                file_name, hash_name = self._make_filename(current_url)
            self.logger.debug("Cloned file: %s", file_name)
            self.meta[file_name]["hash"] = hash_name
            self.meta[file_name]["headers"] = headers
            self.meta[file_name]["content_type"] = content_type

            if not content_type:
                pass
            elif "text/html" in content_type:
                soup = await self.replace_links(data, level)
                data = str(soup).encode()
            elif "text/css" in content_type:
                css = cssutils.parseString(data, validate=self.css_validate)
                for carved_url in cssutils.getUrls(css):
                    if carved_url.startswith("data"):
                        continue
                    carved_url = yarl.URL(carved_url)
                    if not carved_url.is_absolute():
                        carved_url = self.root.join(carved_url)
                    if carved_url.with_scheme("http").human_repr() not in self.visited_urls:
                        await self.new_urls.put({"url": carved_url, "level": level + 1, "try_count": 0})
            if type(data) == str:
                data = data.encode()

            try:
                with open(os.path.join(self.target_path, hash_name), "wb") as index_fh:
                    index_fh.write(data)
            except TypeError:
                await self.new_urls.put({"url": current_url, "level": level, "try_count": try_count + 1})

    async def get_root_host(self) -> None:
        """Update the website's root host"""
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.get(self.root)
                if resp.url.host != self.root.host or resp.url.path != self.root.path:
                    self.moved_root = resp.url
                resp.close()
        except aiohttp.ClientError as err:
            self.logger.error("Can't connect to target host: %s", err)
            exit(-1)


class SimpleCloner(BaseCloner):
    async def fetch_data(
        self, session: aiohttp.ClientSession, current_url: yarl.URL, level: int, try_count: int
    ) -> Tuple[Union[yarl.URL, None], bytes, List[Dict[str, str]], str]:
        """Fetch data from the given URL using aiohttp

        :param session: aiohttp ClientSession object
        :type session: aiohttp.ClientSession
        :param current_url: URL of the page to clone
        :type current_url: yarl.URL
        :param level: Depth of the URL
        :type level: int
        :param try_count: Try count of the URL
        :type try_count: int
        :return: Redirected URL, Page data, Response headers, Page content type
        :rtype: Tuple[Union[yarl.URL, None], bytes, List[Dict[str, str]], str]
        """
        data = None
        headers = []
        content_type = None
        redirect_url = None
        try:
            response = await session.get(current_url, headers={"Accept": "text/html"}, timeout=10.0)
            headers, _ = self.get_headers(response)
            content_type = response.content_type
            if response.url.with_scheme("http") != current_url.with_scheme("http"):
                redirect_url = response.url
            data = await response.read()
        except (aiohttp.ClientError, asyncio.TimeoutError, AssertionError) as client_error:
            self.logger.error(client_error)
            await self.new_urls.put({"url": current_url, "level": level, "try_count": try_count + 1})
        else:
            await response.release()
        return redirect_url, data, headers, content_type


class HeadlessCloner(BaseCloner):
    async def fetch_data(
        self, browser: pyppeteer.browser.Browser, current_url: yarl.URL, level: int, try_count: int
    ) -> Tuple[Union[yarl.URL, None], Union[str, bytes], List[Dict[str, str]], Union[str, None]]:
        """Fetch data from the given URL using Pyppeteer

        :param browser: Pyppeteer Browser object
        :type browser: pyppeteer.Browser.browser
        :param current_url: URL of the page to clone
        :type current_url: yarl.URL
        :param level: Depth of the URL
        :type level: int
        :param try_count: Try count of the URL
        :type try_count: int
        :return: Redirected URL, Page data, Response headers, Page content type
        :rtype: Tuple[Union[yarl.URL, None], Union[str, bytes], List[Dict[str, str]], Union[str, None]]
        """
        data = None
        headers = []
        content_type = None
        page = None
        redirect_url = None
        try:
            page = await browser.newPage()
            response = await page.goto(str(current_url))
            headers, content_type = self.get_headers(response)
            response_url = yarl.URL(response.url)
            if response_url.with_scheme("http") != current_url.with_scheme("http"):
                redirect_url = response_url
            data = await response.buffer()
        except (ConnectionError, NetworkError, TimeoutError, PageError) as err:
            self.logger.error(err)
            await self.new_urls.put({"url": current_url, "level": level, "try_count": try_count + 1})
        finally:
            try:
                if page:
                    await page.close()
            except PageError as err:  # when KeyboardInterrupt is raised midway cloning
                self.logger.error(err)

        return redirect_url, data, headers, content_type


class CloneRunner:
    def __init__(
        self, root: str, max_depth: int, css_validate: bool, default_path: str = "/opt/snare", headless: bool = False
    ) -> None:
        """Runner class for all cloners

        :param root: Website root URL
        :type root: str
        :param max_depth: Max depth of cloning
        :type max_depth: int
        :param css_validate: Whether CSS validation is enabled
        :type css_validate: bool
        :param default_path: Storage path for site files, defaults to "/opt/snare"
        :type default_path: str, optional
        :param headless: Whether headless cloning is enabled, defaults to False
        :type headless: bool, optional
        :raises Exception: If runner instance is None indicating initialization error
        """
        self.driver = None
        self.runner = None
        if headless:
            self.runner = HeadlessCloner(root, max_depth, css_validate, default_path)
        else:
            self.runner = SimpleCloner(root, max_depth, css_validate, default_path)
        if not self.runner:
            raise Exception("Error initializing cloner!")

    async def run(self) -> None:
        """Clone website

        :raises Exception: If runner instance is None
        """
        if not self.runner:
            raise Exception("Error running cloner! - Cloner instance is None")
        if type(self.runner) == SimpleCloner:
            self.driver = aiohttp.ClientSession()
        else:
            # close and handle SIGINIT manually with `except KeyboardInterrupt`
            self.driver = await pyppeteer.launch(autoClose=False, handleSIGINT=False)
        try:
            await self.runner.new_urls.put({"url": self.runner.root, "level": 0, "try_count": 0})
            await self.runner.new_urls.put({"url": self.runner.error_page, "level": 0, "try_count": 0})
            await self.runner.get_body(self.driver)
        except KeyboardInterrupt:
            # in most cases, the exception is caught in `bin/clone`
            print_color("\nKeyboardInterrupt received... Quitting", "ERROR")

    async def close(self) -> None:
        """Close all open connections and write meta info into file

        :raises Exception: If runner instance is None
        """
        if not self.runner:
            raise Exception("Error closing cloner! - Cloner instance is None")
        with open(os.path.join(self.runner.target_path, "meta.json"), "w") as mj:
            json.dump(self.runner.meta, mj)
        if self.driver:
            await self.driver.close()
