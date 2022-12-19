# classes for dds files

import os
import ctypes as c
import io_util
from utexture import BYTE_PER_PIXEL

# https://docs.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format
DDS_FORMAT = {
    'DXT1/BC1': ['DXT1', 71],          # DXGI_FORMAT_BC1_UNORM
    'DXT5/BC3': ['DXT5', 77],          # DXGI_FORMAT_BC3_UNORM
    'BC4/ATI1': [80, 'ATI1', 'BC4U'],  # DXGI_FORMAT_BC4_UNORM
    'BC4(signed)': [81],               # DXGI_FORMAT_BC4_SNORM
    'BC5/ATI2': [83, 'ATI2', 'BC5U'],  # DXGI_FORMAT_BC5_UNORM
    'BC5(signed)': [84],               # DXGI_FORMAT_BC5_SNORM
    'BC6H(unsigned)': [95],            # DXGI_FORMAT_BC6H_UF16
    'BC6H(signed)': [96],              # DXGI_FORMAT_BC6H_SF16
    'BC7': [98, 99],                   # DXGI_FORMAT_BC7_TYPELESS
    'FloatRGBA': [10],                 # DXGI_FORMAT_R16G16B16A16_FLOAT
    'B8G8R8A8': [87],                  # DXGI_FORMAT_B8G8R8A8_UNORM
    'ASTC_4X4': [134]                  # DXGI_FORMAT_ASTC_4X4_UNORM
}


def get_dds_format(form):
    for k in DDS_FORMAT:
        if form in DDS_FORMAT[k]:
            return k
    raise RuntimeError('Unsupported DDS format. ({})'.format(form))


class DDSHeader(c.LittleEndianStructure):
    MAGIC = b'\x44\x44\x53\x20'
    _pack_ = 1
    _fields_ = [
        ("magic", c.c_char*4),        # Magic=='DDS '
        ("head_size", c.c_uint32),    # Size==124
        ("flags", c.c_uint8*4),       # [7, 16, 8+2*hasMips, 0]
        ("height", c.c_uint32),
        ("width", c.c_uint32),
        ("pitch_size", c.c_uint32),   # Data size of the largest mipmap
        ("depth", c.c_uint32),        # Depth==1
        ("mipmap_num", c.c_uint32),
        ("reserved", c.c_uint32*9),   # Reserved1
        ("tool_name", c.c_char*4),    # Reserved1
        ("null", c.c_uint32),         # Reserved1
        ("pfsize", c.c_uint32),       # PfSize==32
        ("pfflags", c.c_uint32),      # PfFlags==4
        ("fourCC", c.c_char*4),       # FourCC
        ("bit_count_mask", c.c_uint32*5),  # Bitcount, Bitmask (null*5)
        ("caps", c.c_uint8*4),        # [8*hasMips, 16, 64*hasMips, 0]
        ("caps2", c.c_uint8*4),       # [0, 254*isCubeMap, 0, 0]
        ("reserved2", c.c_uint32*3),  # ReservedCpas, Reserved2
    ]

    def init(self, width, height, mipmap_num, format_name, texture_type):
        self.width = width
        self.height = height
        self.mipmap_num = mipmap_num
        self.format_name = format_name
        self.texture_type = texture_type
        self.update()

    def update(self):
        has_mips = self.mipmap_num > 1
        is_cube = self.texture_type == 'Cube'
        self.byte_per_pixel = BYTE_PER_PIXEL[self.format_name]

        self.magic = DDSHeader.MAGIC
        self.head_size = 124
        self.flags = (c.c_uint8*4)(7, 16, 8 + 2 * has_mips, 0)
        self.pitch_size = int(self.width * self.height * self.byte_per_pixel * (1 + (is_cube) * 5))
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

        self.dxgi_format = DDS_FORMAT[self.format_name][0]
        if isinstance(self.dxgi_format, str):
            self.fourCC = self.dxgi_format.encode()
        else:
            self.fourCC = b'DX10'

    @staticmethod
    def read(f):
        head = DDSHeader()
        f.readinto(head)
        io_util.check(head.magic, DDSHeader.MAGIC, msg='Not DDS.')
        io_util.check(head.head_size, 124)
        head.mipmap_num += head.mipmap_num == 0
        cube_flag = head.caps2[1] == 254

        # DXT10 header
        if head.fourCC == b'DX10':
            head.dxgi_format = io_util.read_uint32(f)  # dxgiFormat
            io_util.read_const_uint32(f, 3)            # resourceDimension==3
            f.seek(4, 1)                       # miscFlag==0 or 4 (0 for 2D textures, 4 for Cube maps)
            io_util.read_const_uint32(f, 1)            # arraySize==1

            f.seek(4, 1)                       # miscFlag2
        else:
            head.dxgi_format = head.fourCC.decode()
        head.format_name = get_dds_format(head.dxgi_format)
        head.byte_per_pixel = BYTE_PER_PIXEL[head.format_name]

        head.texture_type = ['2D', 'Cube'][cube_flag]
        return head

    def write(f, header):
        header.update()
        f.write(header)

        # write dxt10 header
        if header.fourCC == b'DX10':
            io_util.write_uint32(f, header.dxgi_format)
            io_util.write_uint32_array(f, [3, 4 * (header.texture_type == 'Cube'), 1])
            io_util.write_uint32(f, 0)

    def print(self):
        print(f'  height: {self.height}')
        print(f'  width: {self.width}')
        print(f'  format: {self.format_name}')
        print(f'  mipmap num: {self.mipmap_num}')
        print(f'  texture type: {self.texture_type}')


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
            byte_per_pixel = header.byte_per_pixel

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

                width, height = width//2, height//2
                if byte_per_pixel < 4:
                    width, height = max(4, width), max(4, height)

            # read mipmaps
            mipmap_data = [b'']*mipmap_num
            for j in range(1 + (header.texture_type == 'Cube') * 5):
                for (width, height), i in zip(mipmap_size, range(mipmap_num)):
                    # read mipmap data
                    size = width*height*byte_per_pixel
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

    def asset_to_DDS(asset):
        # make dds header
        header = DDSHeader()
        header.init(0, 0, 0, asset.format_name, asset.texture_type)

        mipmap_data = []
        mipmap_size = []

        # get mipmaps
        for mip in asset.mipmaps:
            mipmap_data.append(mip.data)
            mipmap_size.append([mip.width, mip.height])

        # update header
        header.width, header.height = asset.get_max_size()
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
            DDSHeader.write(f, self.header)

            # write mipmap data
            for i in range(1 + (self.header.texture_type == 'Cube') * 5):
                for d in self.mipmap_data:
                    stride = len(d) // (1 + (self.header.texture_type == 'Cube') * 5)
                    f.write(d[i * stride: (i + 1) * stride])
