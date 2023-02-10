'''Classes for .uasset'''
from enum import IntEnum
import io
from io import IOBase
import os

from util import mkdir
from .crc import generate_hash, strcrc_deprecated
from .utexture import Utexture
from .version import VersionInfo
from .archive import (ArchiveBase, ArchiveRead, ArchiveWrite,
                      Uint32, Uint64, Int32, Int64, Bytes, String,
                      Int32Array, StructArray, Buffer,
                      SerializableBase)


EXT = ['.uasset', '.uexp', '.ubulk']


def get_all_file_path(file: str) -> list[str]:
    '''Get all file paths for texture asset from a file path.'''
    base_name, ext = os.path.splitext(file)
    if ext not in EXT:
        raise RuntimeError(f'Not Uasset. ({file})')
    return [base_name + ext for ext in EXT]


class PackageFlags(IntEnum):
    PKG_UnversionedProperties = 0x2000   # Uses unversioned property serialization
    PKG_FilterEditorOnly = 0x80000000  # Package has editor-only data filtered out


class ObjectFlags(IntEnum):
    RF_Public = 1
    RF_Standalone = 2  # Main object in the asset
    RF_Transactional = 8
    RF_ClassDefaultObject = 0x10  # Default object
    RF_ArchetypeObject = 0x20  # Template for another object


