from distutils.version import StrictVersion
from bs4 import BeautifulSoup
import os


class SnareHelper:
    def __init__(self, args):
        self.version = "0.2.0"
        self.version_mapper = {
            "0.1.0": ["0.1.0", "0.4.0"],
            "0.2.0": ["0.5.0", "0.5.0"]
        }
        self.meta = {}
        self.path = os.path.join('/opt/snare/pages/', args.page_dir)
        self.timeout = args.update_timeout

    def check_compatibility(self, tanner_version):
        min_version = self.version_mapper[self.version][0]
        max_version = self.version_mapper[self.version][1]
        if not (StrictVersion(min_version) <= StrictVersion(tanner_version) <= StrictVersion(max_version)):
            raise RuntimeError("Wrong tanner version: {}. Compatible versions are {} - {}"
                               .format(tanner_version, min_version, max_version))

    def convert(self):
        files_to_convert = []
        for (dirpath, dirnames, filenames) in walk(self.path):
            for fn in filenames:
                files_to_convert.append(os.path.join(dirpath, fn))

        for fn in files_to_convert:
            path_len = len(self.path)
            file_name = fn[path_len:]
            m = hashlib.md5()
            m.update(fn.encode('utf-8'))
            hash_name = m.hexdigest()
            self.meta[file_name] = {'hash': hash_name, 'content_type': mimetypes.guess_type(file_name)[0]}
            shutil.copyfile(fn, os.path.join(self.path, hash_name))
            os.remove(fn)

        with open(os.path.join(self.path, 'meta.json'), 'w') as mj:
            json.dump(self.meta, mj)

    def add_meta_tag(self, index_page, config):
        google_content = config['WEB-TOOLS']['google']
        bing_content = config['WEB-TOOLS']['bing']

        if not google_content and not bing_content:
            return

        main_page_path = os.path.join(self.path, index_page)
        with open(main_page_path) as main:
            main_page = main.read()
        soup = BeautifulSoup(main_page, 'html.parser')

        if (google_content and soup.find("meta", attrs={"name": "google-site-verification"}) is None):
            google_meta = soup.new_tag('meta')
            google_meta.attrs['name'] = 'google-site-verification'
            google_meta.attrs['content'] = google_content
            soup.head.append(google_meta)
        if (bing_content and soup.find("meta", attrs={"name": "msvalidate.01"}) is None):
            bing_meta = soup.new_tag('meta')
            bing_meta.attrs['name'] = 'msvalidate.01'
            bing_meta.attrs['content'] = bing_content
            soup.head.append(bing_meta)

        html = soup.prettify("utf-8")
        with open(main_page_path, "wb") as file:
            file.write(html)

    def parse_timeout(self):
        result = None
        timeouts_coeff = {
            'M': 60,
            'H': 3600,
            'D': 86400
        }

        form = self.timeout[-1]
        if form not in timeouts_coeff.keys():
            print('Bad timeout format, default will be used')
            parse_timeout('24H')
        else:
            result = int(self.timeout[:-1])
            result *= timeouts_coeff[form]
        return result
