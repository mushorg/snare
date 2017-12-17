from distutils.version import StrictVersion


class VersionManager:
    def __init__(self):
        self.version = "0.1.0"
        self.version_mapper = {
            "0.1.0": "0.4.0"
        }

    def check_compatibility(self, tanner_version):
        max_version =  self.version_mapper[self.version]
        if not StrictVersion(tanner_version) <= StrictVersion(max_version):
            print("Wrong tanner version {}. Need version {} or less".format(tanner_version, max_version))
            exit(1)
