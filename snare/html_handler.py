import asyncio
import json
import logging

import aiohttp
from bs4 import BeautifulSoup
import cssutils


class HtmlHandler:
    def __init__(self, no_dorks, tanner):
        self.no_dorks = no_dorks
        self.dorks = []
        self.logger = logging.getLogger(__name__)
        self.tanner = tanner

    async def get_dorks(self):
        dorks = None
        try:
            async with aiohttp.ClientSession() as session:
                r = await session.get("http://{0}:8090/dorks".format(self.tanner), timeout=10.0)
                try:
                    dorks = await r.json()
                except json.decoder.JSONDecodeError as e:
                    self.logger.error("Error getting dorks: %s", e)
                finally:
                    await r.release()
        except asyncio.TimeoutError as error:
            self.logger.error("Dorks timeout error: %s", error)
        return dorks["response"]["dorks"] if dorks else []

    async def handle_content(self, content):
        soup = BeautifulSoup(content, "html.parser")
        if self.no_dorks is not True:
            for p_elem in soup.find_all("p"):
                if p_elem.findChildren():
                    continue
                css = None
                if "style" in p_elem.attrs:
                    css = cssutils.parseStyle(p_elem.attrs["style"])
                text_list = p_elem.text.split()
                p_new = soup.new_tag("p", style=css.cssText if css else None)
                for idx, word in enumerate(text_list):
                    # Fetch dorks if required
                    if len(self.dorks) <= 0:
                        self.dorks = await self.get_dorks()
                    word += " "
                    if idx % 5 == 0:
                        a_tag = soup.new_tag(
                            "a",
                            href=self.dorks.pop(),
                            style="color:{color};text-decoration:none;cursor:text;".format(
                                color=css.color if css and "color" in css.keys() else "#000000"
                            ),
                        )
                        a_tag.string = word
                        p_new.append(a_tag)
                    else:
                        p_new.append(soup.new_string(word))
                p_elem.replace_with(p_new)
        content = soup.encode("utf-8")
        return content
