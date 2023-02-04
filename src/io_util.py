from io import IOBase
import os
import struct
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


def check(actual, expected, f=None, msg='Parse failed. Make sure you specified UE4 version correctly.'):
    if actual != expected:
        if f is not None:
            print(f'offset: {f.tell()}')
        print(f'actual: {actual}')
        print(f'expected: {expected}')
        raise RuntimeError(msg)


def read_uint64(f: IOBase) -> int:
    bin = f.read(8)
    return int.from_bytes(bin, "little")


def read_uint32(f: IOBase) -> int:
    bin = f.read(4)
    return int.from_bytes(bin, "little")


def read_uint16(f: IOBase) -> int:
    bin = f.read(2)
    return int.from_bytes(bin, "little")


def read_uint8(f: IOBase) -> int:
    bin = f.read(1)
    return int(bin[0])


def read_int64(f: IOBase) -> int:
    bin = f.read(8)
    return int.from_bytes(bin, "little", signed=True)


def read_int32(f: IOBase) -> int:
    bin = f.read(4)
    return int.from_bytes(bin, "little", signed=True)


def read_array(f: IOBase, read_func, len=None):
    if len is None:
        len = read_uint32(f)
    ary = [read_func(f) for i in range(len)]
    return ary


st_list = ['b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'f', 'd']
st_size = [1, 1, 2, 2, 4, 4, 8, 8, 4, 8]


def read_num_array(f: IOBase, st: str, len=None):
    if st not in st_list:
        raise RuntimeError('Structure not found. {}'.format(st))
    if len is None:
        len = read_uint32(f)
    bin = f.read(st_size[st_list.index(st)] * len)
    return list(struct.unpack(st * len, bin))


def read_uint32_array(f: IOBase, len=None) -> list[int]:
    return read_num_array(f, 'I', len=len)


def read_uint16_array(f: IOBase, len=None) -> list[int]:
    return read_num_array(f, 'H', len=len)


def read_uint8_array(f: IOBase, len=None) -> list[int]:
    return read_num_array(f, 'B', len=len)


def read_int32_array(f: IOBase, len=None) -> list[int]:
    return read_num_array(f, 'i', len=len)


def read_str(f: IOBase) -> str:
    num = read_int32(f)
    if num == 0:
        return None

    utf16 = num < 0
    if utf16:
        num = -num
        encode = 'utf-16-le'
    else:
        encode = 'ascii'

    string = f.read((num - 1) * (1 + utf16)).decode(encode)
    f.seek(1 + utf16, 1)
    return string


def read_const_uint32(f: IOBase, n: int, msg='Unexpected Value!'):
    const = read_uint32(f)
    check(const, n, f, msg)


def read_zero(f: IOBase, msg='Not NULL!'):
    read_const_uint32(f, 0, msg)


def read_zero_array(f: IOBase, len: int, msg='Not NULL!'):
    null = read_uint32_array(f, len=len)
    check(null, [0] * len, f, msg)


def read_buffer(f: IOBase, size: int):
    end_offset = get_size(f)
    if f.tell() + size > end_offset:
        raise RuntimeError(
            "There is no buffer that has specified size."
            f" (Offset: {f.tell()}, Size: {size})"
        )
    return f.read(size)


def write_uint64(f: IOBase, n: int):
    bin = n.to_bytes(8, byteorder="little")
    f.write(bin)


def write_uint32(f: IOBase, n: int):
    bin = n.to_bytes(4, byteorder="little")
    f.write(bin)


def write_uint16(f: IOBase, n: int):
    bin = n.to_bytes(2, byteorder="little")
    f.write(bin)


def write_uint8(f: IOBase, n: int):
    bin = n.to_bytes(1, byteorder="little")
    f.write(bin)


def write_int64(f: IOBase, n: int):
    bin = n.to_bytes(8, byteorder="little", signed=True)
    f.write(bin)


def write_int32(f: IOBase, n: int):
    bin = n.to_bytes(4, byteorder="little", signed=True)
    f.write(bin)


def write_array(f: IOBase, ary: list, write_func, with_length=False):
    if with_length:
        write_uint32(f, len(ary))
    for a in ary:
        write_func(f, a)


def write_uint32_array(f: IOBase, ary: list, with_length=False):
    write_array(f, ary, write_uint32, with_length=with_length)


def write_uint16_array(f: IOBase, ary: list, with_length=False):
    write_array(f, ary, write_uint16, with_length=with_length)


def write_uint8_array(f: IOBase, ary: list, with_length=False):
    write_array(f, ary, write_uint8, with_length=with_length)


def write_int32_array(f: IOBase, ary: list, with_length=False):
    write_array(f, ary, write_int32, with_length=with_length)


def write_str(f: IOBase, string: str):
    num = len(string) + 1
    utf16 = not string.isascii()
    write_int32(f, num * (1 - 2 * utf16))
    encode = 'utf-16-le' if utf16 else 'ascii'
    str_byte = string.encode(encode)
    f.write(str_byte + b'\x00' * (1 + utf16))


def write_zero(f: IOBase):
    write_uint32(f, 0)


def write_zero_array(f: IOBase, len: int):
    write_uint32_array(f, [0] * len)


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
