'''Classes for texture assets (.uexp and .ubulk)'''
import io_util
from .umipmap import Umipmap
from .version import VersionInfo
from directx.dds import DDSHeader, DDS
from directx.dxgi_format import DXGI_FORMAT, DXGI_BYTE_PER_PIXEL
from .archive import (ArchiveBase, Bytes, Uint64, Uint32, String, StructArray)

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


class Utexture:
    """
    A texture (FTexturePlatformData)

    Notes:
        UnrealEngine/Engine/Source/Runtime/Engine/Classes/Engine/Texture.h
        UnrealEngine/Engine/Source/Runtime/Engine/Private/TextureDerivedData.cpp
    """

    verison: VersionInfo
    name_list: list[str]
    is_light_map: bool
    dxgi_format: DXGI_FORMAT

    def __init__(self, uasset, class_name="Texture2D"):
        self.uasset = uasset
        self.version = uasset.version
        self.name_list = uasset.name_list
        self.is_light_map = "LightMap" in class_name
        self.is_cube = "Cube" in class_name
        self.is_3D = "Volume" in class_name
        self.is_array = "Array" in class_name
        self.has_opt_data = False

    def serialize(self, uexp_io: ArchiveBase):
        # read .uexp
        if uexp_io.is_writing and self.has_ubulk:
            ubulk_io = self.uasset.get_ubulk_io(rb=uexp_io.is_reading)
            ubulk_start_offset = ubulk_io.tell()
        else:
            ubulk_start_offset = 0
        self.__serialize_uexp(uexp_io, ubulk_start_offset)

        # read .ubulk if exists
        if self.has_ubulk:
            ubulk_io = self.uasset.get_ubulk_io(rb=uexp_io.is_reading)
            for mip in self.mipmaps:
                mip.serialize_ubulk(ubulk_io)

        if uexp_io.is_reading:
            self.print(uexp_io.verbose)
            if (self.is_3D or self.is_array) and len(self.mipmaps) > 1:
                raise RuntimeError(f"Loaded {self.get_texture_type()} texture has mipmaps. This is unexpected.")

    def __calculate_prop_size(self, ar: ArchiveBase):
        # Each UObject has some properties (Imported size, GUID, etc.) before the strip flags.
        # We will skip them cause we don't need to edit them.
        start_offset = ar.tell()
        err_offset = min(ar.size - 7, start_offset + 1000)
        while (True):
            """ Serach and skip to \x01\x00\x01\x00\x01\x00\x00\x00.
            \x01\x00 is StripFlags for UTexture
            \x01\x00 is StripFlags for UTexture2D (or Cube)
            \x01\x00\x00\x00 is bCooked for UTexture2D (or Cube)

            Just searching x01 is not the best algorithm but fast enough.
            Because "found 01" means "found strip flags" for most texture assets.
            """
            b = ar.read(1)
            while (b != b'\x01'):
                b = ar.read(1)
                if (ar.tell() >= err_offset):
                    raise RuntimeError('Parse Failed. Make sure you specified UE4 version correctly.')

            if ar.read(7) == b'\x00\x01\x00\x01\x00\x00\x00':
                # Found \x01\x00\x01\x00\x01\x00\x00\x00
                break
            else:
                ar.seek(-7, 1)
        size = ar.tell() - start_offset
        ar.seek(start_offset)
        return size

    def __serialize_uexp(self, ar: ArchiveBase, ubulk_start_offset: int = 0):
        start_offset = ar.tell()
        uasset_size = self.uasset.get_size()
        if ar.is_reading:
            prop_size = self.__calculate_prop_size(ar)
        else:
            prop_size = 0
        ar << (Bytes, self, "props", prop_size)

        # UTexture::SerializeCookedPlatformData
        ar << (Uint64, self, "pixel_format_name_id")
        self.skip_offset_location = ar.tell()  # offset to self.skip_offset
        ar << (Uint32, self, "skip_offset")  # Offset to the end of this object
        if ar.version >= '4.20':
            ar == (Uint32, 0, "?")
        if ar.version >= '5.0':
            ar << (Bytes, self, "placeholder", 16)

        # FTexturePlatformData::SerializeCooked (SerializePlatformData)
        if ar.is_writing:
            # get mipmap info
            max_width, max_height = self.get_max_uexp_size()
            self.uexp_map_num, ubulk_map_num = self.get_mipmap_num()
            self.mip_count = len(self.mipmaps)
            if not ar.valid:
                self.original_height = max_height
                self.original_width = max_width

        ar << (Uint32, self, "original_width")
        ar << (Uint32, self, "original_height")
        if ar.is_writing:
            self.__update_packed_data()
        ar << (Uint32, self, "packed_data")
        ar << (String, self, "pixel_format")
        if ar.is_reading:
            self.__unpack_packed_data()
            self.__update_format()

        if self.version == 'ff7r' and self.has_opt_data:
            ar == (Uint32, 0, "?")
            ar == (Uint32, 0, "?")
            if ar.is_writing:
                self.num_mips_in_tail = ubulk_map_num + self.first_mip_to_serialize
            ar << (Uint32, self, "num_mips_in_tail")

        ar << (Uint32, self, "first_mip_to_serialize")
        ar << (Uint32, self, "mip_count")

        if self.version == 'ff7r':
            # ff7r have all mipmap data in a mipmap object
            if ar.is_writing:
                uexp_bulk = b''
                for mip in self.mipmaps:
                    if mip.is_uexp:
                        mip.is_meta = True
                        mip.data_size = 0
                        uexp_bulk = b''.join([uexp_bulk, mip.data])
                size = self.get_max_uexp_size()
                self.uexp_optional_mip.update(uexp_bulk, size, 1, True)
            ar << (Umipmap, self, "uexp_optional_mip", uasset_size)
            ar == (Uint32, self.num_slices, "num_slices")
            ar << (Uint32, self, "uexp_map_num")

        if ar.is_writing:
            ubulk_offset = ubulk_start_offset
            for mip in self.mipmaps:
                if not mip.is_uexp:
                    mip.offset = ubulk_offset
                ubulk_offset += mip.data_size

        # read mipmaps
        ar << (StructArray, self, "mipmaps", Umipmap, self.mip_count, uasset_size)

        if ar.is_reading:
            _, ubulk_map_num = self.get_mipmap_num()
            self.has_ubulk = ubulk_map_num > 0

        if ar.version >= '4.23':
            ar == (Uint32, 0, "bIsVirtual")

        if ar.is_writing:
            if ar.version >= '5.0':
                self.skip_offset = ar.tell() - self.skip_offset_location
            else:
                self.skip_offset = ar.tell() + uasset_size

        ar << (Uint64, self, "none_name_id")

        if self.is_light_map:
            ar << (Uint32, self, "light_map_flags")  # ELightMapFlags

        self.uexp_size = ar.tell() - start_offset

        if ar.is_reading:
            if self.version == 'ff7r' and self.has_supported_format():
                # split mipmap data
                i = 0
                for mip in self.mipmaps:
                    if mip.is_uexp:
                        size = int(mip.pixel_num * self.byte_per_pixel * self.num_slices)
                        mip.data = self.uexp_optional_mip.data[i: i + size]
                        i += size
                io_util.check(i, len(self.uexp_optional_mip.data))
        else:
            current = ar.tell()
            ar.seek(self.skip_offset_location)
            ar << (Uint32, self, "skip_offset")
            ar.seek(current)

    def get_max_uexp_size(self) -> tuple[int, int]:
        """Get max size of uexp mips."""
        for mip in self.mipmaps:
            if mip.is_uexp:
                break
        return mip.width, mip.height

    def get_max_size(self) -> tuple[int, int]:
        """Get max size of mips."""
        return self.mipmaps[0].width, self.mipmaps[0].height

    def get_mipmap_num(self) -> tuple[int, int]:
        uexp_map_num = 0
        ubulk_map_num = 0
        for mip in self.mipmaps:
            uexp_map_num += mip.is_uexp
            ubulk_map_num += not mip.is_uexp
        return uexp_map_num, ubulk_map_num

    def rewrite_offset_data(self):
        if self.version <= '4.15' or self.version >= '4.26' or self.version == 'ff7r':
            return
        # ubulk mipmaps have wierd offset data. (Fixed at 4.26)
        f = self.uasset.get_uexp_io(rb=False)
        uasset_size = self.uasset.get_size()
        uexp_size = self.uasset.get_uexp_size()
        ubulk_offset_base = -uasset_size - uexp_size
        for mip in self.mipmaps:
            if not mip.is_uexp:
                mip.rewrite_offset(f, ubulk_offset_base + mip.offset)

    def remove_mipmaps(self):
        old_mipmap_num = len(self.mipmaps)
        if old_mipmap_num == 1:
            return
        self.mipmaps = [self.mipmaps[0]]
        self.mipmaps[0].is_uexp = True
        self.has_ubulk = False
        print('mipmaps have been removed.')
        print(f'  mipmap: {old_mipmap_num} -> 1')

    def get_dds(self) -> DDS:
        """Get texture as dds."""
        if not self.has_supported_format():
            raise RuntimeError(f'Unsupported pixel format. ({self.pixel_format})')

        # make dds header
        header = DDSHeader()

        mipmap_data = []
        mipmap_size = []

        # get mipmaps
        for mip in self.mipmaps:
            mipmap_data.append(mip.data)
            mipmap_size.append([mip.width, mip.height])

        # update header
        w, h = self.get_max_size()
        header.update(w, h, self.get_depth(), len(mipmap_data), self.dxgi_format, self.is_cube, self.get_array_size())

        return DDS(header, mipmap_data, mipmap_size)

    def inject_dds(self, dds: DDS):
        """Inject dds into asset."""
        if not self.has_supported_format():
            raise RuntimeError(f'Unsupported pixel format. ({self.pixel_format})')

        # check formats
        if dds.header.dxgi_format != self.dxgi_format:
            raise RuntimeError(
                "The format does not match. "
                f"(Uasset: {self.dxgi_format.name[12:]}, DDS: {dds.header.dxgi_format.name[12:]})"
            )

        if dds.get_texture_type() != self.get_texture_type():
            raise RuntimeError(
                "Texture type does not match. "
                f"(Uasset: {self.get_texture_type()}, DDS: {dds.get_texture_type()})"
            )

        if dds.get_array_size() != self.get_array_size():
            raise RuntimeError(
                "Array size does not match. "
                f"(Uasset: {self.get_array_size()}, DDS: {dds.get_array_size()})"
            )

        max_width, max_height = self.get_max_size()
        old_size = (max_width, max_height)
        old_mipmap_num = len(self.mipmaps)

        uexp_width, uexp_height = self.get_max_uexp_size()

        old_depth = self.get_depth()
        new_depth = dds.header.depth

        # inject
        self.first_mip_to_serialize = 0
        i = 0
        self.mipmaps = [Umipmap() for i in range(len(dds.mipmap_data))]
        for data, size, mip in zip(dds.mipmap_data, dds.mipmap_size, self.mipmaps):
            if self.has_ubulk and i + 1 < len(dds.mipmap_data) and size[0] * size[1] > uexp_width * uexp_height:
                mip.update(data, size, new_depth, False)
            else:
                mip.update(data, size, new_depth, True)
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

        print('DDS has been injected.')
        print(f'  size: {old_size} -> {new_size}')
        if self.is_3D:
            print(f'  depth: {old_depth} -> {new_depth}')
        else:
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
        depth = self.get_depth()
        print(f'  type: {self.get_texture_type()}')
        print(f'  format: {self.pixel_format} ({self.dxgi_format.name[12:]})')
        print(f'  width: {max_width}')
        print(f'  height: {max_height}')
        if self.is_3D:
            print(f'  depth: {depth}')
        elif self.is_array:
            print(f'  array_size: {self.get_array_size()}')
        else:
            print(f'  mipmaps: {len(self.mipmaps)}')

    def to_uncompressed(self):
        if self.pixel_format in PF_TO_UNCOMPRESSED:
            self.change_format(PF_TO_UNCOMPRESSED[self.pixel_format])

    def change_format(self, pixel_format: str):
        """Change pixel format."""
        if self.pixel_format != pixel_format:
            print(f'Changed pixel format from {self.pixel_format} to {pixel_format}')
        self.pixel_format = pixel_format
        self.__update_format()
        self.uasset.update_name_list(self.pixel_format_name_id, pixel_format)

    def has_supported_format(self):
        return self.pixel_format in PF_TO_DXGI

    def __update_format(self):
        if not self.has_supported_format():
            print(f'Warning: Unsupported pixel format. ({self.pixel_format})')
            self.dxgi_format = DXGI_FORMAT.DXGI_FORMAT_UNKNOWN
            self.byte_per_pixel = None
            return
        self.dxgi_format = PF_TO_DXGI[self.pixel_format]
        self.byte_per_pixel = DXGI_BYTE_PER_PIXEL[self.dxgi_format]

    def __unpack_packed_data(self):
        if self.version >= "4.24" or self.version == 'ff7r':
            # self.is_cube = packed_data & (1 << 31) > 0
            self.has_opt_data = self.packed_data & (1 << 30) > 0
        self.num_slices = self.packed_data & ((1 << 30) - 1)

    def __update_packed_data(self) -> int:
        self.packed_data = self.num_slices
        if self.version >= "4.24" or self.version == 'ff7r':
            self.packed_data |= self.is_cube * (1 << 31)
            self.packed_data |= self.has_opt_data * (1 << 30)

    def get_texture_type(self) -> str:
        if self.is_3D:
            return "3D"
        if self.is_cube:
            t = "Cube"
        else:
            t = "2D"
        if self.is_array:
            t += "Array"
        return t

    def get_array_size(self):
        if self.is_3D:
            return 1
        if self.is_cube:
            return self.num_slices // 6
        else:
            return self.num_slices

    def get_depth(self):
        if self.is_3D:
            return self.num_slices
        return 1
