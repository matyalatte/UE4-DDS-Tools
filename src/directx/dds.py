"""Class for DDS files.

Notes:
    - Official document for DDS header
      https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-header
    - Official repo for DDS
      https://github.com/microsoft/DirectXTex
"""

import ctypes as c
from enum import IntEnum
from io import IOBase
import os

from .dxgi_format import (DXGI_FORMAT, DXGI_BYTE_PER_PIXEL,
                          FOURCC_TO_DXGI, BITMASK_TO_DXGI)
from util import get_size, mkdir


class PF_FLAGS(IntEnum):
    """dwFlags for DDS_PIXELFORMAT"""
    # ALPHAPIXELS = 0x00000001
    # ALPHA = 0x00000002
    FOURCC = 0x00000004
    # RGB = 0x00000040
    # LUMINANCE = 0x00020000
    BUMPDUDV = 0x00080000


UNCANONICAL_FOURCC = [
    # fourCC for uncanonical formats (ETC, PVRTC, ATITC, ASTC)
    b"PTC2",
    b"PTC4",
    b"ATC",
    b"ATCA",
    b"ATCE",
    b"ATCI",
    b"AS44",
    b"AS55",
    b"AS66",
    b"AS85",
    b"AS86",
    b"AS:5"
]


class DDSPixelFormat(c.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("size", c.c_uint32),              # PfSize == 32
        ("flags", c.c_uint32),             # PfFlags (if 4 then FourCC is used)
        ("fourCC", c.c_char * 4),            # FourCC
        ("bit_count", c.c_uint32),           # Bitcount
        ("bit_mask", c.c_uint32 * 4),        # Bitmask
    ]

    def __init__(self):
        super().__init__()
        self.size = 32
        self.flags = (c.c_uint32)(PF_FLAGS.FOURCC)
        self.fourCC = b"DX10"
        self.bit_count = (c.c_uint32)(0)
        self.bit_mask = (c.c_uint32 * 4)((0) * 4)

    def get_dxgi(self) -> DXGI_FORMAT:
        """Similar method as GetDXGIFormat in DirectXTex/DDSTextureLoader/DDSTextureLoader12.cpp"""

        if not self.is_canonical():
            raise RuntimeError(f"Non-standard fourCC detected. ({self.fourCC.decode()})")

        # Try to detect DXGI from fourCC.
        if self.flags & PF_FLAGS.FOURCC:
            for cc_list, dxgi in FOURCC_TO_DXGI:
                if self.fourCC in cc_list:
                    return dxgi

        # Try to detect DXGI from bit mask.
        detected_dxgi = None
        for bit_mask, dxgi in BITMASK_TO_DXGI:
            if self.is_bit_mask(bit_mask):
                detected_dxgi = dxgi

        if detected_dxgi is None:
            print("Failed to detect dxgi format. It'll be loaded as B8G8R8A8.")
            return DXGI_FORMAT.B8G8R8A8_UNORM

        if self.flags & PF_FLAGS.BUMPDUDV:
            # DXGI format should be signed.
            return DXGI_FORMAT.get_signed(detected_dxgi)
        else:
            return detected_dxgi

    def update(self, new_dxgi):
        if new_dxgi > DXGI_FORMAT.get_max_dx10():
            # When dx10 doesn't support the specified dxgi format.
            for cc_list, dxgi in FOURCC_TO_DXGI:
                if new_dxgi == dxgi:
                    self.fourCC = cc_list[0]
        else:
            self.fourCC = b"DX10"

    def is_bit_mask(self, bit_mask):
        for b1, b2 in zip(self.bit_mask, bit_mask):
            if b1 != b2:
                return False
        return True

    def is_canonical(self):
        return self.fourCC not in UNCANONICAL_FOURCC

    def is_dx10(self):
        return self.fourCC == b"DX10"


