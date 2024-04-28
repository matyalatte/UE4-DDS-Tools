from enum import IntEnum
from .crc import strcrc
from .city_hash import city_hash_64
from .version import VersionInfo
from .archive import (ArchiveBase,
                      Uint8, Uint32, Uint64, Int32, Bytes,
                      String, StringWithLen,
                      SerializableBase)


class ObjectFlags(IntEnum):
    RF_Public = 1
    RF_Standalone = 2  # Main object in the asset
    RF_Transactional = 8
    RF_ClassDefaultObject = 0x10  # Default object
    RF_ArchetypeObject = 0x20  # Template for another object


class NameBase(SerializableBase):
    def __init__(self):
        self.hash = None

    def serialize(self, ar: ArchiveBase):
        pass

    def __str__(self):
        return self.name

    def update(self, new_name, update_hash=False):
        pass


class ImportBase(SerializableBase):
    def serialize(self, ar: ArchiveBase):
        pass

    def name_import(self, imports: list, name_list: list[NameBase]) -> str:
        pass

    def print(self, padding=2):
        pass


class ExportBase(SerializableBase):
    TEXTURE_CLASSES = [
        "Texture2D", "TextureCube", "LightMapTexture2D", "ShadowMapTexture2D",
        "Texture2DArray", "TextureCubeArray", "VolumeTexture"
    ]

    def __init__(self):
        self.object = None  # The actual data will be stored here
        self.meta_size = 0  # binary size of meta data

    def serialize(self, ar: ArchiveBase):
        pass

    def name_export(self, exports: list, imports: list[ImportBase], name_list: list[NameBase]):
        pass

    def is_base(self):
        return (self.object_flags & ObjectFlags.RF_ArchetypeObject > 0
                or self.object_flags & ObjectFlags.RF_ClassDefaultObject > 0)

    def is_standalone(self):
        return self.object_flags & ObjectFlags.RF_Standalone > 0

    def is_public(self):
        return self.object_flags & ObjectFlags.RF_Public > 0

    def is_texture(self):
        return self.class_name in ExportBase.TEXTURE_CLASSES

    def update(self, size, offset):
        self.size = size
        self.offset = offset

    @staticmethod
    def get_meta_size(version: VersionInfo):
        pass


class UassetName(NameBase):
    def serialize(self, ar: ArchiveBase):
        ar << (String, self, "name")
        if ar.version <= "4.11":
            return
        ar << (Bytes, self, "hash", 4)

    def update(self, new_name, update_hash=False):
        self.name = new_name
        if update_hash:
            self.hash = strcrc(new_name)


class UassetImport(ImportBase):
    """Meta data for an object that is contained within another file. (FObjectImport)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Private/UObject/ObjectResource.cpp
    """

    def serialize(self, ar: ArchiveBase):
        ar << (Int32, self, "class_package_name_id")
        ar << (Int32, self, "class_package_name_number")
        ar << (Int32, self, "class_name_id")
        ar << (Int32, self, "class_name_number")
        ar << (Int32, self, "class_package_import_id")
        ar << (Int32, self, "name_id")
        ar << (Int32, self, "name_number")
        if ar.version >= "5.0":
            ar << (Uint32, self, "optional")

    def name_import(self, imports: list[ImportBase], name_list: list[NameBase]) -> str:
        self.name = str(name_list[self.name_id])
        self.class_name = str(name_list[self.class_name_id])
        if self.class_package_import_id == 0:
            self.package_name = "None"
        else:
            self.package_name = name_list[imports[-self.class_package_import_id - 1].name_id]
        return self.name

    def print(self, padding=2):
        pad = " " * padding
        print(f"{pad}{self.name}")
        print(f"{pad}  class: {self.class_name}")
        print(f"{pad}  package_name: {self.package_name}")


