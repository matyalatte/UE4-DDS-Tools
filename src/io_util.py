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


def check(actual, expected, f=None, msg='Parse failed. Make sure you specified UE4 version correctly.'):
    if actual != expected:
        if f is not None:
            print(f'offset: {f.tell()}')
        print(f'actual: {actual}')
        print(f'expected: {expected}')
        raise RuntimeError(msg)


def get_size(f: IOBase):
    pos = f.tell()
    f.seek(0, 2)
    size = f.tell()
    f.seek(pos)
    return size


def compare(file1: str, file2: str):
    f1 = open(file1, 'rb')
    f2 = open(file2, 'rb')
    print(f'Comparing {file1} and {file2}...')

    f1_size = get_size(f1)
    f2_size = get_size(f2)

    f1_bin = f1.read()
    f2_bin = f2.read()
    f1.close()
    f2.close()

    if f1_size == f2_size and f1_bin == f2_bin:
        print('Same data!')
        return

    i = 0
    for b1, b2 in zip(f1_bin, f2_bin):
        if b1 != b2:
            break
        i += 1

    raise RuntimeError(f'Not same :{i}')