class DDS_FLAGS(IntEnum):
    CAPS = 0x1
    HEIGHT = 0x2
    WIDTH = 0x4
    PITCH = 0x8  # Use "w * h * bpp" for pitch_or_linear_size
    PIXELFORMAT = 0x1000
    MIPMAPCOUNT = 0x20000
    LINEARSIZE = 0x80000  # Use "w * bpp" for pitch_or_linear_size
    DEPTH = 0x800000  # For volume textures
    DEFAULT = CAPS | HEIGHT | WIDTH | PIXELFORMAT | MIPMAPCOUNT

    @staticmethod
    def get_flags(is_compressed, is_3d):
        flags = DDS_FLAGS.DEFAULT
        if is_compressed:
            flags |= DDS_FLAGS.PITCH
        else:
            flags |= DDS_FLAGS.LINEARSIZE
        if is_3d:
            flags |= DDS_FLAGS.DEPTH
        return flags


class DDS_CAPS(IntEnum):
    CUBEMAP = 0x8      # DDSCAPS_COMPLEX
    MIPMAP = 0x400008  # DDSCAPS_COMPLEX | DDSCAPS_MIPMAP
    REQUIRED = 0x1000  # DDSCAPS_TEXTURE

    @staticmethod
    def get_caps(has_mips, is_cube):
        caps = DDS_CAPS.REQUIRED
        if has_mips:
            caps |= DDS_CAPS.MIPMAP
        if is_cube:
            caps |= DDS_CAPS.CUBEMAP
        return caps


class DDS_CAPS2(IntEnum):
    CUBEMAP = 0x200
    CUBEMAP_POSITIVEX = 0x400
    CUBEMAP_NEGATIVEX = 0x800
    CUBEMAP_POSITIVEY = 0x1000
    CUBEMAP_NEGATIVEY = 0x2000
    CUBEMAP_POSITIVEZ = 0x4000
    CUBEMAP_NEGATIVEZ = 0x8000
    CUBEMAP_FULL = 0xFE00  # for cubemap that have all faces
    VOLUME = 0x200000

    @staticmethod
    def get_caps2(is_cube, is_3d):
        caps2 = 0
        if is_cube:
            caps2 |= DDS_CAPS2.CUBEMAP_FULL
        if is_3d:
            caps2 |= DDS_CAPS2.VOLUME
        return caps2

    @staticmethod
    def is_cube(caps2):
        return (caps2 & DDS_CAPS2.CUBEMAP) > 0

    @staticmethod
    def is_3d(caps2):
        return (caps2 & DDS_CAPS2.VOLUME) > 0

    @staticmethod
    def is_partial_cube(caps2):
        return DDS_CAPS2.is_cube(caps2) and (caps2 != DDS_CAPS2.CUBEMAP_FULL)


HDR_SUPPORTED = [
    # Convertible as a decompressed format
    "BC6H_TYPELESS",
    "BC6H_UF16",
    "BC6H_SF16",

    # Directory convertible
    "R32G32B32A32_FLOAT",
    "R16G16B16A16_FLOAT",
    "R32G32B32_FLOAT"
]


TGA_SUPPORTED = [
    # Convertible as a decompressed format
    "BC1_TYPELESS",
    "BC1_UNORM",
    "BC1_UNORM_SRGB",
    "BC2_TYPELESS",
    "BC2_UNORM",
    "BC2_UNORM_SRGB",
    "BC3_TYPELESS",
    "BC3_UNORM",
    "BC3_UNORM_SRGB",
    "BC4_TYPELESS",
    "BC4_UNORM",
    "BC4_SNORM",
    "BC7_TYPELESS",
    "BC7_UNORM",
    "BC7_UNORM_SRGB",

    # Directory convertible
    "R8G8B8A8_UNORM",
    "R8G8B8A8_UNORM_SRGB",
    "B8G8R8A8_UNORM",
    "B8G8R8A8_UNORM_SRGB",
    "B8G8R8X8_UNORM",
    "B8G8R8X8_UNORM_SRGB",
    "R8_UNORM",
    "A8_UNORM",
    "B5G5R5A1_UNORM"
]