class UassetFileSummary(SerializableBase):
    """Info for .uasset file (FPackageFileSummary)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Private/UObject/PackageFileSummary.cpp
    """
    TAG = b'\xC1\x83\x2A\x9E'  # Magic for uasset files
    TAG_SWAPPED = b'\x9E\x2A\x83\xC1'  # for big endian files

    def serialize(self, ar: ArchiveBase):
        self.file_name = ar.name

        ar << (Bytes, self, "tag", 4)
        ar.endian = self.get_endian()

        """
        File version
        positive: 3.x
        -3: 4.0 ~ 4.6
        -5: 4.7 ~ 4.9
        -6: 4.10 ~ 4.13
        -7: 4.14 ~ 4.27
        -8: 5.0 ~
        """
        expected_version = (
            -8 + (ar.version <= '4.6') * 2 + (ar.version <= '4.9')
            + (ar.version <= '4.13') + (ar.version <= '4.27')
        )
        ar == (Int32, expected_version, "header.file_version")

        """
        Version info. But most assets have zeros for these variables. (unversioning)
        So, we can't get UE version from them.
        - LegacyUE3Version
        - FileVersionUE.FileVersionUE4
        - FileVersionUE.FileVersionUE5 (Added at 5.0)
        - FileVersionLicenseeUE
        - CustomVersionContainer
        """
        ar << (Bytes, self, "version_info", 16 + 4 * (ar.version >= '5.0'))

        ar << (Int32, self, "uasset_size")  # TotalHeaderSize
        ar << (String, self, "package_name")

        # PackageFlags
        ar << (Uint32, self, "pkg_flags")
        if ar.is_reading:
            ar.check(self.pkg_flags & PackageFlags.PKG_FilterEditorOnly > 0, True,
                     msg="Unsupported file format detected. (PKG_FilterEditorOnlyitorOnly is false.)")

        # Name table
        ar << (Int32, self, "name_count")
        ar << (Int32, self, "name_offset")

        if ar.version >= '5.1':
            # SoftObjectPaths
            ar == (Int32, 0, "soft_object_count")
            if ar.is_writing:
                self.soft_object_offset = self.import_offset
            ar << (Int32, self, "soft_object_offset")

        if ar.version >= '4.9':
            # GatherableTextData
            ar == (Int32, 0, "gatherable_text_count")
            ar == (Int32, 0, "gatherable_text_offset")

        # Exports
        ar << (Int32, self, "export_count")
        ar << (Int32, self, "export_offset")

        # Imports
        ar << (Int32, self, "import_count")
        ar << (Int32, self, "import_offset")

        # DependsOffset
        ar << (Int32, self, "depends_offset")

        if ar.version >= '4.4' and ar.version <= '4.14':
            # StringAssetReferencesCount
            ar == (Int32, 0, "string_asset_count")
            if ar.is_writing:
                self.string_asset_offset = self.asset_registry_data_offset
            ar << (Int32, self, "string_asset_offset")
        elif ar.version >= '4.15':
            # SoftPackageReferencesCount
            ar == (Int32, 0, "soft_package_count")
            ar == (Int32, 0, "soft_package_offset")

            # SearchableNamesOffset
            ar == (Int32, 0, "searchable_name_offset")

        # ThumbnailTableOffset
        ar == (Int32, 0, "thumbnail_table_offset")

        ar << (Bytes, self, "guid", 16)  # GUID

        # Generations: Export count and name count for previous versions of this package
        ar << (Int32, self, "generation_count")
        if self.generation_count <= 0 or self.generation_count >= 10:
            raise RuntimeError(f"Unexpected value. (generation_count: {self.generation_count})")
        ar << (Int32Array, self, "generation_data", self.generation_count * 2)

        """
        - SavedByEngineVersion (14 bytes)
        - CompatibleWithEngineVersion (14 bytes) (4.8 ~ )
        """
        ar << (Bytes, self, "empty_engine_version", 14 * (1 + (ar.version >= '4.8')))

        # CompressionFlags, CompressedChunks
        ar << (Bytes, self, "compression_info", 8)

        """
        PackageSource:
            Value that is used to determine if the package was saved by developer or not.
            CRC hash for shipping builds. Others for user created files.
        """
        ar << (Uint32, self, "package_source")

        # AdditionalPackagesToCook (zero length array)
        ar == (Int32, 0, "additional_packages_to_cook")

        if ar.version <= '4.13':
            ar == (Int32, 0, "num_texture_allocations")
        ar << (Int32, self, "asset_registry_data_offset")
        ar << (Int32, self, "bulk_offset")  # .uasset + .uexp - 4 (BulkDataStartOffset)

        # WorldTileInfoDataOffset
        ar == (Int32, 0, "world_tile_info_offset")

        # ChunkIDs (zero length array), ChunkID
        ar == (Int32Array, [0, 0], "ChunkID", 2)

        if ar.version <= '4.13':
            return

        # PreloadDependency
        ar << (Int32, self, "preload_dependency_count")
        ar << (Int32, self, "preload_dependency_offset")

        if ar.version <= '4.27':
            return

        # Number of names that are referenced from serialized export data
        ar << (Int32, self, "referenced_names_count")

        # Location into the file on disk for the payload table of contents data
        ar << (Int64, self, "payload_toc_offset")

    def print(self):
        print('File Summary')
        print(f'  file size: {self.uasset_size}')
        print(f'  number of names: {self.name_count}')
        print('  name directory offset: 193')
        print(f'  number of exports: {self.export_count}')
        print(f'  export directory offset: {self.export_offset}')
        print(f'  number of imports: {self.import_count}')
        print(f'  import directory offset: {self.import_offset}')
        print(f'  depends offset: {self.depends_offset}')
        print(f'  file length (uasset+uexp-4): {self.bulk_offset}')
        print(f'  official asset: {self.is_official()}')
        print(f"  unversioned: {self.is_unversioned()}")

    def is_unversioned(self):
        return (self.pkg_flags & PackageFlags.PKG_UnversionedProperties) > 0

    def is_official(self):
        crc = strcrc_deprecated("".join(os.path.basename(self.file_name).split(".")[:-1]))
        return self.package_source == crc

    def update_package_source(self, file_name=None, is_official=True):
        if file_name is not None:
            self.file_name = file_name
        if is_official:
            crc = strcrc_deprecated("".join(os.path.basename(self.file_name).split(".")[:-1]))
        else:
            crc = int.from_bytes(b"MOD ", "little")
        self.package_source = crc

    def get_endian(self):
        if self.tag == UassetFileSummary.TAG:
            return "little"
        elif self.tag == UassetFileSummary.TAG_SWAPPED:
            return "big"
        raise RuntimeError(f"Invalid tag detected. ({self.tag})")


class Name(SerializableBase):
    def __init__(self):
        self.hash = None

    def serialize(self, ar: ArchiveBase):
        ar << (String, self, "name")
        if ar.version <= "4.11":
            return
        ar << (Bytes, self, "hash", 4)

    def __str__(self):
        return self.name

    def update(self, new_name, update_hash=False):
        self.name = new_name
        if update_hash:
            self.hash = generate_hash(new_name)


