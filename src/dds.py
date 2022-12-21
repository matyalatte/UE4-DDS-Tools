"""Class for DDS files."""

import ctypes as c
from enum import Enum
import os

import io_util


# https://docs.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format
class DXGI_FORMAT(Enum):
    """Enum for DDS format."""
    DXGI_FORMAT_UNKNOWN = 0
    DXGI_FORMAT_R32G32B32A32_TYPELESS = 1
    DXGI_FORMAT_R32G32B32A32_FLOAT = 2
    DXGI_FORMAT_R32G32B32A32_UINT = 3
    DXGI_FORMAT_R32G32B32A32_SINT = 4
    DXGI_FORMAT_R32G32B32_TYPELESS = 5
    DXGI_FORMAT_R32G32B32_FLOAT = 6
    DXGI_FORMAT_R32G32B32_UINT = 7
    DXGI_FORMAT_R32G32B32_SINT = 8
    DXGI_FORMAT_R16G16B16A16_TYPELESS = 9
    DXGI_FORMAT_R16G16B16A16_FLOAT = 10
    DXGI_FORMAT_R16G16B16A16_UNORM = 11
    DXGI_FORMAT_R16G16B16A16_UINT = 12
    DXGI_FORMAT_R16G16B16A16_SNORM = 13
    DXGI_FORMAT_R16G16B16A16_SINT = 14
    DXGI_FORMAT_R32G32_TYPELESS = 15
    DXGI_FORMAT_R32G32_FLOAT = 16
    DXGI_FORMAT_R32G32_UINT = 17
    DXGI_FORMAT_R32G32_SINT = 18
    DXGI_FORMAT_R32G8X24_TYPELESS = 19
    DXGI_FORMAT_D32_FLOAT_S8X24_UINT = 20
    DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS = 21
    DXGI_FORMAT_X32_TYPELESS_G8X24_UINT = 22
    DXGI_FORMAT_R10G10B10A2_TYPELESS = 23
    DXGI_FORMAT_R10G10B10A2_UNORM = 24
    DXGI_FORMAT_R10G10B10A2_UINT = 25
    DXGI_FORMAT_R11G11B10_FLOAT = 26
    DXGI_FORMAT_R8G8B8A8_TYPELESS = 27
    DXGI_FORMAT_R8G8B8A8_UNORM = 28
    DXGI_FORMAT_R8G8B8A8_UNORM_SRGB = 29
    DXGI_FORMAT_R8G8B8A8_UINT = 30
    DXGI_FORMAT_R8G8B8A8_SNORM = 31
    DXGI_FORMAT_R8G8B8A8_SINT = 32
    DXGI_FORMAT_R16G16_TYPELESS = 33
    DXGI_FORMAT_R16G16_FLOAT = 34
    DXGI_FORMAT_R16G16_UNORM = 35
    DXGI_FORMAT_R16G16_UINT = 36
    DXGI_FORMAT_R16G16_SNORM = 37
    DXGI_FORMAT_R16G16_SINT = 38
    DXGI_FORMAT_R32_TYPELESS = 39
    DXGI_FORMAT_D32_FLOAT = 40
    DXGI_FORMAT_R32_FLOAT = 41
    DXGI_FORMAT_R32_UINT = 42
    DXGI_FORMAT_R32_SINT = 43
    DXGI_FORMAT_R24G8_TYPELESS = 44
    DXGI_FORMAT_D24_UNORM_S8_UINT = 45
    DXGI_FORMAT_R24_UNORM_X8_TYPELESS = 46
    DXGI_FORMAT_X24_TYPELESS_G8_UINT = 47
    DXGI_FORMAT_R8G8_TYPELESS = 48
    DXGI_FORMAT_R8G8_UNORM = 49
    DXGI_FORMAT_R8G8_UINT = 50
    DXGI_FORMAT_R8G8_SNORM = 51
    DXGI_FORMAT_R8G8_SINT = 52
    DXGI_FORMAT_R16_TYPELESS = 53
    DXGI_FORMAT_R16_FLOAT = 54
    DXGI_FORMAT_D16_UNORM = 55
    DXGI_FORMAT_R16_UNORM = 56
    DXGI_FORMAT_R16_UINT = 57
    DXGI_FORMAT_R16_SNORM = 58
    DXGI_FORMAT_R16_SINT = 59
    DXGI_FORMAT_R8_TYPELESS = 60
    DXGI_FORMAT_R8_UNORM = 61
    DXGI_FORMAT_R8_UINT = 62
    DXGI_FORMAT_R8_SNORM = 63
    DXGI_FORMAT_R8_SINT = 64
    DXGI_FORMAT_A8_UNORM = 65
    DXGI_FORMAT_R1_UNORM = 66
    DXGI_FORMAT_R9G9B9E5_SHAREDEXP = 67
    DXGI_FORMAT_R8G8_B8G8_UNORM = 68
    DXGI_FORMAT_G8R8_G8B8_UNORM = 69
    DXGI_FORMAT_BC1_TYPELESS = 70
    DXGI_FORMAT_BC1_UNORM = 71
    DXGI_FORMAT_BC1_UNORM_SRGB = 72
    DXGI_FORMAT_BC2_TYPELESS = 73
    DXGI_FORMAT_BC2_UNORM = 74
    DXGI_FORMAT_BC2_UNORM_SRGB = 75
    DXGI_FORMAT_BC3_TYPELESS = 76
    DXGI_FORMAT_BC3_UNORM = 77
    DXGI_FORMAT_BC3_UNORM_SRGB = 78
    DXGI_FORMAT_BC4_TYPELESS = 79
    DXGI_FORMAT_BC4_UNORM = 80
    DXGI_FORMAT_BC4_SNORM = 81
    DXGI_FORMAT_BC5_TYPELESS = 82
    DXGI_FORMAT_BC5_UNORM = 83
    DXGI_FORMAT_BC5_SNORM = 84
    DXGI_FORMAT_B5G6R5_UNORM = 85
    DXGI_FORMAT_B5G5R5A1_UNORM = 86
    DXGI_FORMAT_B8G8R8A8_UNORM = 87
    DXGI_FORMAT_B8G8R8X8_UNORM = 88
    DXGI_FORMAT_R10G10B10_XR_BIAS_A2_UNORM = 89
    DXGI_FORMAT_B8G8R8A8_TYPELESS = 90
    DXGI_FORMAT_B8G8R8A8_UNORM_SRGB = 91
    DXGI_FORMAT_B8G8R8X8_TYPELESS = 92
    DXGI_FORMAT_B8G8R8X8_UNORM_SRGB = 93
    DXGI_FORMAT_BC6H_TYPELESS = 94
    DXGI_FORMAT_BC6H_UF16 = 95
    DXGI_FORMAT_BC6H_SF16 = 96
    DXGI_FORMAT_BC7_TYPELESS = 97
    DXGI_FORMAT_BC7_UNORM = 98
    DXGI_FORMAT_BC7_UNORM_SRGB = 99
    DXGI_FORMAT_AYUV = 100
    DXGI_FORMAT_Y410 = 101
    DXGI_FORMAT_Y416 = 102
    DXGI_FORMAT_NV12 = 103
    DXGI_FORMAT_P010 = 104
    DXGI_FORMAT_P016 = 105
    DXGI_FORMAT_420_OPAQUE = 106
    DXGI_FORMAT_YUY2 = 107
    DXGI_FORMAT_Y210 = 108
    DXGI_FORMAT_Y216 = 109
    DXGI_FORMAT_NV11 = 110
    DXGI_FORMAT_AI44 = 111
    DXGI_FORMAT_IA44 = 112
    DXGI_FORMAT_P8 = 113
    DXGI_FORMAT_A8P8 = 114
    DXGI_FORMAT_B4G4R4A4_UNORM = 115
    DXGI_FORMAT_P208 = 130
    DXGI_FORMAT_V208 = 131
    DXGI_FORMAT_V408 = 132
    DXGI_FORMAT_ASTC_4X4_TYPELESS = 133
    DXGI_FORMAT_ASTC_4X4_UNORM = 134
    # DXGI_FORMAT_SAMPLER_FEEDBACK_MIN_MIP_OPAQUE
    # DXGI_FORMAT_SAMPLER_FEEDBACK_MIP_REGION_USED_OPAQUE
    DXGI_FORMAT_FORCE_UINT = 0xffffffff

    @classmethod
    def is_valid_format(cls, fmt):
        return fmt in cls._member_names_

    @classmethod
    def get_max(cls):
        return 134

    @classmethod
    def get_max_canonical(cls):
        return 132