class DX10Header(c.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("dxgi_format", c.c_uint32),
        ("resource_dimension", c.c_uint32),
        ("misc_flags", c.c_uint32),
        ("array_size", c.c_uint32),
        ("misc_flags2", c.c_uint32)
    ]

    def get_dxgi(self):
        if self.dxgi_format > DXGI_FORMAT.get_max_dx10():
            raise RuntimeError(f"Unsupported DXGI format detected. ({self.dxgi_format})")
        return DXGI_FORMAT(self.dxgi_format)

    def update(self, dxgi_format, is_cube, is_3d, array_size):
        self.dxgi_format = int(dxgi_format)
        self.resource_dimension = 3 + is_3d
        self.misc_flags = 4 * is_cube
        self.array_size = array_size
        self.misc_flags2 = 0

    def is_array(self):
        return self.array_size > 1


def is_hdr(name: str):
    return "BC6" in name or "FLOAT" in name or "INT" in name or "SNORM" in name


def convertible_to_tga(name: str):
    return name in TGA_SUPPORTED


def convertible_to_hdr(name: str):
    return name in HDR_SUPPORTED


def read_buffer(f: IOBase, size: int, end_offset: int):
    if f.tell() + size > end_offset:
        raise RuntimeError(
            "There is no buffer that has specified size."
            f" (Offset: {f.tell()}, Size: {size})"
        )
    return f.read(size)


