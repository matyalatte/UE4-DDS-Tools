"""Class for DDS files.

Notes:
    - Official document for DDS header
      https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-header
    - Official repo for DDS
      https://github.com/microsoft/DirectXTex
"""

import ctypes as c
from enum import IntEnum
import os

from dxgi_format import (DXGI_FORMAT, DXGI_BYTE_PER_PIXEL,
                         FOURCC_TO_DXGI, BITMASK_TO_DXGI)
import io_util


class PF_FLAGS(IntEnum):
    '''dwFlags for DDS_PIXELFORMAT'''
    # DDS_ALPHAPIXELS = 0x00000001
    # DDS_ALPHA = 0x00000002
    DDS_FOURCC = 0x00000004
    # DDS_RGB = 0x00000040
    # DDS_LUMINANCE = 0x00020000
    DDS_BUMPDUDV = 0x00080000


UNCANONICAL_FOURCC = [
    # fourCC for uncanonical formats (ETC, PVRTC, ATITC, ASTC)
    b"ETC",
    b"ETC1",
    b"ETC2",
    b"ET2A",
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


def is_hdr(name):
    return 'BC6' in name or 'FLOAT' in name or 'INT' in name or 'SNORM' in name


def convertible_to_tga(name):
    return name in TGA_SUPPORTED


def convertible_to_hdr(name):
    return name in HDR_SUPPORTED


class DDSHeader(c.LittleEndianStructure):
    MAGIC = b'DDS '
    _pack_ = 1
    _fields_ = [
        ("magic", c.c_char * 4),             # Magic == 'DDS '
        ("head_size", c.c_uint32),           # Size == 124
        ("flags", c.c_uint8 * 4),            # [7, 16, 8 + 2 * hasMips, 0]
        ("height", c.c_uint32),
        ("width", c.c_uint32),
        ("pitch_size", c.c_uint32),          # Data size of the largest mipmap
        ("depth", c.c_uint32),
        ("mipmap_num", c.c_uint32),
        ("reserved", c.c_uint32 * 9),        # Reserved1
        ("tool_name", c.c_char * 4),         # Reserved1
        ("null", c.c_uint32),                # Reserved1
        ("pfsize", c.c_uint32),              # PfSize == 32
        ("pfflags", c.c_uint32),             # PfFlags (if 4 then FourCC is used)
        ("fourCC", c.c_char * 4),            # FourCC
        ("bit_count", c.c_uint32),           # Bitcount
        ("bit_mask", c.c_uint32 * 4),        # Bitmask
        ("caps", c.c_uint8 * 4),             # [8 * hasMips, 16, 64 * hasMips, 0]
        ("caps2", c.c_uint8 * 4),            # [0, 254 * isCubeMap, 0, 0]
        ("reserved2", c.c_uint32 * 3),       # ReservedCpas, Reserved2
    ]

    def __init__(self):
        super().__init__()
        self.mipmap_num = 0
        self.dxgi_format = DXGI_FORMAT.DXGI_FORMAT_UNKNOWN
        self.byte_per_pixel = 0

    @staticmethod
    def read(f):
        """Read dds header."""
        head = DDSHeader()
        f.readinto(head)
        io_util.check(head.magic, DDSHeader.MAGIC, msg='Not DDS.')
        io_util.check(head.head_size, 124, msg='Not DDS.')
        head.mipmap_num += head.mipmap_num == 0

        ERR_MSG = "Customized formats (e.g. ETC, PVRTC, ATITC, and ASTC) are unsupported."

        if not head.is_canonical():
            raise RuntimeError(f"Non-standard fourCC detected. ({head.fourCC.decode()})\n" + ERR_MSG)

        # DXT10 header
        if head.fourCC == b'DX10':
            fmt = io_util.read_uint32(f)
            if fmt > DXGI_FORMAT.get_max():
                raise RuntimeError(f"Unsupported DXGI format detected. ({fmt})\n" + ERR_MSG)

            head.dxgi_format = DXGI_FORMAT(fmt)  # dxgiFormat
            io_util.read_const_uint32(f, 3)      # resourceDimension == 3
            f.seek(4, 1)                         # miscFlag == 0 or 4 (0 for 2D textures, 4 for Cube maps)
            io_util.read_const_uint32(f, 1)      # arraySize == 1
            f.seek(4, 1)                         # miscFlag2
        else:
            head.dxgi_format = head.get_dxgi_from_header()
        head.byte_per_pixel = DXGI_BYTE_PER_PIXEL[head.dxgi_format]
        return head

    @staticmethod
    def read_from_file(file_name):
        """Read dds header from a file."""
        with open(file_name, 'rb') as f:
            head = DDSHeader.read(f)
        return head

    def write(self, f):
        f.write(self)
        # DXT10 header
        if self.fourCC == b'DX10':
            io_util.write_uint32(f, self.dxgi_format)
            io_util.write_uint32(f, 3)
            io_util.write_uint32(f, 4 * self.is_cube())
            io_util.write_uint32(f, 1)
            io_util.write_uint32(f, 0)

    def update(self, width, height, mipmap_num, dxgi_format, is_cube):
        self.width = width
        self.height = height
        self.mipmap_num = mipmap_num
        if isinstance(dxgi_format, str):
            self.dxgi_format = DXGI_FORMAT["DXGI_FORMAT_" + dxgi_format]
        else:
            self.dxgi_format = dxgi_format

        has_mips = self.mipmap_num > 1

        self.magic = DDSHeader.MAGIC
        self.head_size = 124
        self.flags = (c.c_uint8*4)(7, 16, 8 + 2 * has_mips, 0)
        self.pitch_size = int(self.width * self.height * self.get_bpp() * (1 + (is_cube) * 5))
        self.depth = 1
        self.reserved = (c.c_uint32 * 9)((0) * 9)
        self.tool_name = 'MATY'.encode()
        self.null = 0
        self.pfsize = 32
        self.pfflags = PF_FLAGS.DDS_FOURCC
        self.bit_count = (c.c_uint32)(0)
        self.bit_mask = (c.c_uint32 * 4)((0) * 4)
        self.caps = (c.c_uint8 * 4)(8 * has_mips, 16, 64 * has_mips, 0)
        self.caps2 = (c.c_uint8 * 4)(0, 254 * is_cube, 0, 0)
        self.reserved2 = (c.c_uint32*3)(0, 0, 0)
        self.fourCC = b'DX10'

    def is_bit_mask(self, bit_mask):
        for b1, b2 in zip(self.bit_mask, bit_mask):
            if b1 != b2:
                return False
        return True

    def get_dxgi_from_header(self):
        '''Similar method as GetDXGIFormat in DirectXTex/DDSTextureLoader/DDSTextureLoader12.cpp'''
        # Try to detect DXGI from fourCC.
        if self.pfflags & PF_FLAGS.DDS_FOURCC:
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
            return DXGI_FORMAT.DXGI_FORMAT_B8G8R8A8_UNORM

        if self.pfflags & PF_FLAGS.DDS_BUMPDUDV:
            # DXGI format should be signed.
            return DXGI_FORMAT.get_signed(detected_dxgi)
        else:
            return detected_dxgi

    def is_cube(self):
        return self.caps2[1] == 254

    def is_3d(self):
        return self.depth > 1

    def is_hdr(self):
        return is_hdr(self.dxgi_format.name)

    def is_normals(self):
        dxgi = self.dxgi_format.name[12:]
        return 'BC5' in dxgi or dxgi == 'R8G8_UNORM'

    def get_format_as_str(self):
        return self.dxgi_format.name

    def is_srgb(self):
        return 'SRGB' in self.dxgi_format.name

    def is_int(self):
        return 'UINT' in self.dxgi_format.name or 'SINT' in self.dxgi_format.name

    def is_canonical(self):
        return self.fourCC not in UNCANONICAL_FOURCC

    def convertible_to_tga(self):
        name = self.dxgi_format.name[12:]
        return convertible_to_tga(name)

    def convertible_to_hdr(self):
        name = self.dxgi_format.name[12:]
        return convertible_to_hdr(name)

    def get_bpp(self):
        return DXGI_BYTE_PER_PIXEL[self.dxgi_format]

    def get_texture_type(self):
        return ['2D', 'Cube'][self.is_cube()]

    def print(self):
        print(f'  width: {self.width}')
        print(f'  height: {self.height}')
        print(f'  format: {self.dxgi_format.name[12:]}')
        print(f'  mipmaps: {self.mipmap_num}')
        print(f'  cubemap: {self.is_cube()}')


class DDS:
    def __init__(self, header, mipmap_data, mipmap_size):
        self.header = header
        self.mipmap_data = mipmap_data
        self.mipmap_size = mipmap_size

    @staticmethod
    def load(file, verbose=False):
        if file[-3:] not in ['dds', 'DDS']:
            raise RuntimeError(f'Not DDS. ({file})')
        print('load: ' + file)
        with open(file, 'rb') as f:
            # read header
            header = DDSHeader.read(f)

            mipmap_num = header.mipmap_num
            byte_per_pixel = header.get_bpp()

            # calculate mipmap sizes
            mipmap_size = []
            height, width = header.height, header.width
            for i in range(mipmap_num):
                _width, _height = width, height
                if byte_per_pixel < 4:
                    # mipmap sizes should be multiples of 4
                    _width += (4 - width % 4) * (width % 4 != 0)
                    _height += (4 - height % 4) * (height % 4 != 0)

                mipmap_size.append([_width, _height])

                width, height = width // 2, height // 2
                if byte_per_pixel < 4:
                    width, height = max(4, width), max(4, height)

            # read mipmaps
            mipmap_data = [b''] * mipmap_num
            for j in range(1 + (header.is_cube()) * 5):
                for (width, height), i in zip(mipmap_size, range(mipmap_num)):
                    # read mipmap data
                    size = width * height * byte_per_pixel
                    if size != int(size):
                        raise RuntimeError(
                            'The size of mipmap data is not int. This is unexpected.'
                        )
                    data = f.read(int(size))

                    # store mipmap data
                    mipmap_data[i] = b''.join([mipmap_data[i], data])

            if verbose:
                # print mipmap info
                for i in range(mipmap_num):
                    print(f'  Mipmap {i}')
                    width, height = mipmap_size[i]
                    print(f'    size (w, h): ({width}, {height})')

            header.print()
            io_util.check(f.tell(), io_util.get_size(f), msg='Parse Failed. This is unexpected.')

        return DDS(header, mipmap_data, mipmap_size)

    @staticmethod
    def utexture_to_DDS(utexture):
        # make dds header
        header = DDSHeader()
        header.update(0, 0, 0, utexture.dxgi_format, utexture.is_cube)

        mipmap_data = []
        mipmap_size = []

        # get mipmaps
        for mip in utexture.mipmaps:
            mipmap_data.append(mip.data)
            mipmap_size.append([mip.width, mip.height])

        # update header
        header.width, header.height = utexture.get_max_size()
        header.mipmap_num = len(mipmap_data)

        return DDS(header, mipmap_data, mipmap_size)

    # save as dds
    def save(self, file):
        print('save: {}'.format(file))
        folder = os.path.dirname(file)
        if folder not in ['.', ''] and not os.path.exists(folder):
            io_util.mkdir(folder)

        with open(file, 'wb') as f:
            # write header
            self.header.write(f)

            # write mipmap data
            for i in range(1 + (self.header.is_cube()) * 5):
                for d in self.mipmap_data:
                    stride = len(d) // (1 + (self.header.is_cube()) * 5)
                    f.write(d[i * stride: (i + 1) * stride])

    def get_texture_type(self):
        return self.header.get_texture_type()

    def is_cube(self):
        return self.header.is_cube()
