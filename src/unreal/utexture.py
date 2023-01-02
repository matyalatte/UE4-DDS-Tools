'''Classes for texture assets (.uexp and .ubulk)'''
import io
import os
import io_util
from .uasset import Uasset
from .umipmap import Umipmap
from .version import VersionInfo
from dxgi_format import DXGI_FORMAT, DXGI_BYTE_PER_PIXEL


# Defined in UnrealEngine/Engine/Source/Runtime/D3D12RHI/Private/D3D12RHI.cpp
PF_TO_DXGI = {
    'PF_DXT1': DXGI_FORMAT.DXGI_FORMAT_BC1_UNORM,
    'PF_DXT3': DXGI_FORMAT.DXGI_FORMAT_BC2_UNORM,
    'PF_DXT5': DXGI_FORMAT.DXGI_FORMAT_BC3_UNORM,
    'PF_BC4': DXGI_FORMAT.DXGI_FORMAT_BC4_UNORM,
    'PF_BC5': DXGI_FORMAT.DXGI_FORMAT_BC5_UNORM,
    'PF_BC6H': DXGI_FORMAT.DXGI_FORMAT_BC6H_UF16,
    'PF_BC7': DXGI_FORMAT.DXGI_FORMAT_BC7_UNORM,
    'PF_A1': DXGI_FORMAT.DXGI_FORMAT_R1_UNORM,
    'PF_A8': DXGI_FORMAT.DXGI_FORMAT_A8_UNORM,
    'PF_G8': DXGI_FORMAT.DXGI_FORMAT_R8_UNORM,
    'PF_R8': DXGI_FORMAT.DXGI_FORMAT_R8_UNORM,
    'PF_R8G8': DXGI_FORMAT.DXGI_FORMAT_R8G8_UNORM,
    'PF_G16': DXGI_FORMAT.DXGI_FORMAT_R16_UNORM,
    'PF_G16R16': DXGI_FORMAT.DXGI_FORMAT_R16G16_UNORM,
    'PF_B8G8R8A8': DXGI_FORMAT.DXGI_FORMAT_B8G8R8A8_UNORM,
    'PF_A2B10G10R10': DXGI_FORMAT.DXGI_FORMAT_R10G10B10A2_UNORM,
    'PF_A16B16G16R16': DXGI_FORMAT.DXGI_FORMAT_R16G16B16A16_UNORM,
    'PF_FloatRGB': DXGI_FORMAT.DXGI_FORMAT_R11G11B10_FLOAT,
    'PF_FloatR11G11B10': DXGI_FORMAT.DXGI_FORMAT_R11G11B10_FLOAT,
    'PF_FloatRGBA': DXGI_FORMAT.DXGI_FORMAT_R16G16B16A16_FLOAT,
    'PF_A32B32G32R32F': DXGI_FORMAT.DXGI_FORMAT_R32G32B32A32_FLOAT,
    'PF_B5G5R5A1_UNORM': DXGI_FORMAT.DXGI_FORMAT_B5G5R5A1_UNORM,
    'PF_ASTC_4x4': DXGI_FORMAT.DXGI_FORMAT_ASTC_4X4_UNORM
}

PF_TO_UNCOMPRESSED = {
    'PF_DXT1': 'PF_B8G8R8A8',
    'PF_DXT3': 'PF_B8G8R8A8',
    'PF_DXT5': 'PF_B8G8R8A8',
    'PF_BC4': 'PF_G8',
    'PF_BC5': 'PF_R8G8',
    'PF_BC6H': 'PF_FloatRGBA',
    'PF_BC7': 'PF_B8G8R8A8',
    'PF_ASTC_4x4': 'PF_B8G8R8A8'
}


