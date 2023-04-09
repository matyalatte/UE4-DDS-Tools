from io import IOBase
import os
import tempfile


def flush_stdout():
    print("", end="", flush=True)


def mkdir(dir):
    os.makedirs(dir, exist_ok=True)


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
        print("Same data!")
        return

    i = 0
    for b1, b2 in zip(f1_bin, f2_bin):
        if b1 != b2:
            break
        i += 1

    raise RuntimeError(f"Not same :{i}")


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


def get_file_list(folder: str, ext: str = None, include_base=True):
    file_list = get_file_list_rec(folder)
    if ext is not None:
        file_list = [f for f in file_list if get_ext(f) in ext]
    if include_base:
        directory, folder = get_base_folder(folder)
        file_list = [os.path.join(folder, file) for file in file_list]
    else:
        directory = folder
    return directory, file_list


def get_file_list_rec(folder: str) -> list[str]:
    file_list = []
    for file in sorted(os.listdir(folder)):
        file_path = os.path.join(folder, file)
        if os.path.isdir(file_path):
            file_list += [os.path.join(file, f) for f in get_file_list_rec(file_path)]
        else:
            file_list.append(file)
    return file_list
