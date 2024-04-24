"""Mipmap class for texture asset"""
from .data_resource import LegacyDataResource, UassetDataResource, BulkDataMapEntry
from .archive import (ArchiveBase, Int32, Uint32, Uint16, Buffer,
                      SerializableBase)


class Umipmap(SerializableBase):
    """
    A mipmap (FTexture2DMipMap)

    Notes:
        UnrealEngine/Engine/Source/Runtime/Engine/Public/TextureResource.h
        UnrealEngine/Engine/Source/Runtime/Engine/Private/Texture2D.cpp
    """

    def __init__(self):
        self.depth = 1
        self.data_resource = None

    def init_data_resource(self, uasset):
        if uasset.version >= "5.2":
            if uasset.is_ucas:
                self.data_resource = BulkDataMapEntry()
            else:
                self.data_resource = UassetDataResource()
        else:
            self.data_resource = LegacyDataResource()

    def update(self, data: bytes, size: tuple[int, int], depth: int, has_uexp_bulk: bool):
        self.data = data
        self.width = size[0]
        self.height = size[1]
        self.depth = depth
        self.pixel_num = self.width * self.height * self.depth
        self.data_resource.update(len(data), has_uexp_bulk)

    def serialize(self, ar: ArchiveBase):
        offset = ar.args[0]
        data_resources = ar.args[1]
        if ar.version <= "4.27":
            ar == (Uint32, 1, "bCooked")

        if ar.version <= "5.1":
            ar << (LegacyDataResource, self, "data_resource", offset)
        else:  # >= "5.2"
            # id for UassetDataResource
            if ar.is_writing:
                self.data_resource_id = len(data_resources)
                data_resources.append(self.data_resource)

            ar << (Int32, self, "data_resource_id")

            if ar.is_reading:
                self.data_resource = data_resources[self.data_resource_id]
            else:
                if self.has_uexp_bulk() or self.has_no_bulk():
                    self.data_resource.offset = ar.tell()

        if self.has_uexp_bulk():
            ar << (Buffer, self, "data", self.data_resource.data_size)

        if ar.version == "borderlands3":
            int_type = Uint16
        else:
            int_type = Uint32
        ar << (int_type, self, "width")
        ar << (int_type, self, "height")
        if ar.version >= "4.20":
            ar << (int_type, self, "depth")
        self.pixel_num = self.width * self.height * self.depth

    def serialize_ubulk(self, ubulk_ar: ArchiveBase, uptnl_ar: ArchiveBase):
        if self.has_uexp_bulk() or self.has_no_bulk():
            return
        if self.has_uptnl_bulk():
            uptnl_ar << (Buffer, self, "data", self.data_resource.data_size)
        else:
            ubulk_ar << (Buffer, self, "data", self.data_resource.data_size)

    def rewrite_offset(self, ar: ArchiveBase, new_offset: int):
        self.data_resource.rewrite_offset(ar, new_offset)

    def print(self, padding: int = 2):
        pad = " " * padding
        print(pad + f"bulk type: {self.data_resource.get_type_str()}")
        print(pad + f"data size: {self.get_data_size()}")
        print(pad + f"offset: {self.data_resource.offset}")
        print(pad + f"width: {self.width}")
        print(pad + f"height: {self.height}")
        if self.depth > 1:
            print(pad + f"depth: {self.depth}")

    def has_uexp_bulk(self):
        return self.data_resource.has_uexp_bulk()

    def has_no_bulk(self):
        return self.data_resource.has_no_bulk()

    def has_ubulk_bulk(self):
        return self.data_resource.has_ubulk_bulk()

    def has_uptnl_bulk(self):
        return self.data_resource.has_uptnl_bulk()

    def has_wrong_offset(self):
        return self.data_resource.has_wrong_offset

    def get_data_size(self):
        return self.data_resource.data_size