DXGI_BYTE_PER_PIXEL = {
    DXGI_FORMAT.DXGI_FORMAT_UNKNOWN: 0,
    DXGI_FORMAT.DXGI_FORMAT_R32G32B32A32_TYPELESS: 16,
    DXGI_FORMAT.DXGI_FORMAT_R32G32B32A32_FLOAT: 16,
    DXGI_FORMAT.DXGI_FORMAT_R32G32B32A32_UINT: 16,
    DXGI_FORMAT.DXGI_FORMAT_R32G32B32A32_SINT: 16,
    DXGI_FORMAT.DXGI_FORMAT_R32G32B32_TYPELESS: 12,
    DXGI_FORMAT.DXGI_FORMAT_R32G32B32_FLOAT: 12,
    DXGI_FORMAT.DXGI_FORMAT_R32G32B32_UINT: 12,
    DXGI_FORMAT.DXGI_FORMAT_R32G32B32_SINT: 12,
    DXGI_FORMAT.DXGI_FORMAT_R16G16B16A16_TYPELESS: 8,
    DXGI_FORMAT.DXGI_FORMAT_R16G16B16A16_FLOAT: 8,
    DXGI_FORMAT.DXGI_FORMAT_R16G16B16A16_UNORM: 8,
    DXGI_FORMAT.DXGI_FORMAT_R16G16B16A16_UINT: 8,
    DXGI_FORMAT.DXGI_FORMAT_R16G16B16A16_SNORM: 8,
    DXGI_FORMAT.DXGI_FORMAT_R16G16B16A16_SINT: 8,
    DXGI_FORMAT.DXGI_FORMAT_R32G32_TYPELESS: 8,
    DXGI_FORMAT.DXGI_FORMAT_R32G32_FLOAT: 8,
    DXGI_FORMAT.DXGI_FORMAT_R32G32_UINT: 8,
    DXGI_FORMAT.DXGI_FORMAT_R32G32_SINT: 8,
    DXGI_FORMAT.DXGI_FORMAT_R32G8X24_TYPELESS: 8,
    DXGI_FORMAT.DXGI_FORMAT_D32_FLOAT_S8X24_UINT: 8,
    DXGI_FORMAT.DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS: 8,
    DXGI_FORMAT.DXGI_FORMAT_X32_TYPELESS_G8X24_UINT: 8,
    DXGI_FORMAT.DXGI_FORMAT_R10G10B10A2_TYPELESS: 4,
    DXGI_FORMAT.DXGI_FORMAT_R10G10B10A2_UNORM: 4,
    DXGI_FORMAT.DXGI_FORMAT_R10G10B10A2_UINT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R11G11B10_FLOAT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R8G8B8A8_TYPELESS: 4,
    DXGI_FORMAT.DXGI_FORMAT_R8G8B8A8_UNORM: 4,
    DXGI_FORMAT.DXGI_FORMAT_R8G8B8A8_UNORM_SRGB: 4,
    DXGI_FORMAT.DXGI_FORMAT_R8G8B8A8_UINT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R8G8B8A8_SNORM: 4,
    DXGI_FORMAT.DXGI_FORMAT_R8G8B8A8_SINT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R16G16_TYPELESS: 4,
    DXGI_FORMAT.DXGI_FORMAT_R16G16_FLOAT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R16G16_UNORM: 4,
    DXGI_FORMAT.DXGI_FORMAT_R16G16_UINT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R16G16_SNORM: 4,
    DXGI_FORMAT.DXGI_FORMAT_R16G16_SINT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R32_TYPELESS: 4,
    DXGI_FORMAT.DXGI_FORMAT_D32_FLOAT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R32_FLOAT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R32_UINT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R32_SINT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R24G8_TYPELESS: 4,
    DXGI_FORMAT.DXGI_FORMAT_D24_UNORM_S8_UINT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R24_UNORM_X8_TYPELESS: 4,
    DXGI_FORMAT.DXGI_FORMAT_X24_TYPELESS_G8_UINT: 4,
    DXGI_FORMAT.DXGI_FORMAT_R8G8_TYPELESS: 2,
    DXGI_FORMAT.DXGI_FORMAT_R8G8_UNORM: 2,
    DXGI_FORMAT.DXGI_FORMAT_R8G8_UINT: 2,
    DXGI_FORMAT.DXGI_FORMAT_R8G8_SNORM: 2,
    DXGI_FORMAT.DXGI_FORMAT_R8G8_SINT: 2,
    DXGI_FORMAT.DXGI_FORMAT_R16_TYPELESS: 2,
    DXGI_FORMAT.DXGI_FORMAT_R16_FLOAT: 2,
    DXGI_FORMAT.DXGI_FORMAT_D16_UNORM: 2,
    DXGI_FORMAT.DXGI_FORMAT_R16_UNORM: 2,
    DXGI_FORMAT.DXGI_FORMAT_R16_UINT: 2,
    DXGI_FORMAT.DXGI_FORMAT_R16_SNORM: 2,
    DXGI_FORMAT.DXGI_FORMAT_R16_SINT: 2,
    DXGI_FORMAT.DXGI_FORMAT_R8_TYPELESS: 1,
    DXGI_FORMAT.DXGI_FORMAT_R8_UNORM: 1,
    DXGI_FORMAT.DXGI_FORMAT_R8_UINT: 1,
    DXGI_FORMAT.DXGI_FORMAT_R8_SNORM: 1,
    DXGI_FORMAT.DXGI_FORMAT_R8_SINT: 1,
    DXGI_FORMAT.DXGI_FORMAT_A8_UNORM: 1,
    DXGI_FORMAT.DXGI_FORMAT_R1_UNORM: 0.125,
    DXGI_FORMAT.DXGI_FORMAT_R9G9B9E5_SHAREDEXP: 4,
    DXGI_FORMAT.DXGI_FORMAT_R8G8_B8G8_UNORM: 4,
    DXGI_FORMAT.DXGI_FORMAT_G8R8_G8B8_UNORM: 4,
    DXGI_FORMAT.DXGI_FORMAT_BC1_TYPELESS: 0.5,
    DXGI_FORMAT.DXGI_FORMAT_BC1_UNORM: 0.5,
    DXGI_FORMAT.DXGI_FORMAT_BC1_UNORM_SRGB: 0.5,
    DXGI_FORMAT.DXGI_FORMAT_BC2_TYPELESS: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC2_UNORM: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC2_UNORM_SRGB: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC3_TYPELESS: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC3_UNORM: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC3_UNORM_SRGB: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC4_TYPELESS: 0.5,
    DXGI_FORMAT.DXGI_FORMAT_BC4_UNORM: 0.5,
    DXGI_FORMAT.DXGI_FORMAT_BC4_SNORM: 0.5,
    DXGI_FORMAT.DXGI_FORMAT_BC5_TYPELESS: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC5_UNORM: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC5_SNORM: 1,
    DXGI_FORMAT.DXGI_FORMAT_B5G6R5_UNORM: 2,
    DXGI_FORMAT.DXGI_FORMAT_B5G5R5A1_UNORM: 2,
    DXGI_FORMAT.DXGI_FORMAT_B8G8R8A8_UNORM: 4,
    DXGI_FORMAT.DXGI_FORMAT_B8G8R8X8_UNORM: 4,
    DXGI_FORMAT.DXGI_FORMAT_R10G10B10_XR_BIAS_A2_UNORM: 4,
    DXGI_FORMAT.DXGI_FORMAT_B8G8R8A8_TYPELESS: 4,
    DXGI_FORMAT.DXGI_FORMAT_B8G8R8A8_UNORM_SRGB: 4,
    DXGI_FORMAT.DXGI_FORMAT_B8G8R8X8_TYPELESS: 4,
    DXGI_FORMAT.DXGI_FORMAT_B8G8R8X8_UNORM_SRGB: 4,
    DXGI_FORMAT.DXGI_FORMAT_BC6H_TYPELESS: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC6H_UF16: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC6H_SF16: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC7_TYPELESS: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC7_UNORM: 1,
    DXGI_FORMAT.DXGI_FORMAT_BC7_UNORM_SRGB: 1,
    DXGI_FORMAT.DXGI_FORMAT_AYUV: 4,
    DXGI_FORMAT.DXGI_FORMAT_Y410: 4,
    DXGI_FORMAT.DXGI_FORMAT_Y416: 8,
    DXGI_FORMAT.DXGI_FORMAT_NV12: 1.5,
    DXGI_FORMAT.DXGI_FORMAT_P010: 3,
    DXGI_FORMAT.DXGI_FORMAT_P016: 3,
    DXGI_FORMAT.DXGI_FORMAT_420_OPAQUE: 1.5,
    DXGI_FORMAT.DXGI_FORMAT_YUY2: 4,
    DXGI_FORMAT.DXGI_FORMAT_Y210: 8,
    DXGI_FORMAT.DXGI_FORMAT_Y216: 8,
    DXGI_FORMAT.DXGI_FORMAT_NV11: 1.5,
    DXGI_FORMAT.DXGI_FORMAT_AI44: 1,
    DXGI_FORMAT.DXGI_FORMAT_IA44: 1,
    DXGI_FORMAT.DXGI_FORMAT_P8: 1,
    DXGI_FORMAT.DXGI_FORMAT_A8P8: 2,
    DXGI_FORMAT.DXGI_FORMAT_B4G4R4A4_UNORM: 2,
    DXGI_FORMAT.DXGI_FORMAT_P208: 2,
    DXGI_FORMAT.DXGI_FORMAT_V208: 2,
    DXGI_FORMAT.DXGI_FORMAT_V408: 3,
    DXGI_FORMAT.DXGI_FORMAT_ASTC_4X4_TYPELESS: 8,
    DXGI_FORMAT.DXGI_FORMAT_ASTC_4X4_UNORM: 8
}