def is_power_of_2(n):
    if n == 1:
        return True
    if n % 2 != 0:
        return False
    return is_power_of_2(n // 2)


EXT = ['.uasset', '.uexp', '.ubulk']


def get_all_file_path(file):
    '''Get all file paths for texture asset from a file path.'''
    base_name, ext = os.path.splitext(file)
    if ext not in EXT:
        raise RuntimeError(f'Not Uasset. ({file})')
    return [base_name + ext for ext in EXT]


VERSION_ERR_MSG = 'Make sure you specified UE4 version correctly.'


def skip_unversioned_headers(f):
    uhead = io_util.read_uint8_array(f, 2)
    is_last = uhead[1] % 2 == 0
    while is_last:
        uhead = io_util.read_uint8_array(f, 2)
        is_last = uhead[1] % 2 == 0
        if f.tell() > 100:
            raise RuntimeError('Parse Failed. ' + VERSION_ERR_MSG)


class Utexture:
    UNREAL_SIGNATURE = b'\xC1\x83\x2A\x9E'
    UBULK_FLAG = [0, 16384]

    def __init__(self, file_path, version='ff7r', verbose=False):
        self.version = VersionInfo(version)

        if not os.path.isfile(file_path):
            raise RuntimeError(f'Not File. ({file_path})')

        uasset_name, uexp_name, ubulk_name = get_all_file_path(file_path)
        print('load: ' + uasset_name)

        # read .uasset
        self.uasset = Uasset(uasset_name, self.version)
        self.unversioned = self.uasset.header.unversioned
        self.nouexp = self.uasset.nouexp
        if self.version <= '4.15':
            if not self.nouexp:
                raise RuntimeError('Uexp should not exist.')
        elif self.nouexp:
            raise RuntimeError('Uexp should exist.')

        if len(self.uasset.exports) != 1:
            raise RuntimeError('Unexpected number of exports')

        self.uasset_size = self.uasset.size
        self.name_list = self.uasset.name_list
        self.texture_type = self.uasset.texture_type

        # read .uexp
        if self.nouexp:
            with open(uasset_name, 'rb') as f:
                f.seek(self.uasset_size)
                uexp = f.read(self.uasset.exports[0].size)
            f = io.BytesIO(uexp)
        else:
            f = open(uexp_name, 'rb')

        self.read_uexp(f)

        if not self.nouexp:
            foot = f.read(4)
            io_util.check(foot, Utexture.UNREAL_SIGNATURE, f)
        f.close()

        # read .ubulk
        if self.has_ubulk:
            if self.nouexp:
                with open(uasset_name, 'rb') as f:
                    f.seek(self.uasset.size + self.uasset.exports[0].size)
                    size = io_util.get_size(f) - self.uasset.size - self.uasset.exports[0].size - 4
                    ubulk = f.read(size)
                    foot = f.read(4)
                    io_util.check(foot, Utexture.UNREAL_SIGNATURE)
                f = io.BytesIO(ubulk)
            else:
                f = open(ubulk_name, 'rb')
                size = io_util.get_size(f)
            for mip in self.mipmaps:
                if mip.uexp:
                    continue
                mip.data = f.read(mip.data_size)
            io_util.check(size, f.tell())
            f.close()

        self.print(verbose)

    # read uexp
    def read_uexp(self, f):
        # read cooked size if exist
        self.bin1 = None
        self.imported_width = None
        self.imported_height = None
        if self.unversioned:
            skip_unversioned_headers(f)
            s = f.tell()
            f.seek(0)
            self.bin1 = f.read(s)
            chk = io_util.read_uint8_array(f, 8)
            chk = [i for i in chk if i == 0]
            f.seek(-8, 1)
            if len(chk) > 2:
                self.imported_width = io_util.read_uint32(f)
                self.imported_height = io_util.read_uint32(f)
        else:
            first_property_id = io_util.read_uint64(f)
            if first_property_id >= len(self.name_list):
                raise RuntimeError('list index out of range. ' + VERSION_ERR_MSG)
            first_property = self.name_list[first_property_id]
            f.seek(0)
            if first_property == 'ImportedSize':
                self.bin1 = f.read(49)
                self.imported_width = io_util.read_uint32(f)
                self.imported_height = io_util.read_uint32(f)

        # skip property part
        offset = f.tell()
        b = f.read(8)
        while (b != b'\x01\x00\x01\x00\x01\x00\x00\x00'):
            b = b''.join([b[1:], f.read(1)])
            if f.tell() > 1000:
                raise RuntimeError('Parse Failed. ' + VERSION_ERR_MSG)
        s = f.tell()-offset
        f.seek(offset)
        self.unk = f.read(s)

        # read meta data
        self.pixel_format_name_id = io_util.read_uint64(f)
        self.offset_to_end_offset = f.tell()
        self.end_offset = io_util.read_uint32(f)  # Offset to end of uexp?
        if self.version >= '4.20':
            io_util.read_null(f, msg='Not NULL! ' + VERSION_ERR_MSG)
        if self.version >= '5.0':
            io_util.read_null_array(f, 4)

        self.original_width = io_util.read_uint32(f)
        self.original_height = io_util.read_uint32(f)
        self.cube_flag = io_util.read_uint16(f)
        self.unk_int = io_util.read_uint16(f)
        if self.cube_flag == 1:
            if self.texture_type != '2D':
                raise RuntimeError('Unexpected error! Please report it to the developer.')
        elif self.cube_flag == 6:
            if self.texture_type != 'Cube':
                raise RuntimeError('Unexpected error! Please report it to the developer.')
        else:
            raise RuntimeError('Not a cube flag! ' + VERSION_ERR_MSG)
        self.pixel_format = io_util.read_str(f)
        self.update_format()
        if self.version == 'ff7r' and self.unk_int == Utexture.UBULK_FLAG[1]:
            io_util.read_null(f)
            io_util.read_null(f)
            ubulk_map_num = io_util.read_uint32(f)  # bulk map num + unk_map_num
        self.unk_map_num = io_util.read_uint32(f)  # number of some mipmaps in uexp
        map_num = io_util.read_uint32(f)  # map num ?

        if self.version == 'ff7r':
            # ff7r have all mipmap data in a mipmap object
            self.uexp_mip_bulk = Umipmap.read(f, self.version)
            io_util.read_const_uint32(f, self.cube_flag)
            f.seek(4, 1)  # uexp mip map num

        # read mipmaps
        self.mipmaps = [Umipmap.read(f, self.version) for i in range(map_num)]

        _, ubulk_map_num = self.get_mipmap_num()
        self.has_ubulk = ubulk_map_num > 0

        if self.version == 'ff7r':
            # split mipmap data
            i = 0
            for mip in self.mipmaps:
                if mip.uexp:
                    size = int(mip.pixel_num * self.byte_per_pixel * self.cube_flag)
                    mip.data = self.uexp_mip_bulk.data[i:i+size]
                    i += size
            io_util.check(i, len(self.uexp_mip_bulk.data))

        if self.version >= '4.23':
            io_util.read_null(f, msg='Not NULL! ' + VERSION_ERR_MSG)
        # io_util.check(self.end_offset, f.tell()+self.uasset_size)
        self.none_name_id = io_util.read_uint64(f)

    # get max size of uexp mips
    def get_max_uexp_size(self):
        for mip in self.mipmaps:
            if mip.uexp:
                break
        return mip.width, mip.height

    # get max size of mips
    def get_max_size(self):
        return self.mipmaps[0].width, self.mipmaps[0].height

    # get number of mipmaps
    def get_mipmap_num(self):
        uexp_map_num = 0
        ubulk_map_num = 0
        for mip in self.mipmaps:
            uexp_map_num += mip.uexp
            ubulk_map_num += not mip.uexp
        return uexp_map_num, ubulk_map_num

    # save as uasset
    def save(self, file, valid=False):
        folder = os.path.dirname(file)
        if folder not in ['.', ''] and not os.path.exists(folder):
            io_util.mkdir(folder)

        uasset_name, uexp_name, ubulk_name = get_all_file_path(file)
        if self.nouexp:
            uexp_name = None
        if not self.has_ubulk or self.nouexp:
            ubulk_name = None

        # write .uexp
        if self.nouexp:
            f = io.BytesIO(b'')
        else:
            f = open(uexp_name, 'wb')

        self.write_uexp(f, valid=valid)

        if not self.nouexp:
            f.write(Utexture.UNREAL_SIGNATURE)
            size = f.tell()
        else:
            f.seek(0)
            uexp = f.read()
            size = f.tell() + 4
        f.close()

        # write .ubulk if exist
        if self.has_ubulk:
            if self.nouexp:
                f = io.BytesIO(b'')
            else:
                f = open(ubulk_name, 'wb')
            for mip in self.mipmaps:
                if not mip.uexp:
                    f.write(mip.data)
            if self.nouexp:
                f.seek(0)
                ubulk = f.read()

        # write .uasset
        # if self.version=='4.13':
        #     size += len(ubulk) + 4
        self.uasset.exports[0].update(size - 4, size - 4)

        self.uasset.save(uasset_name, size)
        if self.nouexp:
            with open(uasset_name, 'ab') as f:
                f.write(uexp)
                if self.has_ubulk:
                    f.write(ubulk)
                f.write(Utexture.UNREAL_SIGNATURE)

        return uasset_name, uexp_name, ubulk_name

    def write_uexp(self, f, valid=False):
        # get mipmap info
        max_width, max_height = self.get_max_uexp_size()
        uexp_map_num, ubulk_map_num = self.get_mipmap_num()
        uexp_map_data_size = 0
        for mip in self.mipmaps:
            if mip.uexp:
                uexp_map_data_size += len(mip.data) + 32 * (self.version != 'ff7r')

        # write cooked size if exist
        if self.bin1 is not None:
            f.write(self.bin1)

        if self.imported_height is not None:
            if not valid:
                self.imported_height = max(self.original_height, max_height)
                self.imported_width = max(self.original_width, max_width)
            io_util.write_uint32(f, self.imported_width)
            io_util.write_uint32(f, self.imported_height)

        if not valid:
            self.original_height = max_height
            self.original_width = max_width

        f.write(self.unk)

        # write meta data
        io_util.write_uint64(f, self.pixel_format_name_id)
        io_util.write_uint32(f, 0)  # write dummy offset. (rewrite it later)
        if self.version >= '4.20':
            io_util.write_null(f)
        if self.version >= '5.0':
            io_util.write_null_array(f, 4)

        io_util.write_uint32(f, self.original_width)
        io_util.write_uint32(f, self.original_height)
        io_util.write_uint16(f, self.cube_flag)
        io_util.write_uint16(f, self.unk_int)

        io_util.write_str(f, self.pixel_format)

        if self.version == 'ff7r' and self.unk_int == Utexture.UBULK_FLAG[1]:
            io_util.write_null(f)
            io_util.write_null(f)
            io_util.write_uint32(f, ubulk_map_num+self.unk_map_num)

        io_util.write_uint32(f, self.unk_map_num)
        io_util.write_uint32(f, len(self.mipmaps))

        if self.version == 'ff7r':
            # pack mipmaps in a mipmap object
            uexp_bulk = b''
            for mip in self.mipmaps:
                mip.meta = True
                if mip.uexp:
                    uexp_bulk = b''.join([uexp_bulk, mip.data])
            size = self.get_max_uexp_size()
            self.uexp_mip_bulk = Umipmap(self.version)
            self.uexp_mip_bulk.update(uexp_bulk, size, True)
            self.uexp_mip_bulk.offset = self.uasset_size+f.tell() + 24
            self.uexp_mip_bulk.write(f, self.uasset_size)

            io_util.write_uint32(f, self.cube_flag)
            io_util.write_uint32(f, uexp_map_num)

        if self.version <= '4.15' or self.version >= '4.26' or self.version == 'ff7r':
            offset = 0
        else:
            new_end_offset = \
                self.uasset_size + \
                f.tell() + \
                uexp_map_data_size + \
                ubulk_map_num*32 + \
                (len(self.mipmaps)) * (self.version >= '4.20' and self.version <= '4.25') * 4 + \
                (self.version >= '4.23' and self.version <= '4.25') * 4 - \
                (len(self.mipmaps)) * (self.version == 'borderlands3') * 6
            offset = -new_end_offset - 8
        # write mipmaps
        for mip in self.mipmaps:
            if mip.uexp:
                mip.offset = self.uasset_size+f.tell() + 24 - 4 * (self.version >= '5.0')
            else:
                mip.offset = offset
                offset += mip.data_size
            mip.write(f, self.uasset_size)

        if self.version >= '4.23':
            io_util.write_null(f)

        if self.version >= '5.0':
            new_end_offset = f.tell() - self.offset_to_end_offset
        else:
            new_end_offset = f.tell() + self.uasset_size
        io_util.write_uint64(f, self.none_name_id)

        f.seek(self.offset_to_end_offset)
        io_util.write_uint32(f, new_end_offset)
        f.seek(0, 2)

    # remove mipmaps except the largest one
    def remove_mipmaps(self):
        old_mipmap_num = len(self.mipmaps)
        if old_mipmap_num == 1:
            return
        self.mipmaps = [self.mipmaps[0]]
        self.mipmaps[0].uexp = True
        self.has_ubulk = False
        print('mipmaps have been removed.')
        print(f'  mipmap: {old_mipmap_num} -> 1')

    # inject dds into asset
    def inject_dds(self, dds):
        # check formats
        if dds.header.dxgi_format != self.dxgi_format:
            raise RuntimeError(
                "The format does not match. "
                f"(Uasset: {self.dxgi_format.name[12:]}, DDS: {dds.header.dxgi_format.name[12:]})"
            )

        if dds.header.texture_type != self.texture_type:
            raise RuntimeError(
                "Texture type does not match. "
                f"(Uasset: {self.texture_type}, DDS: {dds.header.texture_type})"
            )

        max_width, max_height = self.get_max_size()
        old_size = (max_width, max_height)
        old_mipmap_num = len(self.mipmaps)

        uexp_width, uexp_height = self.get_max_uexp_size()

        # inject
        i = 0
        self.mipmaps = [Umipmap(self.version) for i in range(len(dds.mipmap_data))]
        for data, size, mip in zip(dds.mipmap_data, dds.mipmap_size, self.mipmaps):
            if self.has_ubulk and i + 1 < len(dds.mipmap_data) and size[0] * size[1] > uexp_width * uexp_height:
                mip.update(data, size, False)
            else:
                mip.update(data, size, True)
            i += 1

        # print results
        max_width, max_height = self.get_max_size()
        new_size = (max_width, max_height)
        _, ubulk_map_num = self.get_mipmap_num()
        if ubulk_map_num == 0:
            self.has_ubulk = False
        if self.version == "ff7r":
            self.unk_int = Utexture.UBULK_FLAG[self.has_ubulk]
        new_mipmap_num = len(self.mipmaps)

        print('dds has been injected.')
        print(f'  size: {old_size} -> {new_size}')
        print(f'  mipmap: {old_mipmap_num} -> {new_mipmap_num}')

        # warnings
        if new_mipmap_num > 1 and (not is_power_of_2(max_width) or not is_power_of_2(max_height)):
            print(f'Warning: Mipmaps should have power of 2 as its width and height. ({max_width}, {max_height})')
        if new_mipmap_num > 1 and old_mipmap_num == 1:
            print('Warning: The original texture has only 1 mipmap. But your dds has multiple mipmaps.')

    def print(self, verbose=False):
        if verbose:
            i = 0
            for mip in self.mipmaps:
                print(f'  Mipmap {i}')
                mip.print(padding=4)
                i += 1
        max_width, max_height = self.get_max_size()
        print(f'  max width: {max_width}')
        print(f'  max height: {max_height}')
        print(f'  format: {self.pixel_format} ({self.dxgi_format.name[12:]})')
        print(f'  texture type: {self.texture_type}')
        print(f'  mipmap: {len(self.mipmaps)}')

    def to_uncompressed(self):
        if self.pixel_format in PF_TO_UNCOMPRESSED:
            self.change_format(PF_TO_UNCOMPRESSED[self.pixel_format])

    def change_format(self, pixel_format):
        """Change pixel format."""
        if self.pixel_format != pixel_format:
            print(f'Changed pixel format from {self.pixel_format} to {pixel_format}')
        self.pixel_format = pixel_format
        self.update_format()
        self.uasset.update_name_list(self.pixel_format_name_id, pixel_format)

    def update_format(self):
        if self.pixel_format not in PF_TO_DXGI:
            raise RuntimeError(f'Unsupported pixel format. ({self.pixel_format})')
        self.dxgi_format = PF_TO_DXGI[self.pixel_format]
        self.byte_per_pixel = DXGI_BYTE_PER_PIXEL[self.dxgi_format]


def get_pf_from_uexp(uexp_file):
    with open(uexp_file, 'rb') as f:
        size = io_util.get_size(f)
        pixel_format = None
        while(f.tell() + 1 < size):
            if f.read(1) == b'P':
                pixel_format = b'P'
                while(f.tell() + 1 < size):
                    c = f.read(1)
                    if c == b'\x00':
                        break
                    pixel_format = b''.join([pixel_format, c])
                if pixel_format[:3] == b'PF_':
                    break
                else:
                    pixel_format = None
    if pixel_format is None:
        raise RuntimeError(
            "Can NOT detect pixel format.\n"
            "This asset might not be a texture."
        )
    return pixel_format.decode()
