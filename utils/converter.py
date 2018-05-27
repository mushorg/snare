import os
import hashlib
from os import walk
import mimetypes
import json
import shutil


class Converter:
    def __init__(self):
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
            shutil.copyfile(fn, os.path.join(path, hash_name))
            os.remove(fn)

        with open(os.path.join(path, 'meta.json'), 'w') as mj:
            json.dump(self.meta, mj)
