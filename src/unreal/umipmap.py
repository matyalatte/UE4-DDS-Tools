"""Mipmap class for texture asset"""
from enum import IntEnum
from .archive import (ArchiveBase, Int64, Uint32, Uint16, Buffer,
                      SerializableBase)


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


class Umipmap(SerializableBase):
    """
    A mipmap (FTexture2DMipMap)

    Notes:
        UnrealEngine/Engine/Source/Runtime/Engine/Public/TextureResource.h
        UnrealEngine/Engine/Source/Runtime/Engine/Private/Texture2D.cpp
    """

    def __init__(self):
        self.depth = 1
        self.is_uexp = False
        self.is_meta = False
        self.is_upntl = False
        self.ubulk_flags = 0

    def update(self, data: bytes, size: int, depth: int, is_uexp: bool):
        self.is_uexp = is_uexp
        self.is_meta = False
        self.data_size = len(data)
        self.data = data
        self.offset = 0
        self.width = size[0]
        self.height = size[1]
        self.depth = depth
        self.pixel_num = self.width * self.height * self.depth

    def serialize(self, ar: ArchiveBase):
        self.version = ar.version
        if ar.is_writing:
            if not ar.valid:
                self.__update_ubulk_flags()
            if self.is_uexp:
                self.offset = ar.args[0]
        if ar.version <= "4.27":
            ar == (Uint32, 1, "bCooked")

        ar << (Uint32, self, "ubulk_flags")
        if ar.is_reading:
            self.__unpack_ubulk_flags()

        ar << (Uint32, self, "data_size")
        ar == (Uint32, self.data_size, "data_size2")
        if ar.is_writing:
            if self.is_uexp:
                self.offset += ar.tell() + 8

        self.offset_to_offset = ar.tell()
        ar << (Int64, self, "offset")
        if self.is_uexp and not self.is_meta:
            ar << (Buffer, self, "data", self.data_size)

        if ar.version == "borderlands3":
            int_type = Uint16
        else:
            int_type = Uint32
        ar << (int_type, self, "width")
        ar << (int_type, self, "height")
        if ar.version >= "4.20":
            ar << (int_type, self, "depth")
        self.pixel_num = self.width * self.height * self.depth

    def serialize_ubulk(self, ar: ArchiveBase):
        if self.is_uexp:
            return
        ar << (Buffer, self, "data", self.data_size)

    def rewrite_offset(self, ar: ArchiveBase, new_offset: int):
        self.offset = new_offset
        current = ar.tell()
        ar.seek(self.offset_to_offset)
        ar << (Int64, self, "offset")
        ar.seek(current)

    def __unpack_ubulk_flags(self):
        self.is_uexp = (self.ubulk_flags & BulkDataFlags.BULKDATA_ForceInlinePayload > 0) or \
                       (self.ubulk_flags & BulkDataFlags.BULKDATA_Unused > 0)
        self.is_meta = self.ubulk_flags & BulkDataFlags.BULKDATA_Unused > 0
        self.is_upntl = self.ubulk_flags & BulkDataFlags.BULKDATA_OptionalPayload > 0
        if self.is_upntl:
            raise RuntimeError("Optional payload (.upntl) is unsupported.")

    def __update_ubulk_flags(self):
        # update bulk flags
        if self.is_uexp:
            if self.is_meta:
                self.ubulk_flags = BulkDataFlags.BULKDATA_Unused
            else:
                self.ubulk_flags = BulkDataFlags.BULKDATA_ForceInlinePayload
                if self.version != "ff7r":
                    self.ubulk_flags |= BulkDataFlags.BULKDATA_SingleUse
        else:
            self.ubulk_flags = BulkDataFlags.BULKDATA_PayloadAtEndOfFile
            if self.version >= "4.14":
                self.ubulk_flags |= BulkDataFlags.BULKDATA_Force_NOT_InlinePayload
            if self.version >= "4.16":
                self.ubulk_flags |= BulkDataFlags.BULKDATA_PayloadInSeperateFile
            if (self.version == "ff7r") or (self.version >= "4.26"):
                self.ubulk_flags |= BulkDataFlags.BULKDATA_NoOffsetFixUp

    def print(self, padding: int = 2):
        pad = " " * padding
        print(pad + "file: " + "uexp" * self.is_uexp + "ubluk" * (not self.is_uexp))
        print(pad + f"data size: {self.data_size}")
        print(pad + f"offset: {self.offset}")
        print(pad + f"width: {self.width}")
        print(pad + f"height: {self.height}")
        if self.version >= "4.20" and self.depth > 1:
            print(pad + f"depth: {self.depth}")
