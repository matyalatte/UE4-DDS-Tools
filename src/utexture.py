'''Classes for texture assets (.uexp and .ubulk)'''
import io
import os
import io_util
from uasset import Uasset
from umipmap import Umipmap


BYTE_PER_PIXEL = {
    'DXT1/BC1': 0.5,
    'DXT5/BC3': 1,
    'BC4/ATI1': 0.5,
    'BC4(signed)': 0.5,
    'BC5/ATI2': 1,
    'BC5(signed)': 1,
    'BC6H(unsigned)': 1,
    'BC6H(signed)': 1,
    'BC7': 1,
    'FloatRGBA': 8,
    'B8G8R8A8': 4,
    'ASTC_4X4': 8
}


PF_FORMAT = {
    'PF_DXT1': 'DXT1/BC1',
    'PF_DXT5': 'DXT5/BC3',
    'PF_BC4': 'BC4/ATI1',
    'PF_BC5': 'BC5/ATI2',
    'PF_BC6H': 'BC6H(unsigned)',
    'PF_BC7': 'BC7',
    'PF_FloatRGBA': 'FloatRGBA',
    'PF_B8G8R8A8': 'B8G8R8A8',
    'PF_ASTC_4x4': 'ASTC_4X4'
}


def is_power_of_2(n):
    if n == 1:
        return True
    if n % 2 != 0:
        return False
    return is_power_of_2(n // 2)


EXT = ['.uasset', '.uexp', '.ubulk']


# get all file paths for texture asset from a file path.
def get_all_file_path(file):
    base_name, ext = os.path.splitext(file)
    if ext not in EXT:
        raise RuntimeError('Not Uasset. ({})'.format(file))
    return [base_name + ext for ext in EXT]


VERSION_ERR_MSG = 'Make sure you specified UE4 version correctly.'


class Utexture:
    UNREAL_SIGNATURE = b'\xC1\x83\x2A\x9E'
    UBULK_FLAG = [0, 16384]

    def __init__(self, file_path, version='ff7r', verbose=False):
        if version == '4.26':
            version = '4.27'
        if version in ['4.23', '4.24']:
            version = '4.25'
        if version in ['4.20', '4.21']:
            version = '4.22'
        self.bl3 = version == 'borderlands3'
        if self.bl3:
            version = '4.22'
        self.version = version

        if not os.path.isfile(file_path):
            raise RuntimeError('Not File. ({})'.format(file_path))

        uasset_name, uexp_name, ubulk_name = get_all_file_path(file_path)
        print('load: ' + uasset_name)

        # read .uasset
        self.uasset = Uasset(uasset_name, version)
        self.unversioned = self.uasset.header.unversioned
        self.nouexp = self.uasset.nouexp
        if self.version in ['4.14', '4.13', '4.15']:
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
            io_util.check(foot, Utexture.UNREAL_SIGNATURE)
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
            uh = io_util.read_uint8_array(f, 2)
            is_last = uh[1] % 2 == 0
            while (is_last):
                uh = io_util.read_uint8_array(f, 2)
                is_last = uh[1] % 2 == 0
                if f.tell() > 100:
                    raise RuntimeError('Parse Failed. ' + VERSION_ERR_MSG)
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
        self.type_name_id = io_util.read_uint64(f)
        self.offset_to_end_offset = f.tell()
        self.end_offset = io_util.read_uint32(f)  # Offset to end of uexp?
        if self.version in ['4.22', '4.25', '4.27', '5.0']:
            io_util.read_null(f, msg='Not NULL! ' + VERSION_ERR_MSG)
        if self.version == '5.0':
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
        self.type = io_util.read_str(f)
        if self.version == 'ff7r' and self.unk_int == Utexture.UBULK_FLAG[1]:
            io_util.read_null(f)
            io_util.read_null(f)
            ubulk_map_num = io_util.read_uint32(f)  # bulk map num + unk_map_num
        self.unk_map_num = io_util.read_uint32(f)  # number of some mipmaps in uexp
        map_num = io_util.read_uint32(f)  # map num ?

        if self.version == 'ff7r':
            # ff7r have all mipmap data in a mipmap object
            self.uexp_mip_bulk = Umipmap.read(f, 'ff7r')
            io_util.read_const_uint32(f, self.cube_flag)
            f.seek(4, 1)  # uexp mip map num

        # read mipmaps
        self.mipmaps = [Umipmap.read(f, self.version, self.bl3) for i in range(map_num)]
        _, ubulk_map_num = self.get_mipmap_num()
        self.has_ubulk = ubulk_map_num > 0

        # get format name
        if self.type not in PF_FORMAT:
            raise RuntimeError(f'Unsupported pixel format. ({self.type})')
        self.format_name = PF_FORMAT[self.type]
        self.byte_per_pixel = BYTE_PER_PIXEL[self.format_name]

        if self.version == 'ff7r':
            # split mipmap data
            i = 0
            for mip in self.mipmaps:
                if mip.uexp:
                    size = int(mip.pixel_num * self.byte_per_pixel * self.cube_flag)
                    mip.data = self.uexp_mip_bulk.data[i:i+size]
                    i += size
            io_util.check(i, len(self.uexp_mip_bulk.data))

        if self.version in ['4.25', '4.27', '5.0']:
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
        io_util.write_uint64(f, self.type_name_id)
        io_util.write_uint32(f, 0)  # write dummy offset. (rewrite it later)
        if self.version in ['4.22', '4.25', '4.27', '5.0']:
            io_util.write_null(f)
        if self.version == '5.0':
            io_util.write_null_array(f, 4)

        io_util.write_uint32(f, self.original_width)
        io_util.write_uint32(f, self.original_height)
        io_util.write_uint16(f, self.cube_flag)
        io_util.write_uint16(f, self.unk_int)

        io_util.write_str(f, self.type)

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
            self.uexp_mip_bulk = Umipmap('ff7r')
            self.uexp_mip_bulk.update(uexp_bulk, size, True)
            self.uexp_mip_bulk.offset = self.uasset_size+f.tell() + 24
            self.uexp_mip_bulk.write(f, self.uasset_size)

            io_util.write_uint32(f, self.cube_flag)
            io_util.write_uint32(f, uexp_map_num)

        if self.version in ['5.0', '4.27', '4.15', '4.14', '4.13', 'ff7r']:
            offset = 0
        else:
            new_end_offset = \
                self.uasset_size + \
                f.tell() + \
                uexp_map_data_size + \
                ubulk_map_num*32 + \
                (len(self.mipmaps)) * (self.version in ['4.25', '4.22']) * 4 + \
                (self.version == '4.25') * 4 - \
                (len(self.mipmaps)) * (self.bl3) * 6
            offset = -new_end_offset - 8
        # write mipmaps
        for mip in self.mipmaps:
            if mip.uexp:
                mip.offset = self.uasset_size+f.tell() + 24 - 4 * (self.version == '5.0')
            else:
                mip.offset = offset
                offset += mip.data_size
            mip.write(f, self.uasset_size)

        if self.version in ['4.25', '4.27', '5.0']:
            io_util.write_null(f)

        if self.version == '5.0':
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
    def inject_dds(self, dds, force=False):
        # check formats
        if '(signed)' in dds.header.format_name:
            raise RuntimeError(f'UE4 requires unsigned format but your dds is {dds.header.format_name}.')

        if dds.header.format_name != self.format_name and not force:
            raise RuntimeError(f'The format does not match. ({self.type}, {dds.header.format_name})')

        if dds.header.texture_type != self.texture_type:
            raise RuntimeError(f'Texture type does not match. ({self.texture_type}, {dds.header.texture_type})')

        '''
        def get_key_from_value(d, val):
            keys = [k for k, v in d.items() if v == val]
            if keys:
                return keys[0]
            return None

        if force:
            self.format_name = dds.header.format_name
            new_type = get_key_from_value(self.format_name)
            self.uasset_size+=len(new_type)-len(self.type)
            self.type = new_type
            self.name_list[self.type_name_id]=self.type
            self.byte_per_pixel = BYTE_PER_PIXEL[self.format_name]
        '''

        max_width, max_height = self.get_max_size()
        old_size = (max_width, max_height)
        old_mipmap_num = len(self.mipmaps)

        uexp_width, uexp_height = self.get_max_uexp_size()

        # inject
        i = 0
        self.mipmaps = [Umipmap(self.version, self.bl3) for i in range(len(dds.mipmap_data))]
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
        print(f'  format: {self.type}')
        print(f'  texture type: {self.texture_type}')
        print(f'  mipmap: {len(self.mipmaps)}')


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
