from distutils.version import StrictVersion

VERSION = "0.1.0"

compatibility = {
    "0.1.0": "0.4.0"
}


def check_compatibility(tanner_version):
    max_version = compatibility[VERSION]
    if not StrictVersion(tanner_version)<=StrictVersion(max_version):
        print("Wrong tanner version {}. Need version {} or less".format(tanner_version, max_version))
        exit(1)