class UassetImport(SerializableBase):
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
        if ar.version >= '5.0':
            ar << (Uint32, self, "optional")

    def name_import(self, name_list: list[Name]) -> str:
        self.name = str(name_list[self.name_id])
        self.class_name = str(name_list[self.class_name_id])
        self.class_package_name = str(name_list[self.class_package_name_id])
        return self.name

    def print(self, padding=2):
        pad = ' ' * padding
        print(pad + self.name)
        print(pad + '  class: ' + self.class_name)
        print(pad + '  class_file: ' + self.class_package_name)


class Uunknown(SerializableBase):
    """Unknown Uobject."""
    def __init__(self, uasset, size):
        self.uasset = uasset
        self.uexp_size = size
        self.has_ubulk = False

    def serialize(self, uexp_io: ArchiveBase):
        uexp_io << (Buffer, self, "bin", self.uexp_size)
        if uexp_io.is_writing:
            self.uexp_size = len(self.bin)


class UassetExport(SerializableBase):
    """Meta data for an object that is contained within this file. (FObjectExport)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Private/UObject/ObjectResource.cpp
    """
    TEXTURE_CLASSES = [
        "Texture2D", "TextureCube", "LightMapTexture2D", "ShadowMapTexture2D",
        "Texture2DArray", "TextureCubeArray", "VolumeTexture"
    ]

    def __init__(self):
        self.object = None  # The actual data will be stored here
        self.meta_size = 0  # binary size of meta data

    def serialize(self, ar: ArchiveBase):
        ar << (Int32, self, "class_import_id")
        if ar.version >= '4.14':
            ar << (Int32, self, "template_index")
        ar << (Int32, self, "super_import_id")
        ar << (Int32, self, "outer_index")  # 0: main object, 1: not main
        ar << (Int32, self, "name_id")
        ar << (Int32, self, "name_number")
        ar << (Uint32, self, "object_flags")  # & 8: main object
        if ar.version <= '4.15':
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
            ['4.2', 32],
            ['4.10', 36],
            ['4.13', 40],
            ['4.15', 60],
            ['4.27', 64],
            ['5.0', 68]
        ]
        for ver, size in sizes:
            if version <= ver:
                return size
        # 5.1 ~
        return 56

    @staticmethod
    def get_meta_size(version: VersionInfo):
        meta_size = 32
        if version >= '4.14':
            meta_size += 4
        if version >= '4.16':
            meta_size += 4
        meta_size += UassetExport.get_remainings_size(version)
        return meta_size

    def update(self, size, offset):
        self.size = size
        self.offset = offset

    def name_export(self, imports: list[UassetImport], name_list: list[Name]):
        self.name = str(name_list[self.name_id])
        self.class_name = imports[-self.class_import_id-1].name
        self.super_name = imports[-self.super_import_id-1].name

    def is_base(self):
        return (self.object_flags & ObjectFlags.RF_ArchetypeObject > 0
                or self.object_flags & ObjectFlags.RF_ClassDefaultObject > 0)

    def is_standalone(self):
        return self.object_flags & ObjectFlags.RF_Standalone > 0

    def is_public(self):
        return self.object_flags & ObjectFlags.RF_Public > 0

    def is_texture(self):
        return self.class_name in UassetExport.TEXTURE_CLASSES

    def print(self, padding=2):
        pad = ' ' * padding
        print(pad + f'{self.name}')
        print(pad + f'  class: {self.class_name}')
        print(pad + f'  super: {self.super_name}')
        print(pad + f'  size: {self.size}')
        print(pad + f'  offset: {self.offset}')
        print(pad + f'  is public: {self.is_public()}')
        print(pad + f'  is standalone: {self.is_standalone()}')
        print(pad + f'  is base: {self.is_base()}')
        print(pad + f'  object flags: {self.object_flags}')