class DDSHeader(c.LittleEndianStructure):
    MAGIC = b"DDS "
    _pack_ = 1
    _fields_ = [
        ("magic", c.c_char * 4),               # Magic == "DDS "
        ("head_size", c.c_uint32),             # Size == 124
        ("flags", c.c_uint32),                 # DDS_FLAGS
        ("height", c.c_uint32),
        ("width", c.c_uint32),
        ("pitch_or_linear_size", c.c_uint32),  # w * h * bpp for compressed, w * bpp for uncompressed
        ("depth", c.c_uint32),
        ("mipmap_num", c.c_uint32),
        ("reserved", c.c_uint32 * 9),          # Reserved1
        ("tool_name", c.c_char * 4),           # Reserved1
        ("null", c.c_uint32),                  # Reserved1
        ("pixel_format", DDSPixelFormat),
        ("caps", c.c_uint32),                  # DDS_CAPS
        ("caps2", c.c_uint32),                 # DDS_CAPS2
        ("reserved2", c.c_uint32 * 3),         # ReservedCpas, Reserved2
    ]

    def __init__(self):
        super().__init__()
        self.magic = DDSHeader.MAGIC
        self.head_size = 124
        self.mipmap_num = 1
        self.pixel_format = DDSPixelFormat()
        self.reserved = (c.c_uint32 * 9)((0) * 9)
        self.tool_name = b"UEDT"
        self.null = 0
        self.reserved2 = (c.c_uint32*3)(0, 0, 0)
        self.dx10_header = DX10Header()

        self.dxgi_format = DXGI_FORMAT.UNKNOWN
        self.byte_per_pixel = 0

    @staticmethod
    def read(f: IOBase) -> "DDSHeader":
        """Read dds header."""
        head = DDSHeader()
        f.readinto(head)
        head.mipmap_num += head.mipmap_num == 0
        head.depth += head.depth == 0

        # DXT10 header
        if head.pixel_format.is_dx10():
            f.readinto(head.dx10_header)
            head.dxgi_format = head.dx10_header.get_dxgi()
        else:
            head.dxgi_format = head.pixel_format.get_dxgi()
            head.dx10_header.update(head.dxgi_format, head.is_cube(), head.is_3d(), 1)
        head.byte_per_pixel = DXGI_BYTE_PER_PIXEL[head.dxgi_format]

        # Raise errors for unsupported files
        if head.magic != DDSHeader.MAGIC or head.head_size != 124:
            raise RuntimeError("Not DDS file.")
        if head.dx10_header.resource_dimension == 2:
            raise RuntimeError("1D textures are unsupported.")

        return head

    @staticmethod
    def read_from_file(file_name: str) -> "DDSHeader":
        """Read dds header from a file."""
        with open(file_name, "rb") as f:
            head = DDSHeader.read(f)
        return head

    def write(self, f: IOBase):
        f.write(self)
        if self.pixel_format.is_dx10():
            f.write(self.dx10_header)

    def update(self, width, height, depth, mipmap_num, dxgi_format: DXGI_FORMAT, is_cube, array_size):
        self.width = width
        self.height = height
        self.depth = depth
        self.mipmap_num = mipmap_num
        if isinstance(dxgi_format, str):
            self.dxgi_format = DXGI_FORMAT[dxgi_format]
        else:
            self.dxgi_format = dxgi_format

        has_mips = self.has_mips()
        is_3d = self.is_3d()
        bpp = self.get_bpp()

        self.flags = DDS_FLAGS.get_flags(self.is_compressed(), is_3d)
        if self.is_compressed():
            self.pitch_or_linear_size = int(width * height * bpp)
        else:
            self.pitch_or_linear_size = int(width * bpp)
        self.caps = DDS_CAPS.get_caps(has_mips, is_cube)
        self.caps2 = DDS_CAPS2.get_caps2(is_cube, is_3d)
        self.dx10_header.update(self.dxgi_format, is_cube, is_3d, array_size)
        self.pixel_format.update(self.dxgi_format)

    def is_compressed(self):
        return DXGI_FORMAT.is_compressed(self.dxgi_format)

    def get_block_size(self):
        return DXGI_FORMAT.get_block_size(self.dxgi_format)

    def has_mips(self):
        return self.mipmap_num > 1

    def is_cube(self):
        return DDS_CAPS2.is_cube(self.caps2)

    def is_3d(self):
        return self.depth > 1

    def is_array(self):
        return self.dx10_header.is_array()

    def is_hdr(self):
        return is_hdr(self.dxgi_format.name)

    def is_normals(self):
        dxgi = self.get_format_as_str()
        return "BC5" in dxgi or dxgi == "R8G8_UNORM"

    def get_format_as_str(self):
        return self.dxgi_format.name

    def is_srgb(self):
        return "SRGB" in self.dxgi_format.name

    def is_int(self):
        return "UINT" in self.dxgi_format.name or "SINT" in self.dxgi_format.name

    def is_canonical(self):
        return self.pixel_format.is_canonical()

    def convertible_to_tga(self):
        name = self.get_format_as_str()
        return convertible_to_tga(name)

    def convertible_to_hdr(self):
        name = self.get_format_as_str()
        return convertible_to_hdr(name)

    def get_bpp(self):
        return DXGI_BYTE_PER_PIXEL[self.dxgi_format]

    def get_array_size(self):
        return self.dx10_header.array_size

    def get_num_slices(self):
        return self.get_array_size() * self.depth * (1 + (self.is_cube() * 5))

    def get_texture_type(self):
        if self.is_3d():
            return "3D"
        if self.is_cube():
            t = "Cube"
        else:
            t = "2D"
        if self.is_array():
            t += "Array"
        return t

    def get_size_list(self):
        """Calculate mipmap sizes"""
        mipmap_size_list = []
        slice_size = 0
        height, width = self.height, self.width
        block_size = self.get_block_size()
        byte_per_pixel = self.get_bpp()

        def cail(val, unit):
            remain = val % unit
            val += (unit - remain) * (remain != 0)
            return val

        for i in range(self.mipmap_num):
            _width, _height = width, height
            if self.is_compressed():
                # mipmap sizes should be multiples of block_size
                _width = cail(width, block_size)
                _height = cail(height, block_size)

            mipmap_size_list.append([_width, _height])
            slice_size += _width * _height * byte_per_pixel
            if slice_size != int(slice_size):
                raise RuntimeError(
                    "The size of mipmap data is not int. This is unexpected."
                )
            width, height = width // 2, height // 2
            width, height = max(block_size, width), max(block_size, height)

        return mipmap_size_list, int(slice_size)

    def print(self):
        print(f"  type: {self.get_texture_type()}")
        print(f"  format: {self.get_format_as_str()}")
        print(f"  width: {self.width}")
        print(f"  height: {self.height}")
        if self.is_3d():
            print(f"  depth: {self.depth}")
        elif self.is_array():
            print(f"  array_size: {self.get_array_size()}")
        else:
            print(f"  mipmaps: {self.mipmap_num}")

    def disassemble(self):
        self.update(self.width, self.height, 1, self.mipmap_num, self.dxgi_format, self.is_cube(), 1)

    def assemble(self, is_array, size):
        if is_array:
            self.update(self.width, self.height, 1, self.mipmap_num, self.dxgi_format, self.is_cube(), size)
        else:
            self.update(self.width, self.height, size, self.mipmap_num, self.dxgi_format, self.is_cube(), 1)


