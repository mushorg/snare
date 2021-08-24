from distutils.version import StrictVersion
import hashlib
import json
import logging
import mimetypes
import os
from os import walk
import shutil

from bs4 import BeautifulSoup


class VersionManager:
    """Check Snare-Tanner compatibility"""

    def __init__(self) -> None:
        """Constructor method"""
        self.logger = logging.getLogger(__name__)
        self.version = "0.3.0"
        self.version_mapper = {
            "0.1.0": ["0.1.0", "0.4.0"],
            "0.2.0": ["0.5.0", "0.5.0"],
            "0.3.0": ["0.5.0", "0.6.0"],
        }

    def check_compatibility(self, tanner_version: str) -> None:
        """Check Snare compatibility with Tanner

        :param tanner_version: Tanner version
        :type tanner_version: str
        :raises RuntimeError: If Tanner and Snare versions are compatible
        """
        min_version = self.version_mapper[self.version][0]
        max_version = self.version_mapper[self.version][1]
        if not (StrictVersion(min_version) <= StrictVersion(tanner_version) <= StrictVersion(max_version)):
            self.logger.exception("Wrong tanner version %s", tanner_version)
            raise RuntimeError(
                "Wrong tanner version: {}. Compatible versions are {} - {}".format(
                    tanner_version, min_version, max_version
                )
            )


class Converter:
    """Convert a website's source files to a Snare-friendly form"""

    def __init__(self) -> None:
        """Constructor method"""
        self.logger = logging.getLogger(__name__)
        self.meta = {}

    def convert(self, path: str) -> None:
        """Rename all page files to their MD5 hash and populate meta.json with their hash and Content-Type header

        :param path: Page files storage directory
        :type path: str
        """
        files_to_convert = []

        for (dirpath, dirnames, filenames) in walk(path):
            for fn in filenames:
                files_to_convert.append(os.path.join(dirpath, fn))

        for fn in files_to_convert:
            path_len = len(path)
            file_name = fn[path_len:]
            m = hashlib.md5()
            m.update(fn.encode("utf-8"))
            hash_name = m.hexdigest()
            self.meta[file_name] = {
                "hash": hash_name,
                "headers": [
                    {"Content-Type": mimetypes.guess_type(file_name)[0]},
                ],
            }
            self.logger.debug("Converting the file as %s ", os.path.join(path, hash_name))
            shutil.copyfile(fn, os.path.join(path, hash_name))
            os.remove(fn)

        with open(os.path.join(path, "meta.json"), "w") as mj:
            json.dump(self.meta, mj)


def add_meta_tag(page_dir: str, index_page: str, config: dict, base_path: str) -> None:
    """Add meta tags to index page

    :param page_dir: Page files storage directory
    :type page_dir: str
    :param index_page: Index page file name
    :type index_page: str
    :param config: Configuration settings
    :type config: dict
    :param base_path: Base path of files
    :type base_path: str
    """
    google_content = config["WEB-TOOLS"]["google"]
    bing_content = config["WEB-TOOLS"]["bing"]

    if not google_content and not bing_content:
        return

    main_page_path = os.path.join(os.path.join(base_path, "pages"), page_dir, index_page)
    with open(main_page_path) as main:
        main_page = main.read()
    soup = BeautifulSoup(main_page, "html.parser")

    if google_content and soup.find("meta", attrs={"name": "google-site-verification"}) is None:
        google_meta = soup.new_tag("meta")
        google_meta.attrs["name"] = "google-site-verification"
        google_meta.attrs["content"] = google_content
        soup.head.append(google_meta)
    if bing_content and soup.find("meta", attrs={"name": "msvalidate.01"}) is None:
        bing_meta = soup.new_tag("meta")
        bing_meta.attrs["name"] = "msvalidate.01"
        bing_meta.attrs["content"] = bing_content
        soup.head.append(bing_meta)

    html = soup.prettify("utf-8")
    with open(main_page_path, "wb") as file:
        file.write(html)


def check_meta_file(meta_info: dict) -> bool:
    """Verify meta info

    :param meta_info: Meta info from meta.json
    :type meta_info: Dict
    :return: True if contents are properly present
    :rtype: bool
    """
    for _, val in meta_info.items():
        if "hash" in val and any(header in val for header in ["content_type", "headers"]):
            continue
        elif val.get("redirect"):
            continue
        else:
            return False
    return True


def parse_timeout(timeout: str) -> int:
    """Parse auto-update timeout duration string

    :param timeout: Timeout duration
    :type timeout: str
    :return: Timeout duration in seconds
    :rtype: int
    """
    timeouts_coeff = {"M": 60, "H": 3600, "D": 86400}

    form = timeout[-1]
    if form not in timeouts_coeff.keys():
        print_color("Bad timeout format, default will be used", "WARNING")
        result = parse_timeout("24H")
    else:
        result = int(timeout[:-1])
        result *= timeouts_coeff[form]
    return result


def print_color(msg: str, mode: str = "INFO", end: str = "\n") -> None:
    """Color printing

    :param msg: Message to be printed
    :type msg: str
    :param mode: Mode/level of message, defaults to "INFO"
    :type mode: str, optional
    :param end: Ending character(s), defaults to "\n"
    :type end: str, optional
    """
    colors = {
        "INFO": "\033[97m",  # white
        "ERROR": "\033[31m",  # red
        "WARNING": "\033[33m",  # yellow
    }
    try:
        color = colors[mode]
    except KeyError:
        color = colors["INFO"]
    print(color + str(msg) + "\033[0m", end=end)


def check_privileges(path: str) -> None:
    """Create the given directory if it doesn't exist and Check if user has access to it

    :param path: Directory location (will be created if it doesn't exist already)
    :type path: str
    :raises PermissionError: If directory cannot be created
    :raises PermissionError: If directory does not have write access
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except PermissionError:
            raise PermissionError(f"Failed to create path: {os.path.abspath(path)}")
    if not os.access(path, os.W_OK):
        raise PermissionError(f"Failed to access path: {os.path.abspath(path)}")