def int_to_byte(n, length=1):
    return n.to_bytes(length, byteorder="little")


DDS_PIXELFORMAT_TO_DXGI = [
    [[b'DXT1'], DXGI_FORMAT.DXGI_FORMAT_BC1_UNORM],
    [[b'DXT2', b'DXT3'], DXGI_FORMAT.DXGI_FORMAT_BC2_UNORM],
    [[b'DXT4', b'DXT5'], DXGI_FORMAT.DXGI_FORMAT_BC3_UNORM],
    [[b'ATI1', b'BC4U', b'3DC1'], DXGI_FORMAT.DXGI_FORMAT_BC4_UNORM],
    [[b'ATI2', b'BC5U', b'3DC2'], DXGI_FORMAT.DXGI_FORMAT_BC5_UNORM],
    [[b'BC4S'], DXGI_FORMAT.DXGI_FORMAT_BC4_SNORM],
    [[b'BC5S'], DXGI_FORMAT.DXGI_FORMAT_BC5_SNORM],
    [[b'BC6H'], DXGI_FORMAT.DXGI_FORMAT_BC6H_UF16],
    [[b'BC7L', b'BC7'], DXGI_FORMAT.DXGI_FORMAT_BC7_UNORM],
    [[b'RGBG'], DXGI_FORMAT.DXGI_FORMAT_R8G8_B8G8_UNORM],
    [[b'GRGB'], DXGI_FORMAT.DXGI_FORMAT_G8R8_G8B8_UNORM],
    [[b'YUY2', b'UYVY'], DXGI_FORMAT.DXGI_FORMAT_YUY2],
    [[int_to_byte(36)], DXGI_FORMAT.DXGI_FORMAT_R16G16B16A16_UNORM],
    [[int_to_byte(110)], DXGI_FORMAT.DXGI_FORMAT_R16G16B16A16_SNORM],
    [[int_to_byte(111)], DXGI_FORMAT.DXGI_FORMAT_R16_FLOAT],
    [[int_to_byte(112)], DXGI_FORMAT.DXGI_FORMAT_R16G16_FLOAT],
    [[int_to_byte(113)], DXGI_FORMAT.DXGI_FORMAT_R16G16B16A16_FLOAT],
    [[int_to_byte(114)], DXGI_FORMAT.DXGI_FORMAT_R32_FLOAT],
    [[int_to_byte(115)], DXGI_FORMAT.DXGI_FORMAT_R32G32_FLOAT],
    [[int_to_byte(116)], DXGI_FORMAT.DXGI_FORMAT_R32G32B32A32_FLOAT]
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
    "BC2_TYPELESS",
    "BC2_UNORM",
    "BC3_TYPELESS",
    "BC3_UNORM",
    "BC7_TYPELESS",
    "BC7_UNORM",
    "BC1_UNORM_SRGB",
    "BC2_UNORM_SRGB",
    "BC3_UNORM_SRGB",
    "BC7_UNORM_SRGB",
    "BC4_TYPELESS",
    "BC4_UNORM",
    "BC4_SNORM",

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

# fourCC for uncanonical formats (ETC, PVRTC, ATITC, ASTC)
UNCANONICAL_FOURCC = [
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


def get_dds_format(fmt):
    """Convert raw format data to string."""
    for pxlfmt, dxgi in DDS_PIXELFORMAT_TO_DXGI:
        if fmt in pxlfmt:
            return dxgi
    print("Failed to detect dxgi format. It'll be loaded as a B8G8R8A8 texture.")
    return DXGI_FORMAT.DXGI_FORMAT_B8G8R8A8_UNORM


def is_hdr(name):
    return 'BC6' in name or 'FLOAT' in name


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
        ("pfflags", c.c_uint32),             # PfFlags == 4
        ("fourCC", c.c_char * 4),            # FourCC
        ("bit_count_mask", c.c_uint32 * 5),  # Bitcount, Bitmask (null * 5)
        ("caps", c.c_uint8 * 4),             # [8 * hasMips, 16, 64 * hasMips, 0]
        ("caps2", c.c_uint8 * 4),            # [0, 254 * isCubeMap, 0, 0]
        ("reserved2", c.c_uint32 * 3),       # ReservedCpas, Reserved2
    ]

    def initialize(self, width, height, mipmap_num, dxgi_format):
        self.width = width
        self.height = height
        self.mipmap_num = mipmap_num
        if isinstance(dxgi_format, str):
            self.dxgi_format = DXGI_FORMAT["DXGI_FORMAT_" + dxgi_format]
        else:
            self.dxgi_format = dxgi_format

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
            head.dxgi_format = get_dds_format(head.fourCC)
        head.byte_per_pixel = DXGI_BYTE_PER_PIXEL[head.dxgi_format]
        head.texture_type = ['2D', 'Cube'][head.is_cube()]
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
            io_util.write_uint32(f, self.dxgi_format.value)
            io_util.write_uint32(f, 3)
            io_util.write_uint32(f, 4 * self.is_cube())
            io_util.write_uint32(f, 1)
            io_util.write_uint32(f, 0)

    def update(self):
        has_mips = self.mipmap_num > 1
        is_cube = self.is_cube()
        self.magic = DDSHeader.MAGIC
        self.head_size = 124
        self.flags = (c.c_uint8*4)(7, 16, 8 + 2 * has_mips, 0)
        self.pitch_size = int(self.width * self.height * self.get_bpp() * (1 + (is_cube) * 5))
        self.depth = 1
        self.reserved = (c.c_uint32*9)(0, 0, 0, 0, 0, 0, 0, 0, 0)
        self.tool_name = 'MATY'.encode()
        self.null = 0
        self.pfsize = 32
        self.pfflags = 4
        self.bit_count_mask = (c.c_uint32 * 5)(0, 0, 0, 0, 0)
        self.caps = (c.c_uint8 * 4)(8 * has_mips, 16, 64 * has_mips, 0)
        self.caps2 = (c.c_uint8 * 4)(0, 254 * is_cube, 0, 0)
        self.reserved2 = (c.c_uint32*3)(0, 0, 0)
        self.fourCC = b'DX10'
        self.texture_type = ['2D', 'Cube'][is_cube]

    def is_cube(self):
        return self.caps2[1] == 254

    def is_3d(self):
        return self.depth > 1

    def is_hdr(self):
        return is_hdr(self.dxgi_format.name)

    def is_bc5(self):
        return 'BC5' in self.dxgi_format.name

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

    def print(self):
        print(f'  height: {self.height}')
        print(f'  width: {self.width}')
        print(f'  format: {self.dxgi_format.name[12:]}')
        print(f'  mipmap num: {self.mipmap_num}')
        print(f'  cubemap: {self.is_cube()}')


class DDS:
    def __init__(self, header, mipmap_data, mipmap_size):
        self.header = header
        self.mipmap_data = mipmap_data
        self.mipmap_size = mipmap_size

    def load(file, verbose=False):
        if file[-3:] not in ['dds', 'DDS']:
            raise RuntimeError('Not DDS. ({})'.format(file))
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

    def utexture_to_DDS(utexture):
        # make dds header
        header = DDSHeader()
        header.initialize(0, 0, 0, utexture.dxgi_format)
        header.caps2[1] = 254 * (utexture.texture_type == "Cube")
        header.update()

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
