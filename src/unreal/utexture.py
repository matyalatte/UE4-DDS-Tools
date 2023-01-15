'''Classes for texture assets (.uexp and .ubulk)'''
import io_util
from .umipmap import Umipmap
from directx.dxgi_format import DXGI_FORMAT, DXGI_BYTE_PER_PIXEL


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


VERSION_ERR_MSG = 'Make sure you specified UE4 version correctly.'


def skip_unversioned_headers(f):
    start_offset = f.tell()
    uhead = io_util.read_uint8_array(f, 2)
    is_last = uhead[1] % 2 == 0
    while is_last:
        uhead = io_util.read_uint8_array(f, 2)
        is_last = uhead[1] % 2 == 0
        if f.tell() - start_offset > 100:
            raise RuntimeError('Parse Failed. ' + VERSION_ERR_MSG)


class Utexture:
    """
    A texture (FTexturePlatformData)

    Notes:
        UnrealEngine/Engine/Source/Runtime/Engine/Classes/Engine/Texture.h
        UnrealEngine/Engine/Source/Runtime/Engine/Private/TextureDerivedData.cpp
    """
    UNREAL_SIGNATURE = b'\xC1\x83\x2A\x9E'

    def __init__(self, uasset, verbose=False, is_light_map=False):
        self.uasset = uasset
        self.version = uasset.version
        self.name_list = uasset.name_list
        self.is_light_map = is_light_map

        # read .uexp
        f = self.uasset.get_uexp_io(rb=True)
        self.read_uexp(f)

        # read .ubulk if exists
        if self.has_ubulk:
            f = self.uasset.get_ubulk_io(rb=True)
            for mip in self.mipmaps:
                if mip.uexp:
                    continue
                mip.data = f.read(mip.data_size)

        self.print(verbose)

    # read uexp
    def read_uexp(self, f):
        # read cooked size if exist
        self.bin1 = None
        self.imported_width = None
        self.imported_height = None
        start_offset = f.tell()

        if self.is_unversioned():
            skip_unversioned_headers(f)
            s = f.tell()
            f.seek(start_offset)
            self.bin1 = f.read(s - start_offset)
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
            f.seek(start_offset)
            if first_property == 'ImportedSize':
                self.bin1 = f.read(49)
                self.imported_width = io_util.read_uint32(f)
                self.imported_height = io_util.read_uint32(f)

        # skip property part
        offset = f.tell()
        b = f.read(8)
        while (b != b'\x01\x00\x01\x00\x01\x00\x00\x00'):
            """
            \x01\x00 is StripFlags for UTexture
            \x01\x00 is StripFlags for UTexture2D (or Cube)
            \x01\x00\x00\x00 is bCooked for UTexture2D (or Cube)
            """
            b = b''.join([b[1:], f.read(1)])
            if f.tell() - offset > 1000:
                raise RuntimeError('Parse Failed. ' + VERSION_ERR_MSG)
        s = f.tell() - offset
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
        self.read_packed_data(io_util.read_uint32(f))  # PlatformData->PackedData
        self.update_format(io_util.read_str(f))  # PixelFormatString

        if self.version == 'ff7r' and self.has_opt_data:
            io_util.read_null(f)
            io_util.read_null(f)
            f.seek(4, 1)  # NumMipsInTail ? (bulk map num + first_mip_to_serialize)

        self.first_mip_to_serialize = io_util.read_uint32(f)
        map_num = io_util.read_uint32(f)  # mip map count

        if self.version == 'ff7r':
            # ff7r have all mipmap data in a mipmap object
            self.uexp_optional_mip = Umipmap.read(f, self.version)
            io_util.read_const_uint32(f, self.num_slices)
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
                    size = int(mip.pixel_num * self.byte_per_pixel * self.num_slices)
                    mip.data = self.uexp_optional_mip.data[i: i + size]
                    i += size
            io_util.check(i, len(self.uexp_optional_mip.data))

        if self.version >= '4.23':
            # bIsVirtual
            io_util.read_null(f, msg='Virtual texture is unsupported.')
        self.none_name_id = io_util.read_uint64(f)

        if self.is_light_map:
            self.light_map_flags = io_util.read_uint32(f)  # ELightMapFlags

        self.uexp_size = f.tell() - start_offset

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
    def write(self, valid=False):
        # write .uexp
        f = self.uasset.get_uexp_io(rb=False)
        if self.has_ubulk:
            ubulk_io = self.uasset.get_ubulk_io(rb=False)
            ubulk_start_offset = ubulk_io.tell()
        else:
            ubulk_start_offset = 0
        self.write_uexp(f, ubulk_start_offset, valid=valid)

        # write .ubulk if exists
        if self.has_ubulk:
            for mip in self.mipmaps:
                if not mip.uexp:
                    ubulk_io.write(mip.data)

    def write_uexp(self, f, ubulk_start_offset, valid=False):
        uasset_size = self.uasset.get_size()
        start_offset = f.tell()

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
        self.offset_to_end_offset = f.tell()
        f.seek(4, 1)  # for self.end_offset. write here later
        if self.version >= '4.20':
            io_util.write_null(f)
        if self.version >= '5.0':
            io_util.write_null_array(f, 4)

        io_util.write_uint32(f, self.original_width)
        io_util.write_uint32(f, self.original_height)
        io_util.write_uint32(f, self.get_packed_data())

        io_util.write_str(f, self.pixel_format)

        if self.version == 'ff7r' and self.has_opt_data:
            io_util.write_null(f)
            io_util.write_null(f)
            io_util.write_uint32(f, ubulk_map_num + self.first_mip_to_serialize)

        io_util.write_uint32(f, self.first_mip_to_serialize)
        io_util.write_uint32(f, len(self.mipmaps))

        if self.version == 'ff7r':
            # pack mipmaps in a mipmap object
            uexp_bulk = b''
            for mip in self.mipmaps:
                mip.meta = True
                if mip.uexp:
                    uexp_bulk = b''.join([uexp_bulk, mip.data])
            size = self.get_max_uexp_size()
            self.uexp_optional_mip = Umipmap(self.version)
            self.uexp_optional_mip.update(uexp_bulk, size, True)
            self.uexp_optional_mip.write(f, uasset_size)

            io_util.write_uint32(f, self.num_slices)
            io_util.write_uint32(f, uexp_map_num)

        ubulk_offset = ubulk_start_offset

        # write mipmaps
        for mip in self.mipmaps:
            if not mip.uexp:
                mip.offset = ubulk_offset
                ubulk_offset += mip.data_size
            mip.write(f, uasset_size)

        if self.version >= '4.23':
            io_util.write_null(f)

        if self.version >= '5.0':
            new_end_offset = f.tell() - self.offset_to_end_offset
        else:
            new_end_offset = f.tell() + uasset_size
        io_util.write_uint64(f, self.none_name_id)

        if self.is_light_map:
            io_util.write_uint32(f, self.light_map_flags)

        if self.version >= '4.16' and self.version <= '4.25' and self.version != 'ff7r':
            # ubulk mipmaps have wierd offset data. (Fixed at 4.26)
            ubulk_offset_base = -uasset_size - f.tell()
            for mip in self.mipmaps:
                if not mip.uexp:
                    mip.rewrite_offset(f, ubulk_offset_base + mip.offset)

        current = f.tell()
        f.seek(self.offset_to_end_offset)
        io_util.write_uint32(f, new_end_offset)
        f.seek(current)
        self.uexp_size = current - start_offset

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

        if dds.is_cube() != self.is_cube:
            raise RuntimeError(
                "Texture type does not match. "
                f"(Uasset: {self.get_texture_type()}, DDS: {dds.get_texture_type()})"
            )

        max_width, max_height = self.get_max_size()
        old_size = (max_width, max_height)
        old_mipmap_num = len(self.mipmaps)

        uexp_width, uexp_height = self.get_max_uexp_size()

        # inject
        self.first_mip_to_serialize = 0
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
            self.has_opt_data = self.has_ubulk
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
        print(f'  width: {max_width}')
        print(f'  height: {max_height}')
        print(f'  format: {self.pixel_format} ({self.dxgi_format.name[12:]})')
        print(f'  mipmaps: {len(self.mipmaps)}')
        print(f'  cubemap: {self.is_cube}')

    def to_uncompressed(self):
        if self.pixel_format in PF_TO_UNCOMPRESSED:
            self.change_format(PF_TO_UNCOMPRESSED[self.pixel_format])

    def change_format(self, pixel_format):
        """Change pixel format."""
        if self.pixel_format != pixel_format:
            print(f'Changed pixel format from {self.pixel_format} to {pixel_format}')
        self.update_format(pixel_format)
        self.uasset.update_name_list(self.pixel_format_name_id, pixel_format)

    def update_format(self, pixel_format):
        self.pixel_format = pixel_format
        if self.pixel_format not in PF_TO_DXGI:
            raise RuntimeError(f'Unsupported pixel format. ({self.pixel_format})')
        self.dxgi_format = PF_TO_DXGI[self.pixel_format]
        self.byte_per_pixel = DXGI_BYTE_PER_PIXEL[self.dxgi_format]

    def read_packed_data(self, packed_data):
        self.is_cube = packed_data & (1 << 31) > 0
        self.has_opt_data = packed_data & (1 << 30) > 0
        self.num_slices = packed_data & ((1 << 30) - 1)

    def get_packed_data(self):
        packed_data = self.num_slices
        packed_data |= self.is_cube * (1 << 31)
        packed_data |= self.has_opt_data * (1 << 30)
        return packed_data

    def get_texture_type(self):
        return ['2D', 'Cube'][self.is_cube]

    def is_unversioned(self):
        return self.uasset.header.is_unversioned()

    def has_uexp(self):
        return self.uasset.has_uexp()


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
