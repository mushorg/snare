import os
import sys
import logging
import asyncio
import hashlib
import json
import re
import aiohttp
import cssutils
import yarl
from bs4 import BeautifulSoup
from asyncio import Queue
from collections import defaultdict
from pyppeteer import launch

from snare.utils.snare_helpers import print_color

animation = "|/-\\"


class BaseCloner:
    def __init__(self, root, max_depth, css_validate, default_path="/opt/snare"):
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
    def add_scheme(url):
        new_url = yarl.URL(url)
        if not new_url.scheme:
            new_url = yarl.URL("http://" + url)
        err_url = new_url.with_path("/status_404").with_query(None).with_fragment(None)
        return new_url, err_url

    @staticmethod
    def get_headers(response):
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
                content_type = value
            elif key.lower() not in ignored_headers_lowercase:
                headers.append({key: value})
        return [headers, content_type]

    async def process_link(self, url, level, check_host=False):
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

    async def replace_links(self, data, level):
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

    def _make_filename(self, url):
        if url.is_absolute():
            file_name = url.relative().human_repr()
        else:
            file_name = url.human_repr()

        if not file_name.startswith("/"):
            file_name = "/" + file_name

        m = hashlib.md5()
        m.update(file_name.encode("utf-8"))
        hash_name = m.hexdigest()
        return file_name, hash_name

    async def fetch_data(self, driver, current_url, level, try_count):
        raise NotImplementedError

    async def get_body(self, driver):
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

            if content_type == "text/html":
                soup = await self.replace_links(data, level)
                data = str(soup).encode()
            elif content_type == "text/css":
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

    async def get_root_host(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.root) as resp:
                    resp_url = yarl.URL(resp.url)
                    if resp_url.host != self.root.host or resp_url.path != self.root.path:
                        self.moved_root = resp_url
        except aiohttp.ClientError as err:
            self.logger.error("Can't connect to target host: %s", err)
            exit(-1)


class SimpleCloner(BaseCloner):
    async def fetch_data(self, session, current_url, level, try_count):
        data = None
        headers = []
        content_type = None
        redirect_url = None
        try:
            response = await session.get(current_url, headers={"Accept": "text/html"}, timeout=10.0)
            headers, _ = self.get_headers(response)
            content_type = response.content_type
            response_url = yarl.URL(response.url)
            if response_url.with_scheme("http") != current_url.with_scheme("http"):
                redirect_url = response_url
            data = await response.read()
        except (aiohttp.ClientError, asyncio.TimeoutError, AssertionError) as client_error:
            self.logger.error(client_error)
            await self.new_urls.put({"url": current_url, "level": level, "try_count": try_count + 1})
        else:
            await response.release()
        return [redirect_url, data, headers, content_type]


class HeadlessCloner(BaseCloner):
    async def fetch_data(self, browser, current_url, level, try_count):
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
        except Exception as err:
            self.logger.error(err)
            await self.new_urls.put({"url": current_url, "level": level, "try_count": try_count + 1})
        finally:
            try:
                if page:
                    await page.close()
            except Exception as err:
                print_color(str(err), "WARNING")

        return [redirect_url, data, headers, content_type]


class CloneRunner:
    def __init__(self, root, max_depth, css_validate, default_path="/opt/snare", headless=False):
        self.driver = None
        self.runner = None
        if headless:
            self.runner = HeadlessCloner(root, max_depth, css_validate, default_path)
        else:
            self.runner = SimpleCloner(root, max_depth, css_validate, default_path)
        if not self.runner:
            raise Exception("Error initializing cloner!")

    async def run(self):
        if not self.runner:
            raise Exception("Error initializing cloner!")
        if type(self.runner) == SimpleCloner:
            self.driver = aiohttp.ClientSession()
        else:
            # close and handle SIGINIT manually with `except KeyboardInterrupt`
            self.driver = await launch(autoClose=False, handleSIGINT=False)
        try:
            await self.runner.new_urls.put({"url": self.runner.root, "level": 0, "try_count": 0})
            await self.runner.new_urls.put({"url": self.runner.error_page, "level": 0, "try_count": 0})
            await self.runner.get_body(self.driver)
        except KeyboardInterrupt:
            # in most cases, the exception is caught in `bin/clone`
            print_color("\nKeyboardInterrupt received... Quitting", "ERROR")

    async def close(self):
        if not self.runner:
            raise Exception("Error initializing cloner!")
        with open(os.path.join(self.runner.target_path, "meta.json"), "w") as mj:
            json.dump(self.runner.meta, mj)
        if self.driver:
            await self.driver.close()