class DDS:
    def __init__(self, header: DDSHeader, slices: list[bytes] = None, mipmap_sizes: list[list[int]] = None):
        self.header = header
        self.slice_bin_list = slices
        self.mipmap_size_list = mipmap_sizes

    @staticmethod
    def load(file: str, verbose=False):
        if file[-3:] not in ["dds", "DDS"]:
            raise RuntimeError(f"Not DDS. ({file})")
        print("load: " + file)
        with open(file, "rb") as f:
            end_offset = get_size(f)

            # read header
            header = DDSHeader.read(f)

            mipmap_sizes, slice_size = header.get_size_list()
            num_slices = header.get_num_slices()

            # read texture data
            slices = []
            for i in range(num_slices):
                data = read_buffer(f, slice_size, end_offset)
                slices.append(data)

            dds = DDS(header, slices, mipmap_sizes)
            dds.print(verbose)

            if f.tell() != end_offset:
                raise RuntimeError(f"Parse failed. (Not the end of the file. Offset: {f.tell()})")

        return dds

    # save as dds
    def save(self, file: str):
        print("save: {}".format(file))
        folder = os.path.dirname(file)
        if folder not in [".", ""] and not os.path.exists(folder):
            mkdir(folder)

        with open(file, "wb") as f:
            # write header
            self.header.write(f)

            # write mipmap data
            for d in self.slice_bin_list:
                f.write(d)

    def get_texture_type(self):
        return self.header.get_texture_type()

    def is_cube(self):
        return self.header.is_cube()

    def get_array_size(self):
        return self.header.get_array_size()

    def get_disassembled_dds_list(self):
        new_dds_num = self.header.depth * self.get_array_size()
        num_slices = 1 + (5 * self.is_cube())
        self.header.disassemble()
        dds_list = []
        for i in range(new_dds_num):
            dds = DDS(
                self.header,
                self.slice_bin_list[i * num_slices: (i + 1) * num_slices],
                self.mipmap_size_list
            )
            dds_list.append(dds)
        return dds_list

    @staticmethod
    def assemble(dds_list, is_array=True):
        header = dds_list[0].header
        header.assemble(is_array, len(dds_list))
        for dds in dds_list[1:]:
            if header.dxgi_format != dds.header.dxgi_format:
                raise RuntimeError("Failed to assemble dds files. DXGI formats should be the same")
            if dds_list[0].mipmap_size_list != dds.mipmap_size_list:
                raise RuntimeError("Failed to assemble dds files. Texture sizes should be the same")
        slice_bin_list = sum([dds.slice_bin_list for dds in dds_list], [])
        return DDS(header, slice_bin_list, dds_list[0].mipmap_size_list)

    def print(self, verbose):
        self.header.print()
        if verbose:
            # print mipmap info
            for i, size in zip(range(len(self.mipmap_size_list)), self.mipmap_size_list):
                print(f"  Mipmap {i}")
                width, height = size
                print(f"    size (w, h): ({width}, {height})")