class Uasset:
    def __init__(self, file_path: str, version: str = "ff7r", verbose=False):
        if not os.path.isfile(file_path):
            raise RuntimeError(f'Not File. ({file_path})')

        self.texture = None
        self.uexp_io = None
        self.ubulk_io = None
        self.uasset_file, self.uexp_file, self.ubulk_file = get_all_file_path(file_path)
        print('load: ' + self.uasset_file)

        if self.uasset_file[-7:] != '.uasset':
            raise RuntimeError(f'Not .uasset. ({self.uasset_file})')

        if verbose:
            print('Loading ' + self.uasset_file + '...')

        self.version = VersionInfo(version)
        self.context = {"version": self.version, "verbose": verbose, "valid": False}
        ar = ArchiveRead(open(self.uasset_file, 'rb'), context=self.context)
        self.serialize(ar)
        ar.close()
        self.read_export_objects(verbose=verbose)

    def serialize(self, ar: ArchiveBase):
        # read header
        if ar.is_reading:
            ar << (UassetFileSummary, self, "header")
            if ar.verbose:
                self.header.print()
        else:
            ar.seek(self.header.name_offset)

        # read name map
        ar << (StructArray, self, "name_list", Name, self.header.name_count)
        if ar.verbose:
            print('Names')
            for i, name in zip(range(len(self.name_list)), self.name_list):
                print('  {}: {}'.format(i, name))

        # read imports
        if ar.is_reading:
            ar.check(self.header.import_offset, ar.tell())
        else:
            self.header.import_offset = ar.tell()
        ar << (StructArray, self, "imports", UassetImport, self.header.import_count)
        if ar.is_reading:
            list(map(lambda x: x.name_import(self.name_list), self.imports))
            if ar.verbose:
                print('Imports')
                list(map(lambda x: x.print(), self.imports))

        if ar.is_reading:
            # read exports
            ar.check(self.header.export_offset, ar.tell())
            ar << (StructArray, self, "exports", UassetExport, self.header.export_count)
            list(map(lambda x: x.name_export(self.imports, self.name_list), self.exports))
            if ar.verbose:
                print('Exports')
                list(map(lambda x: x.print(), self.exports))
                print(f'Main Export Class: {self.get_main_class_name()}')
        else:
            # skip exports part
            self.header.export_offset = ar.tell()
            ar.seek(UassetExport.get_meta_size(ar.version) * self.header.export_count, 1)
            if self.version not in ['4.15', '4.14']:
                self.header.depends_offset = ar.tell()

        # read depends map
        ar << (Int32Array, self, "depends_map", self.header.export_count)

        # write asset registry data
        if ar.is_reading:
            ar.check(self.header.asset_registry_data_offset, ar.tell())
        else:
            self.header.asset_registry_data_offset = ar.tell()
        ar == (Int32, 0, "asset_registry_data")

        # Preload dependencies (import and export ids that must be serialized before other exports)
        if self.has_uexp():
            if ar.is_reading:
                ar.check(self.header.preload_dependency_offset, ar.tell())
            else:
                self.header.preload_dependency_offset = ar.tell()
            ar << (Int32Array, self, "preload_dependencly_ids", self.header.preload_dependency_count)

        if ar.is_reading:
            ar.check(ar.tell(), self.get_size())
            if self.has_uexp():
                self.uexp_bin = None
                self.ubulk_bin = None
            else:
                self.uexp_size = self.header.bulk_offset - self.header.uasset_size
                self.uexp_bin = ar.read(self.uexp_size)
                self.ubulk_bin = ar.read(ar.size - ar.tell() - 4)
                ar == (Bytes, self.header.tag, "tail_tag", 4)
        else:
            self.header.uasset_size = ar.tell()
            self.header.bulk_offset = self.uexp_size + self.header.uasset_size
            self.header.name_count = len(self.name_list)
            # write header
            ar.seek(0)
            ar << (UassetFileSummary, self, "header")

            # write exports
            ar.seek(self.header.export_offset)
            offset = self.header.uasset_size
            for export in self.exports:
                export.update(export.size, offset)
                offset += export.size
            ar << (StructArray, self, "exports", UassetExport, self.header.export_count)

            if not self.has_uexp():
                ar.seek(self.header.uasset_size)
                ar.write(self.uexp_bin)
                ar.write(self.ubulk_bin)
                ar.write(self.header.tag)

    def read_export_objects(self, verbose=False):
        uexp_io = self.get_uexp_io(rb=True)
        for exp in self.exports:
            if verbose:
                print(f"{exp.name}: (offset: {uexp_io.tell()})")
            if exp.is_texture():
                exp.object = Utexture(self, class_name=exp.class_name)
            else:
                exp.object = Uunknown(self, exp.size)
            exp.object.serialize(uexp_io)
            uexp_io.check(exp.object.uexp_size, exp.size)
        self.close_uexp_io(rb=True)
        self.close_ubulk_io(rb=True)

    def write_export_objects(self):
        uexp_io = self.get_uexp_io(rb=False)
        for exp in self.exports:
            exp.object.serialize(uexp_io)
            offset = uexp_io.tell()
            exp.update(exp.object.uexp_size, offset)
        self.uexp_size = uexp_io.tell()
        for exp in self.exports:
            if exp.is_texture():
                exp.object.rewrite_offset_data()
        self.close_uexp_io(rb=False)
        self.close_ubulk_io(rb=False)

    def save(self, file: str, valid=False):
        folder = os.path.dirname(file)
        if folder not in ['.', ''] and not os.path.exists(folder):
            mkdir(folder)

        self.uasset_file, self.uexp_file, self.ubulk_file = get_all_file_path(file)

        if not self.has_ubulk():
            self.ubulk_file = None

        print('save :' + self.uasset_file)

        self.context = {"version": self.version, "verbose": False, "valid": valid}
        self.write_export_objects()

        ar = ArchiveWrite(open(self.uasset_file, 'wb'), context=self.context)

        self.serialize(ar)

        ar.close()

    def update_name_list(self, i: int, new_name: str):
        name = self.name_list[i]
        old_name = str(name)
        name.update(new_name, update_hash=self.version >= "4.12")

        def get_size(string):
            is_utf16 = not string.isascii()
            return (len(string) + 1) * (1 + is_utf16)

        # Update file size
        self.header.uasset_size += get_size(new_name) - get_size(old_name)

    def get_main_export(self) -> UassetExport:
        main_list = [exp for exp in self.exports if (exp.is_public() and not exp.is_base())]
        standalone_list = [exp for exp in main_list if exp.is_standalone()]
        if len(standalone_list) > 0:
            return standalone_list[0]
        if len(main_list) > 0:
            return main_list[0]
        return None

    def get_main_class_name(self):
        main_obj = self.get_main_export()
        if main_obj is None:
            return "None"
        else:
            return main_obj.class_name

    def has_uexp(self):
        return self.version >= '4.16'

    def has_ubulk(self):
        for exp in self.exports:
            if exp.object.has_ubulk:
                return True
        return False

    def has_textures(self):
        for exp in self.exports:
            if exp.is_texture():
                return True
        return False

    def get_texture_list(self) -> list[Utexture]:
        textures = []
        for exp in self.exports:
            if exp.is_texture():
                textures.append(exp.object)
        return textures

    def __get_io(self, file: str, bin: bytes, rb: bool) -> IOBase:
        if self.has_uexp():
            opened_io = open(file, "rb" if rb else "wb")
        else:
            opened_io = io.BytesIO(bin if rb else b'')

        if rb:
            return ArchiveRead(opened_io, context=self.context)
        else:
            return ArchiveWrite(opened_io, context=self.context)

    def get_uexp_io(self, rb=True) -> IOBase:
        if self.uexp_io is None:
            self.uexp_io = self.__get_io(self.uexp_file, self.uexp_bin, rb)
        return self.uexp_io

    def get_ubulk_io(self, rb=True) -> IOBase:
        if self.ubulk_io is None:
            self.ubulk_io = self.__get_io(self.ubulk_file, self.ubulk_bin, rb)
        return self.ubulk_io

    def close_uexp_io(self, rb=True):
        if self.uexp_io is None:
            return
        ar = self.uexp_io
        self.uexp_size = ar.tell()
        if self.has_uexp():
            if rb:
                ar.check(ar.read(4), UassetFileSummary.TAG)
            else:
                ar.write(UassetFileSummary.TAG)
        else:
            if not rb:
                ar.seek(0)
                self.uexp_bin = ar.read()
        ar.close()
        self.uexp_io = None

    def close_ubulk_io(self, rb=True):
        if self.ubulk_io is None:
            return
        ar = self.ubulk_io
        if rb:
            ar.check(ar.tell(), ar.size)
        else:
            if not self.has_uexp():
                ar.seek(0)
                self.ubulk_bin = ar.read()
        ar.close()
        self.ubulk_io = None

    def get_all_file_path(self):
        if self.has_uexp():
            if self.has_ubulk():
                return self.uasset_file, self.uexp_file, self.ubulk_file
            else:
                return self.uasset_file, self.uexp_file, None
        else:
            return self.uasset_file, None, None

    def get_size(self):
        return self.header.uasset_size

    def get_uexp_size(self):
        return self.uexp_size

    def update_package_source(self, file_name=None, is_official=True):
        self.header.update_package_source(file_name=file_name, is_official=is_official)
