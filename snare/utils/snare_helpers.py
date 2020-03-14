import os
from os import walk
import hashlib
import mimetypes
import json
import shutil
import argparse
import logging
from distutils.version import StrictVersion
from bs4 import BeautifulSoup


class VersionManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.version = "0.3.0"
        self.version_mapper = {
            "0.1.0": ["0.1.0", "0.4.0"],
            "0.2.0": ["0.5.0", "0.5.0"],
            "0.3.0": ["0.5.0", "0.6.0"]
        }

    def check_compatibility(self, tanner_version):
        min_version = self.version_mapper[self.version][0]
        max_version = self.version_mapper[self.version][1]
        if not (StrictVersion(min_version) <= StrictVersion(tanner_version) <= StrictVersion(max_version)):
            self.logger.exception('Wrong tanner version %s', tanner_version)
            raise RuntimeError("Wrong tanner version: {}. Compatible versions are {} - {}"
                               .format(tanner_version, min_version, max_version))


class Converter:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.meta = {}

    def convert(self, path):
        files_to_convert = []

        for (dirpath, dirnames, filenames) in walk(path):
            for fn in filenames:
                files_to_convert.append(os.path.join(dirpath, fn))

        for fn in files_to_convert:
            path_len = len(path)
            file_name = fn[path_len:]
            m = hashlib.md5()
            m.update(fn.encode('utf-8'))
            hash_name = m.hexdigest()
            self.meta[file_name] = {'hash': hash_name, 'content_type': mimetypes.guess_type(file_name)[0]}
            self.logger.debug('Converting the file as %s ', os.path.join(path, hash_name))
            shutil.copyfile(fn, os.path.join(path, hash_name))
            os.remove(fn)

        with open(os.path.join(path, 'meta.json'), 'w') as mj:
            json.dump(self.meta, mj)


def add_meta_tag(page_dir, index_page, config, base_path):
    google_content = config['WEB-TOOLS']['google']
    bing_content = config['WEB-TOOLS']['bing']

    if not google_content and not bing_content:
        return

    main_page_path = os.path.join(os.path.join(base_path, 'pages'), page_dir, index_page)
    with open(main_page_path) as main:
        main_page = main.read()
    soup = BeautifulSoup(main_page, 'html.parser')

    if google_content and soup.find("meta", attrs={"name": "google-site-verification"}) is None:
        google_meta = soup.new_tag('meta')
        google_meta.attrs['name'] = 'google-site-verification'
        google_meta.attrs['content'] = google_content
        soup.head.append(google_meta)
    if bing_content and soup.find("meta", attrs={"name": "msvalidate.01"}) is None:
        bing_meta = soup.new_tag('meta')
        bing_meta.attrs['name'] = 'msvalidate.01'
        bing_meta.attrs['content'] = bing_content
        soup.head.append(bing_meta)

    html = soup.prettify("utf-8")
    with open(main_page_path, "wb") as file:
        file.write(html)


def check_meta_file(meta_info):
    for k, v in meta_info.items():
        if 'hash' in v and 'content_type' in v:
            continue
        else:
            return False
    return True


def parse_timeout(timeout):
    timeouts_coeff = {
        'M': 60,
        'H': 3600,
        'D': 86400
    }

    form = timeout[-1]
    if form not in timeouts_coeff.keys():
        print_color('Bad timeout format, default will be used', 'WARNING')
        result = parse_timeout('24H')
    else:
        result = int(timeout[:-1])
        result *= timeouts_coeff[form]
    return result


def str_to_bool(v):
    if v.lower() == 'true':
        return True
    elif v.lower() == 'false':
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected')


def print_color(msg, mode='INFO', end="\n"):
    colors = {
        'INFO': '\033[97m',  # white
        'ERROR': '\033[31m',  # red
        'WARNING': '\033[33m'  # yellow
    }
    try:
        color = colors[mode]
    except KeyError:
        color = colors['INFO']
    print(color + str(msg) + '\033[0m', end=end)


def check_privileges(path):
    """
    Checks if the user has privileges to the path passed as argument.
    """
    if not os.path.exists(path):
        os.makedirs(path)
    with open(os.path.join(path, 'temp'), 'w') as tempfile:
        tempfile.write('')
    os.remove(os.path.join(path, 'temp'))
