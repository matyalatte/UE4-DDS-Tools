""""""

from enum import IntEnum
from .archive import (ArchiveBase, Int64, Int32, Uint32,
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
    BULKDATA_Size64Bit = 1 << 13                # data size is written as int64
    BULKDATA_NoOffsetFixUp = 1 << 16            # no need to fix offset data
    # BULKDATA_UsesIoDispatcher = 1 << 16         for UE 4.25


class BulkType(IntEnum):
    UNKNOWN = 0
    UEXP = 1
    UBULK = 2
    UPTNL = 3
    NONE = 4

    @staticmethod
    def int_to_str(type_int: int) -> str:
        dic = {i.value: i.name for i in BulkType}
        if type_int in dic:
            return dic[type_int]
        else:
            return None


class DataResourceBase:
    def __init__(self):
        self.bulk_flags = 0
        self.bulk_type = BulkType.UNKNOWN
        self.has_wrong_offset = False
        self.has_64bit_size = False

    def unpack_bulk_flags(self, ar: ArchiveBase):
        if self.bulk_flags & BulkDataFlags.BULKDATA_ForceInlinePayload > 0:
            self.bulk_type = BulkType.UEXP
        elif self.bulk_flags & BulkDataFlags.BULKDATA_Unused > 0:
            self.bulk_type = BulkType.NONE
        elif self.bulk_flags & BulkDataFlags.BULKDATA_OptionalPayload > 0:
            self.bulk_type = BulkType.UPTNL
        else:
            self.bulk_type = BulkType.UBULK
        if (ar.version == "ff7r") or (ar.version >= "4.26"):
            self.has_wrong_offset = self.bulk_flags & BulkDataFlags.BULKDATA_NoOffsetFixUp == 0
        else:
            if (self.bulk_flags & BulkDataFlags.BULKDATA_NoOffsetFixUp > 0) and ar.version <= "4.23":
                raise RuntimeError(f"BULKDATA_UsesIODispatcher is not supported for this UE version. ({ar.version})")
            self.has_wrong_offset = True
        self.has_64bit_size = self.bulk_flags & BulkDataFlags.BULKDATA_Size64Bit > 0

    def update_bulk_flags(self, ar: ArchiveBase):
        # update bulk flags
        match self.bulk_type:
            case BulkType.UEXP:
                self.bulk_flags = BulkDataFlags.BULKDATA_ForceInlinePayload
                if ar.version != "ff7r":
                    self.bulk_flags |= BulkDataFlags.BULKDATA_SingleUse
            case BulkType.NONE:
                self.bulk_flags = BulkDataFlags.BULKDATA_Unused
            case _:  # ubulk or uptnl
                self.bulk_flags = BulkDataFlags.BULKDATA_PayloadAtEndOfFile
                if ar.version >= "4.14":
                    self.bulk_flags |= BulkDataFlags.BULKDATA_Force_NOT_InlinePayload
                if ar.version >= "4.16":
                    self.bulk_flags |= BulkDataFlags.BULKDATA_PayloadInSeperateFile
                if (ar.version == "ff7r") or (ar.version >= "4.26"):
                    self.bulk_flags |= BulkDataFlags.BULKDATA_NoOffsetFixUp
                else:
                    self.has_wrong_offset = True
                if self.has_uptnl_bulk():
                    self.bulk_flags |= BulkDataFlags.BULKDATA_OptionalPayload

        if self.has_64bit_size:
            self.bulk_flags |= BulkDataFlags.BULKDATA_Size64Bit

    def get_type_str(self) -> str:
        return BulkType.int_to_str(self.bulk_type)

    def has_uexp_bulk(self):
        return self.bulk_type == BulkType.UEXP

    def has_no_bulk(self):
        return self.bulk_type == BulkType.NONE

    def has_ubulk_bulk(self):
        return self.bulk_type == BulkType.UBULK

    def has_uptnl_bulk(self):
        return self.bulk_type == BulkType.UPTNL

    def update(self, data_size: int, has_uexp_bulk: bool):
        self.data_size = data_size
        self.offset = 0
        if has_uexp_bulk:
            self.bulk_type = BulkType.UEXP
        else:
            self.bulk_type = BulkType.UBULK

    def rewrite_offset(self, ar: ArchiveBase, new_offset: int):
        pass


class LegacyDataResource(SerializableBase, DataResourceBase):
    """Meta data for FBulkData.

    Notes:
        Old UE versions will write the meta data in .uexp.
    """
    def serialize(self, ar: ArchiveBase):
        if ar.is_writing:
            if not ar.valid:
                self.update_bulk_flags(ar)
            if self.has_uexp_bulk() or self.has_no_bulk():
                self.offset = ar.args[0]

        ar << (Uint32, self, "bulk_flags")
        if ar.is_reading:
            self.unpack_bulk_flags(ar)

        if self.has_64bit_size:
            int_type = Int64
        else:
            int_type = Int32
        ar << (int_type, self, "data_size")  # ElementCount
        ar == (int_type, self.data_size, "data_size2")  # SizeOnDisk

        if ar.is_writing:
            if self.has_uexp_bulk() or self.has_no_bulk():
                self.offset += ar.tell() + 8

        self.offset_to_offset = ar.tell()
        ar << (Int64, self, "offset")

    def update(self, data_size: int, has_uexp_bulk: bool):
        super().update(data_size, has_uexp_bulk)
        self.has_64bit_size = data_size > (1 << 31)

    def rewrite_offset(self, ar: ArchiveBase, new_offset: int):
        self.offset = new_offset
        current = ar.tell()
        ar.seek(self.offset_to_offset)
        ar << (Int64, self, "offset")
        ar.seek(current)


class UassetDataResource(SerializableBase, DataResourceBase):
    """Meta data for FBulkData. (FObjectDataResource)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Private/UObject/ObjectResource.cpp
        The latest UE version will write the meta data in .uasset.
    """
    def __init__(self):
        super().__init__()
        self.flags = 0
        self.duplicated_offset = -1
        self.outer_index = 1

    def serialize(self, ar: ArchiveBase):
        if ar.is_writing:
            if not ar.valid:
                self.update_bulk_flags(ar)

        ar << (Uint32, self, "flags")
        ar << (Int64, self, "offset")
        ar << (Int64, self, "duplicated_offset")
        ar << (Int64, self, "data_size")
        ar == (Int64, self.data_size, "data_size2")
        ar << (Int32, self, "outer_index")
        ar << (Uint32, self, "bulk_flags")

        if ar.is_reading:
            self.unpack_bulk_flags(ar)

    def update(self, data_size: int, has_uexp_bulk: bool):
        super().update(data_size, has_uexp_bulk)
        self.has_64bit_size = True

    def print(self, padding=2):
        pad = " " * padding
        print(pad + "DataResource")
        print(pad + f"  flags: {self.flags}")
        print(pad + f"  serial offset: {self.offset}")
        print(pad + f"  duplicated serial offset: {self.duplicated_offset}")
        print(pad + f"  data size: {self.data_size}")
        print(pad + f"  outer index: {self.outer_index}")
        print(pad + f"  legacy bulk data flags: {self.bulk_flags}")


class BulkDataMapEntry(SerializableBase, DataResourceBase):
    """data resource for ucas assets. (FBulkDataMapEntry)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Public/Serialization/AsyncLoading2.h
        The latest UE version will write the meta data in .uasset.
    """
    def __init__(self):
        super().__init__()
        self.flags = 0
        self.duplicated_offset = -1

    def serialize(self, ar: ArchiveBase):
        if ar.is_writing:
            if not ar.valid:
                self.update_bulk_flags(ar)

        ar << (Int64, self, "offset")
        ar << (Int64, self, "duplicated_offset")
        ar << (Int64, self, "data_size")
        ar << (Uint32, self, "bulk_flags")
        ar == (Uint32, 0, "pad")

        if ar.is_reading:
            self.unpack_bulk_flags(ar)

    def update(self, data_size: int, has_uexp_bulk: bool):
        super().update(data_size, has_uexp_bulk)
        self.has_64bit_size = True

    def print(self, padding=2):
        pad = " " * padding
        print(pad + "DataResource")
        print(pad + f"  serial offset: {self.offset}")
        print(pad + f"  duplicated serial offset: {self.duplicated_offset}")
        print(pad + f"  data size: {self.data_size}")
        print(pad + f"  flags: {self.bulk_flags}")

    @staticmethod
    def get_struct_size(ar: ArchiveBase) -> int:
        return 32
