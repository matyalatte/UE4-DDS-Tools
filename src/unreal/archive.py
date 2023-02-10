"""Serialize functions.

Notes:
    Similar to FArchive for UE.
    It can read or write attributes with left shift operators.
    e.g. Ar << (type, obj, "attribute_name")
"""

from io import IOBase, BytesIO
import struct


def get_size(f: IOBase):
    pos = f.tell()
    f.seek(0, 2)
    size = f.tell()
    f.seek(pos)
    return size


class ArchiveBase:
    io: IOBase
    is_reading = False
    is_writing = False

    def __init__(self, io: IOBase, endian="little", context: dict = {}):
        self.io = io
        self.size = get_size(io)
        self.endian = endian
        for key, val in context.items():
            setattr(self, key, val)

        if isinstance(io, BytesIO):
            self.name = "BytesIO"
        else:
            self.name = io.name
        self.args = None

    def __lshift__(self, val: tuple):  # pragma: no cover
        """Read or write attributes.
        Notes:
            Ar << (type, obj, "attribute_name", optional_args)
        """
        pass

    def __eq__(self, val: tuple):  # pragma: no cover
        """Read or write a constant value, and raise an error if it has unexpected value.
        Notes:
            Ar == (type, const, "variable_name", optional_args)
        """
        pass

    def tell(self):
        return self.io.tell()

    def seek(self, val, mode=0):
        self.io.seek(val, mode)

    def read(self, size=-1):
        return self.io.read(size)

    def write(self, obj):
        self.io.write(obj)

    def close(self):
        self.io.close()

    def check(self, actual, expected, msg='Parse failed. Make sure you specified UE version correctly.'):
        if actual == expected:
            return
        print(f'offset: {self.tell()}')
        print(f'actual: {actual}')
        print(f'expected: {expected}')
        raise RuntimeError(msg)


class ArchiveRead(ArchiveBase):
    is_reading = True

    def __lshift__(self, val: tuple):
        self.args = val[3:]
        setattr(val[1], val[2], val[0].read(self))

    def __eq__(self, val: tuple):
        self.args = val[3:]
        offset = self.io.tell()
        actual = val[0].read(self)
        expected = val[1]
        if actual != expected:
            print(f"offset: {offset}")
            print(f"expected: {expected}")
            print(f"actual: {actual}")
            msg = f"Unexpected value for {val[2]}."
            raise RuntimeError(msg)


class ArchiveWrite(ArchiveBase):
    is_writing = True

    def __lshift__(self, val: tuple):
        self.args = val[3:]
        val[0].write(self, getattr(val[1], val[2]))

    def __eq__(self, val: tuple):
        self.args = val[3:]
        val[0].write(self, val[1])


class Bytes:
    @staticmethod
    def read(ar: ArchiveBase) -> bytes:
        size = ar.args[0]
        return ar.read(size)

    @staticmethod
    def write(ar: ArchiveBase, val: bytes):
        ar.write(val)


class Buffer(Bytes):
    @staticmethod
    def read(ar: ArchiveBase) -> bytes:
        size = ar.args[0]
        if ar.tell() + size > ar.size:
            raise RuntimeError(
                "There is no buffer that has specified size."
                f" (Offset: {ar.tell()}, Size: {size})"
            )
        return ar.read(size)


class IntBase:
    size = 0
    signed = False

    @classmethod
    def read(cls, ar: ArchiveBase) -> int:
        binary = ar.read(cls.size)
        return int.from_bytes(binary, ar.endian, signed=cls.signed)

    @classmethod
    def write(cls, ar: ArchiveBase, val: int):
        binary = val.to_bytes(cls.size, byteorder=ar.endian, signed=cls.signed)
        ar.write(binary)


class Uint8(IntBase):
    size = 1


class Uint16(IntBase):
    size = 2


class Uint32(IntBase):
    size = 4


class Uint64(IntBase):
    size = 8


class Int8(IntBase):
    size = 1
    signed = True


class Int16(IntBase):
    size = 2
    signed = True


class Int32(IntBase):
    size = 4
    signed = True


class Int64(IntBase):
    size = 8
    signed = True


class NumArrayBase:
    elm_type = ""
    elm_size = 0

    @classmethod
    def read(cls, ar: ArchiveBase) -> list:
        size = ar.args[0]
        binary = ar.read(cls.elm_size * size)
        return list(struct.unpack(cls.elm_type * size, binary))

    @classmethod
    def write(cls, ar: ArchiveBase, val: list):
        binary = struct.pack(cls.elm_type * len(val), *val)
        ar.write(binary)


class Uint32Array(NumArrayBase):
    elm_type = "I"
    elm_size = 4


class Int32Array(NumArrayBase):
    elm_type = "i"
    elm_size = 4


class String:
    @staticmethod
    def read(ar: ArchiveBase) -> str:
        num = Int32.read(ar)
        if num == 0:
            return None

        utf16 = num < 0
        if utf16:
            num = -num
            encode = 'utf-16-le'
        else:
            encode = 'ascii'

        string = ar.read((num - 1) * (1 + utf16)).decode(encode)
        ar.seek(1 + utf16, 1)
        return string

    @staticmethod
    def write(ar: ArchiveBase, val: str):
        num = len(val) + 1
        utf16 = not val.isascii()
        Int32.write(ar, num * (1 - 2 * utf16))
        encode = 'utf-16-le' if utf16 else 'ascii'
        str_byte = val.encode(encode)
        ar.write(str_byte + b'\x00' * (1 + utf16))


class SerializableBase:
    def serialize(self, ar: ArchiveBase):  # pragma: no cover
        pass

    @classmethod
    def read(cls, ar: ArchiveBase):
        obj = cls()
        obj.serialize(ar)
        return obj

    @staticmethod
    def write(ar: ArchiveBase, val):
        val.serialize(ar)


class StructArray:

    @staticmethod
    def read_obj(ar: ArchiveBase, cls, args: tuple):
        ar.args = args
        return cls.read(ar)

    @staticmethod
    def read(ar: ArchiveBase):
        cls = ar.args[0]
        size = ar.args[1]
        args = ar.args[2:]
        objects = [StructArray.read_obj(ar, cls, args) for i in range(size)]
        return objects

    @staticmethod
    def write_obj(ar: ArchiveBase, obj, cls, args: tuple):
        ar.args = args
        cls.write(ar, obj)

    @staticmethod
    def write(ar: ArchiveBase, objects):
        cls = ar.args[0]
        args = ar.args[2:]
        list(map(lambda obj: StructArray.write_obj(ar, obj, cls, args), objects))
