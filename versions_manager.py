from distutils.version import StrictVersion


class VersionManager:
    def __init__(self):
        self.version = "0.2.0"
        self.version_mapper = {
            "0.1.0": ["0.1.0","0.4.0"],
            "0.2.0" : ["0.5.0", "0.5.0"]
        }

    def check_compatibility(self, tanner_version):
        min_version = self.version_mapper[self.version][0]
        max_version = self.version_mapper[self.version][1]
        if not (StrictVersion(min_version) <= StrictVersion(tanner_version) <= StrictVersion(max_version)):
            raise RuntimeError("Wrong tanner version: {}. Compatible versions are {} - {}".format(tanner_version, min_version, max_version))
            exit(1)
