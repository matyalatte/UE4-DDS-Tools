from io import IOBase
import os
import platform
import tempfile
import sys


def mkdir(dir):
    os.makedirs(dir, exist_ok=True)


def get_os_name():
    return platform.system()


def is_windows():
    return get_os_name() == "Windows"


def is_linux():
    return get_os_name() == "Linux"


def is_mac():
    return get_os_name() == "Darwin"


class NonTempDir:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self.path

    def __exit__(self, exc_type, exc_value, traceback):
        pass


def get_temp_dir(disable_tempfile=False):
    if disable_tempfile:
        return NonTempDir("tmp")
    else:
        return tempfile.TemporaryDirectory()


def get_ext(file: str):
    """Get file extension."""
    return file.split('.')[-1].lower()


def get_size(f: IOBase):
    pos = f.tell()
    f.seek(0, 2)
    size = f.tell()
    f.seek(pos)
    return size


def compare(file1: str, file2: str):
    f1 = open(file1, "rb")
    f2 = open(file2, "rb")
    print(f"Comparing {file1} and {file2}...")

    f1_size = get_size(f1)
    f2_size = get_size(f2)

    f1_bin = f1.read()
    f2_bin = f2.read()
    f1.close()
    f2.close()

    if f1_size == f2_size and f1_bin == f2_bin:
        print("They have the same data!")
        return

    i = 0
    for b1, b2 in zip(f1_bin, f2_bin):
        if b1 != b2:
            break
        i += 1

    raise RuntimeError(f"Not the same :{i} ({file1})")


def remove_quotes(string: str) -> str:
    if string[-1] == '\n':
        string = string[:-1]
    if string in ['', '"']:
        return ''
    if string[0] == '"':
        string = string[1:]
    if string[-1] == '"':
        string = string[:-1]
    return string


def get_base_folder(p: str) -> tuple[str, str]:
    folder = os.path.basename(p)
    directory = os.path.dirname(p)
    if folder == "":
        folder = os.path.dirname(directory)
        directory = os.path.basename(directory)
    if directory == ".":
        directory = ""
    return directory, folder


def get_file_list(folder: str, ext: str = None):
    file_list = get_file_list_rec(folder)
    if ext is not None:
        file_list = [f for f in file_list if get_ext(f) in ext]
    return file_list


def get_file_list_rec(folder: str) -> list[str]:
    file_list = []
    for file in sorted(os.listdir(folder)):
        file_path = os.path.join(folder, file)
        if os.path.isdir(file_path):
            file_list += [os.path.join(file, f) for f in get_file_list_rec(file_path)]
        else:
            file_list.append(file)
    return file_list


def check_python_version(major, minor):
    sys_major = sys.version_info.major
    sys_minor = sys.version_info.minor
    if sys_major > major or (sys_major == major and sys_minor >= minor):
        return
    error_msg = f"Python{major}.{minor} or later required. (Running {sys_major}.{sys_minor})"
    raise RuntimeError(error_msg)
