'''Mipmap class for texture asset'''
from enum import IntEnum
import ctypes as c
import io_util


class BulkDataFlags(IntEnum):
    # UnrealEngine/Engine/Source/Runtime/CoreUObject/Public/Serialization/BulkData.h
    BULKDATA_PayloadAtEndOfFile = 1 << 0        # not inline (end of file or ubulk)
    BULKDATA_SingleUse = 1 << 3                 # only used once at runtime
    BULKDATA_Unused = 1 << 5                    # only meta data (no dds data)
    BULKDATA_ForceInlinePayload = 1 << 6        # inline (uexp)
    BULKDATA_PayloadInSeperateFile = 1 << 8     # ubulk
    BULKDATA_Force_NOT_InlinePayload = 1 << 10  # not inline
    BULKDATA_OptionalPayload = 1 << 11          # uptnl
    BULKDATA_NoOffsetFixUp = 1 << 16            # no need to fix offset data


class Umipmap(c.LittleEndianStructure):
    """
    A mipmap (FTexture2DMipMap)

    Notes:
        UnrealEngine/Engine/Source/Runtime/Engine/Public/TextureResource.h
        UnrealEngine/Engine/Source/Runtime/Engine/Private/Texture2D.cpp
    """
    _pack_ = 1
    _fields_ = [
        # if version <= 4.27:
        #    cooked, c.c_uint32 (always 1)
        ("ubulk_flag", c.c_uint32),  # BulkDataFlags
        ("data_size", c.c_uint32),  # 0->ff7r uexp
        ("data_size2", c.c_uint32),  # data size again
        ("offset", c.c_int64)
        # data, c_ubyte*
        # width, c_uint32
        # height, c_uint32
        # if version >= 4.20:
        #    depth, c_uint32 (==1 for 2d and cube. !=1 for 3d textures)
    ]

    def __init__(self, version):
        self.version = version

    def update(self, data, size, uexp):
        self.uexp = uexp
        self.meta = False
        self.data_size = len(data)
        self.data_size2 = len(data)
        self.data = data
        self.offset = 0
        self.width = size[0]
        self.height = size[1]
        self.pixel_num = self.width * self.height

        # update bulk flags
        if self.uexp:
            if self.meta:
                self.ubulk_flag = BulkDataFlags.BULKDATA_Unused
            else:
                self.ubulk_flag = BulkDataFlags.BULKDATA_ForceInlinePayload
                if self.version != 'ff7r':
                    self.ubulk_flag |= BulkDataFlags.BULKDATA_SingleUse
        else:
            self.ubulk_flags = BulkDataFlags.BULKDATA_PayloadAtEndOfFile
            if self.version >= '4.14':
                self.ubulk_flag |= BulkDataFlags.BULKDATA_Force_NOT_InlinePayload
            if self.version >= '4.16':
                self.ubulk_flag |= BulkDataFlags.BULKDATA_PayloadInSeperateFile
            if (self.version == 'ff7r') or (self.version >= '4.26'):
                self.ubulk_flag |= BulkDataFlags.BULKDATA_NoOffsetFixUp

    @staticmethod
    def read(f, version):
        mip = Umipmap(version)
        if version <= '4.27':
            io_util.read_const_uint32(f, 1)
        f.readinto(mip)
        mip.uexp = (mip.ubulk_flag & BulkDataFlags.BULKDATA_ForceInlinePayload > 0) or \
                   (mip.ubulk_flag & BulkDataFlags.BULKDATA_Unused > 0)
        mip.meta = mip.ubulk_flag & BulkDataFlags.BULKDATA_Unused > 0
        mip.upntl = mip.ubulk_flag & BulkDataFlags.BULKDATA_OptionalPayload > 0
        if mip.upntl:
            raise RuntimeError("Optional payload (.upntl) is unsupported.")
        if mip.uexp:
            mip.data = f.read(mip.data_size)

        if version == 'borderlands3':
            read_int = io_util.read_uint16
        else:
            read_int = io_util.read_uint32

        mip.width = read_int(f)
        mip.height = read_int(f)
        if version >= '4.20':
            depth = read_int(f)
            io_util.check(depth, 1, msg='3d texture is unsupported.')

        io_util.check(mip.data_size, mip.data_size2)
        mip.pixel_num = mip.width * mip.height
        return mip

    def print(self, padding=2):
        pad = ' ' * padding
        print(pad + 'file: ' + 'uexp' * self.uexp + 'ubluk' * (not self.uexp))
        print(pad + f'data size: {self.data_size}')
        print(pad + f'offset: {self.offset}')
        print(pad + f'width: {self.width}')
        print(pad + f'height: {self.height}')

    def write(self, f, uasset_size):
        if self.version <= '4.27':
            io_util.write_uint32(f, 1)

        if self.uexp:
            self.offset = uasset_size + f.tell() + 20
            if self.meta:
                self.data_size = 0
                self.data_size2 = 0

        self.offset_to_offset = f.tell() + 12
        f.write(self)

        if self.uexp and not self.meta:
            f.write(self.data)

        if self.version == 'borderlands3':
            write_int = io_util.write_uint16
        else:
            write_int = io_util.write_uint32

        write_int(f, self.width)
        write_int(f, self.height)
        if self.version >= '4.20':
            write_int(f, 1)

    def rewrite_offset(self, f, new_offset):
        self.offset = new_offset
        current = f.tell()
        f.seek(self.offset_to_offset)
        io_util.write_int64(f, new_offset)
        f.seek(current)