class UassetExport(ExportBase):
    """Meta data for an object that is contained within this file. (FObjectExport)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Private/UObject/ObjectResource.cpp
    """

    def serialize(self, ar: ArchiveBase):
        ar << (Int32, self, "class_index")  # -: import id, +: export id
        ar << (Int32, self, "super_index")
        if ar.version >= "4.14":
            ar << (Int32, self, "template_index")
        else:
            self.template_index = 0
        ar << (Int32, self, "outer_index")  # 0: main object, 1: not main
        ar << (Int32, self, "name_id")
        ar << (Int32, self, "name_number")
        ar << (Uint32, self, "object_flags")  # & 8: main object
        if ar.version <= "4.15":
            ar << (Uint32, self, "size")
        else:
            ar << (Uint64, self, "size")
        ar << (Uint32, self, "offset")

        # packageguid and other flags.
        remain_size = self.get_remainings_size(ar.version)
        ar << (Bytes, self, "remainings", remain_size)

    @staticmethod
    def get_remainings_size(version: VersionInfo) -> int:
        sizes = [
            ["4.2", 32],
            ["4.10", 36],
            ["4.13", 40],
            ["4.15", 60],
            ["4.27", 64],
            ["5.0", 68]
        ]
        for ver, size in sizes:
            if version <= ver:
                return size
        # 5.1 ~
        return 56

    @staticmethod
    def get_struct_size(version: VersionInfo):
        meta_size = 32
        if version >= "4.14":
            meta_size += 4
        if version >= "4.16":
            meta_size += 4
        meta_size += UassetExport.get_remainings_size(version)
        return meta_size

    def name_export(self, exports: list[ExportBase], imports: list[ImportBase], name_list: list[NameBase]):
        self.name = str(name_list[self.name_id])

        def index_to_name(index: int):
            if index == 0:
                return "None"
            elif -index - 1 < 0:
                return exports[index].name
            return imports[-index - 1].name

        self.class_name = index_to_name(self.class_index)
        self.super_name = index_to_name(self.super_index)
        self.template_name = index_to_name(self.template_index)

    def print(self, padding=2):
        pad = " " * padding
        print(pad + f"{self.name}")
        print(pad + f"  class: {self.class_name}")
        print(pad + f"  super: {self.super_name}")
        if (self.template_name):
            print(pad + f"  template: {self.template_name}")
        print(pad + f"  size: {self.size}")
        print(pad + f"  offset: {self.offset}")
        print(pad + f"  is public: {self.is_public()}")
        print(pad + f"  is standalone: {self.is_standalone()}")
        print(pad + f"  is base: {self.is_base()}")
        print(pad + f"  object flags: {self.object_flags}")


class ZenName(NameBase):
    def serialize_hash(self, ar: ArchiveBase):
        ar << (Uint64, self, "hash")

    def serialize_head(self, ar: ArchiveBase):
        ar << (Bytes, self, "head", 2)

    def serialize_string(self, ar: ArchiveBase):
        length = self.head[1] + ((self.head[0] & 0x7F) << 8)
        is_utf16 = (self.head[0] & 0x80) > 0
        ar << (StringWithLen, self, "name", length, is_utf16)

    def serialize_head_and_string(self, ar: ArchiveBase):
        self.serialize_head(ar)
        self.serialize_string(ar)

    def update(self, new_name, update_hash=False):
        length = len(new_name)
        is_utf16 = not new_name.isascii()
        self.head = bytes([(length >> 8) + is_utf16 * 0x80, length & 0xFF])
        self.name = new_name
        if update_hash:
            string = new_name.lower()
            if string.isascii():
                binary = string.encode("ascii")
            else:
                binary = string.encode("utf-16-le")
            self.hash = city_hash_64(binary)


class ImportType(IntEnum):
    Export = 0
    ScriptImport = 1
    PackageImport = 2


# Ucas assets don't have class names.
# So, we need to determine them from hashes.
# The object hashes can be generated by generate_hash_from_object_path()
SCRIPT_OBJECTS = {
    # hash: ("class", "super class", "package")
    0x11acced3dc7c0922: ("/Script/Engine", "Package", "None"),
    0x1b93bca796d1fa6f: ("Texture2D", "Class", "/Script/Engine"),
    0x2bfad34ac8b1f6d0: ("Default__Texture2D", "Texture2D", "/Script/Engine"),
    0x21ff31428abdc8ae: ("TextureCube", "Class", "/Script/Engine"),
    0x3712d23e90fd5fe5: ("Default__TextureCube", "TextureCube", "/Script/Engine"),
    0x2461c85f4ba3d161: ("VolumeTexture", "Class", "/Script/Engine"),
    0x015b0407da6ae563: ("Default__VolumeTexture", "VolumeTexture", "/Script/Engine"),
    0x2b74936cc124e6fb: ("Texture2DArray", "Class", "/Script/Engine"),
    0x250cd2505b93e715: ("Default__Texture2DArray", "Texture2DArray", "/Script/Engine"),
    0x22ebbf4da0c22e82: ("TextureCubeArray", "Class", "/Script/Engine"),
    0x14dba7ea9c83a397: ("Default__TextureCubeArray", "Texture2DArray", "/Script/Engine"),
    0x2fe6ca4e48506419: ("LightMapTexture2D", "Class", "/Script/Engine"),
    0x029e125411d1912f: ("Default__LightMapTexture2D", "LightMapTexture2D", "/Script/Engine"),
    0x1e90a76c6b6d37bf: ("ShadowMapTexture2D", "Class", "/Script/Engine"),
    0x01bb4bc588d632f7: ("Default__ShadowMapTexture2D", "ShadowMapTexture2D", "/Script/Engine"),
}


