import os
import random
import string


def directory_generator(size: int = 9, chars: str = string.ascii_lowercase + string.digits) -> str:
    """Generate directory name with given size from given characters

    :param size: Directory name size, defaults to 9
    :type size: int, optional
    :param chars: Sample space of characters for directory name, defaults to string.ascii_lowercase+string.digits
    :type chars: str, optional
    :return: Randomly generated directory name
    :rtype: str
    """
    return "".join(random.choice(chars) for _ in range(size))


def generate_unique_path() -> str:
    """Genrate unique absolute path for storing page data

    :return: Unique absolute path
    :rtype: str
    """
    path = "/opt/snare/pages/" + directory_generator()
    while os.path.exists(path):
        path = "/opt/snare/pages/" + directory_generator()
    return path