class ZenImport(ImportBase):
    """Import exntries for ucas assets (FPackageObjectIndex)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Public/Serialization/AsyncLoading2.h
    """
    INDEX_BITS = 62
    INDEX_MASK = (1 << INDEX_BITS) - 1

    def serialize(self, ar: ArchiveBase):
        if ar.is_writing:
            self.type_and_id = self.type << ZenImport.INDEX_BITS | self.id
        ar << (Uint64, self, "type_and_id")
        self.id = self.type_and_id & ZenImport.INDEX_MASK
        self.type = self.type_and_id >> ZenImport.INDEX_BITS

    def name_import(self, imports: list[ImportBase], name_list: list[ZenName]) -> str:
        if self.is_invalid():
            self.name = "Invalid"
            self.class_name = "None"
            self.package_name = "None"
        elif self.is_script_object() and self.id in SCRIPT_OBJECTS:
            # self.id is a city hash generated from a object path
            self.name, self.class_name, self.package_name = SCRIPT_OBJECTS[self.id]
        else:
            self.name = "???"
            self.class_name = "???"
            self.package_name = "???"
        return self.name

    def is_invalid(self) -> bool:
        return self.type_and_id == 0xFFFFFFFFFFFFFFFF

    def is_script_object(self) -> bool:
        return (self.type & ImportType.ScriptImport) > 0

    def is_export(self) -> bool:
        return (self.type & ImportType.Export) > 0

    @staticmethod
    def get_struct_size(ar: ArchiveBase) -> int:
        return 8

    def generate_hash_from_object_path(self):
        if (self.package_name == "None"):
            object_path = self.name
        else:
            object_path = self.package_name + "." + self.name
        object_path = object_path.replace(".", "/")
        object_path = object_path.replace(":", "/")
        object_path = object_path.lower()
        binary = object_path.encode("utf-16-le")
        self.id = city_hash_64(binary) & ~(3 << ZenImport.INDEX_BITS)

    def print(self, padding=2):
        pad = " " * padding
        print(f"{pad}{self.name}")
        if self.is_invalid():
            print(f"{pad}  type: Invalid")
        else:
            print(f"{pad}  type: {self.type}")
            print(f"{pad}  id: {hex(self.id)}")
        print(f"{pad}  class: {self.class_name}")
        print(f"{pad}  package_name: {self.package_name}")


class ZenExport(ExportBase):
    """Export entries for ucas assets. (FExportMapEntry)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Public/Serialization/AsyncLoading2.h
    """

    def serialize(self, ar: ArchiveBase):
        ar << (Uint64, self, "offset")
        ar << (Uint64, self, "size")
        ar << (Uint32, self, "name_id")
        ar << (Uint32, self, "name_number")
        ar << (ZenImport, self, "outer_index")
        ar << (ZenImport, self, "class_index")
        ar << (ZenImport, self, "super_index")
        ar << (ZenImport, self, "template_index")
        ar << (Uint64, self, "public_export_hash")
        ar << (Uint32, self, "object_flags")
        ar << (Uint8, self, "filter_flags")
        ar == (Bytes, b"\x00\x00\x00", "pad", 3)

    def name_export(self, exports: list[ExportBase], imports: list[ZenImport], name_list: list[ZenName]):
        self.name = str(name_list[self.name_id])

        def index_to_name(index: ZenImport) -> str:
            if index.is_invalid():
                return "None"
            elif index.is_export():
                return exports[index.id].name
            elif (index.is_script_object() and index.id in SCRIPT_OBJECTS):
                return SCRIPT_OBJECTS[index.id][0]
            return "???"

        self.class_name = index_to_name(self.class_index)
        self.super_name = index_to_name(self.super_index)
        self.template_name = index_to_name(self.template_index)

    @staticmethod
    def get_struct_size(version: VersionInfo):
        return 72

    def print(self, padding=2):
        pad = " " * padding
        print(pad + f"{self.name}")
        print(pad + f"  class: {self.class_name}")
        print(pad + f"  super: {self.super_name}")
        print(pad + f"  template: {self.template_name}")
        print(pad + f"  size: {self.size}")
        print(pad + f"  offset: {self.offset}")
        print(pad + f"  is public: {self.is_public()}")
        print(pad + f"  is standalone: {self.is_standalone()}")
        print(pad + f"  is base: {self.is_base()}")
        print(pad + f"  object flags: {self.object_flags}")
