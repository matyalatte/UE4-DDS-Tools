'''Classes for .uasset'''
import io
import os
import ctypes as c
from enum import IntEnum
import io_util
from .crc import generate_hash, strcrc_deprecated
from .utexture import Utexture
from .version import VersionInfo


EXT = ['.uasset', '.uexp', '.ubulk']


def get_all_file_path(file):
    '''Get all file paths for texture asset from a file path.'''
    base_name, ext = os.path.splitext(file)
    if ext not in EXT:
        raise RuntimeError(f'Not Uasset. ({file})')
    return [base_name + ext for ext in EXT]


class PackageFlags(IntEnum):
    PKG_UnversionedProperties = 0x2000   # Uses unversioned property serialization
    PKG_FilterEditorOnly = 0x80000000  # Package has editor-only data filtered out


class ObjectFlags(IntEnum):
    RF_Standalone = 2  # Main object in the asset
    RF_Transactional = 8


class UassetFileSummary:
    """Info for .uasset file (FPackageFileSummary)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Private/UObject/PackageFileSummary.cpp
    """
    TAG = b'\xC1\x83\x2A\x9E'  # Magic for uasset files
    TAG_SWAPPED = b'\x9E\x2A\x83\xC1'  # for big endian files

    def __init__(self, f, version):
        self.file_name = f.name

        # Tag
        tag = f.read(4)
        if tag == UassetFileSummary.TAG_SWAPPED:
            raise RuntimeError("Big endian files are unsupported.")
        io_util.check(tag, UassetFileSummary.TAG, msg="Not uasset file. (Invalid tag detected.)")

        """
        File version
        5: ~ 4.13
        6: 4.14 ~ 4.27
        7: 5.0 ~
        """
        self.file_version = -io_util.read_int32(f) - 1
        if self.file_version < 5:
            raise RuntimeError(f"An old file version detected. This is unsupported. ({self.file_version})")
        if self.file_version > 7:
            raise RuntimeError(f"Unsupported file version detected. ({self.file_version})")
        io_util.check(self.file_version, 6 - (version <= '4.13') + (version >= '5.0'))

        """ version_info (16 or 20 bytes)
        - LegacyUE3Version
        - FileVersionUE.FileVersionUE4
        - FileVersionUE.FileVersionUE5 (for UE5.0 ~)
        - FileVersionLicenseeUE
        - CustomVersionContainer
        """
        self.version_info = f.read(16 + 4 * (self.file_version >= 7))

        self.uasset_size = io_util.read_uint32(f)  # TotalHeaderSize
        self.package_name = io_util.read_str(f)  # "None" for most of assets

        # PackageFlags
        self.pkg_flags = io_util.read_uint32(f)
        io_util.check(self.pkg_flags & PackageFlags.PKG_FilterEditorOnly > 0, True,
                      msg="Unsupported file format detected. (PKG_FilterEditorOnlyitorOnly is false.)")

        # Name table
        self.name_count = io_util.read_uint32(f)
        self.name_offset = io_util.read_uint32(f)

        if (version >= '5.1'):
            # SoftObjectPaths
            io_util.read_null(f, msg="Soft object paths are unsupported.")  # Count
            f.seek(4, 1)  # Offset (same as import_offset)

        # GatherableTextData
        io_util.read_null(f, msg="Gatherable text data is unsupported.")  # Count
        io_util.read_null(f)  # Offset

        # Exports
        self.export_count = io_util.read_uint32(f)
        self.export_offset = io_util.read_uint32(f)

        # Imports
        self.import_count = io_util.read_uint32(f)
        self.import_offset = io_util.read_uint32(f)

        # DependsOffset
        self.depends_offset = io_util.read_uint32(f)

        if version <= '4.14':
            # StringAssetReferencesCount
            io_util.read_null(f, msg="String asset references are unsupported.")
            f.seek(4, 1)  # StringAssetReferencesOffset
        else:
            # SoftPackageReferencesCount
            io_util.read_null(f, msg="Soft package references are unsupported.")
            io_util.read_null(f)  # SoftPackageReferencesOffset

            # SearchableNamesOffset
            io_util.read_null(f, msg="Searchable names are unsupported.")

        # ThumbnailTableOffset
        io_util.read_null(f, msg="Thumbnail table is unsupported.")

        self.guid = f.read(16)  # GUID

        # Generations: Export count and name count for previous versions of this package
        self.generation_count = io_util.read_uint32(f)
        if self.generation_count <= 0 or self.generation_count >= 10:
            raise RuntimeError(f"Unexpected value. (generation_count: {self.generation_count})")
        self.generation_data = io_util.read_uint32_array(f, len=self.generation_count * 2)

        """
        - SavedByEngineVersion (14 bytes)
        - CompatibleWithEngineVersion (14 bytes)
        - CompressionFlags
        - CompressedChunks
        """
        io_util.read_null_array(f, 9)

        """
        PackageSource:
            Value that is used to determine if the package was saved by developer or not.
            CRC hash for shipping builds. Others for user created files.
        """
        self.package_source = io_util.read_uint32(f)

        io_util.read_null(f)  # AdditionalPackagesToCook (zero length array)
        if self.file_version <= 5:
            io_util.read_null(f)  # NumTextureAllocations
        self.asset_registry_data_offset = io_util.read_uint32(f)
        self.bulk_offset = io_util.read_uint32(f)  # .uasset + .uexp - 4 (BulkDataStartOffset)

        """
        - WorldTileInfoDataOffset
        - ChunkIDs (zero length array)
        - ChunkID
        """
        io_util.read_null_array(f, 3)

        if self.file_version <= 5:
            return

        # PreloadDependency
        self.preload_dependency_count = io_util.read_int32(f)
        self.preload_dependency_offset = io_util.read_uint32(f)

        if self.file_version <= 6:
            return

        # Number of names that are referenced from serialized export data
        self.referenced_names_count = io_util.read_uint32(f)

        # Location into the file on disk for the payload table of contents data
        self.payload_toc_offset = io_util.read_int64(f)

    def write(self, f, version):
        f.write(UassetFileSummary.TAG)
        io_util.write_int32(f, -self.file_version - 1)
        f.write(self.version_info)
        io_util.write_uint32(f, self.uasset_size)
        io_util.write_str(f, self.package_name)
        io_util.write_uint32(f, self.pkg_flags)
        io_util.write_uint32(f, self.name_count)
        io_util.write_uint32(f, self.name_offset)
        if (version >= '5.1'):
            io_util.write_null(f)
            io_util.write_uint32(f, self.import_offset)
        io_util.write_null_array(f, 2)
        io_util.write_uint32(f, self.export_count)
        io_util.write_uint32(f, self.export_offset)
        io_util.write_uint32(f, self.import_count)
        io_util.write_uint32(f, self.import_offset)
        io_util.write_uint32(f, self.depends_offset)
        if version <= '4.14':
            io_util.write_null(f)
            io_util.write_uint32(f, self.asset_registry_data_offset)
        else:
            io_util.write_null_array(f, 3)
        io_util.write_null(f)
        f.write(self.guid)
        io_util.write_uint32(f, self.generation_count)
        io_util.write_uint32_array(f, self.generation_data)
        io_util.write_null_array(f, 9)
        io_util.write_uint32(f, self.package_source)
        io_util.write_null(f)
        if self.file_version <= 5:
            io_util.write_null(f)
        io_util.write_uint32(f, self.asset_registry_data_offset)
        io_util.write_uint32(f, self.bulk_offset)
        io_util.write_null_array(f, 3)

        if self.file_version <= 5:
            return
        io_util.write_int32(f, self.preload_dependency_count)
        io_util.write_uint32(f, self.preload_dependency_offset)

        if self.file_version <= 6:
            return
        io_util.write_uint32(f, self.referenced_names_count)
        io_util.write_int64(f, self.payload_toc_offset)

    def print(self):
        print('File Summary')
        print(f'  file size: {self.uasset_size}')
        print(f'  number of names: {self.name_count}')
        print('  name directory offset: 193')
        print(f'  number of exports: {self.export_count}')
        print(f'  export directory offset: {self.export_offset}')
        print(f'  number of imports: {self.import_count}')
        print(f'  import directory offset: {self.import_offset}')
        print(f'  end offset of export: {self.depends_offset}')
        print(f'  file length (uasset+uexp-4): {self.bulk_offset}')
        print(f'  official asset: {self.is_official()}')

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


class UassetImport(c.LittleEndianStructure):
    """Meta data for an object that is contained within another file. (FObjectImport)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Private/UObject/ObjectResource.cpp
    """

    _pack_ = 1
    _fields_ = [  # 28 bytes
        ("class_package_name_id", c.c_uint32),  # name id for the file path of the class
        ("class_package_name_number", c.c_uint32),  # null
        ("class_name_id", c.c_uint32),  # name id for the class
        ("class_name_number", c.c_uint32),  # null
        ("class_package_import_id", c.c_int32),  # import id for the class
        ("name_id", c.c_uint32),  # name id for the object name
        ("package_name_id", c.c_uint32),  # name id for the package
    ]

    @staticmethod
    def read(f, version):
        imp = UassetImport()
        f.readinto(imp)
        if version >= '5.0':
            imp.optional = io_util.read_uint32(f)  # bImportOptional
        return imp

    def write(self, f, version):
        f.write(self)
        if version >= '5.0':
            io_util.write_uint32(f, self.optional)

    def name_import(self, name_list):
        self.name = name_list[self.name_id]
        self.class_name = name_list[self.class_name_id]
        self.class_package_name = name_list[self.class_package_name_id]
        self.package_name = name_list[self.package_name_id]
        return self.name

    def print(self, padding=2):
        pad = ' ' * padding
        print(pad + self.name)
        print(pad + '  file: ' + self.package_name)
        print(pad + '  class: ' + self.class_name)
        print(pad + '  class_file: ' + self.class_package_name)


class Uunknown:
    """Unknown Uobject."""
    def __init__(self, uasset, size):
        self.uasset = uasset
        f = self.uasset.get_uexp_io(rb=True)
        self.bin = f.read(size)
        self.uexp_size = size
        self.has_ubulk = False

    def write(self, valid=False):
        f = self.uasset.get_uexp_io(rb=False)
        f.write(self.bin)
        self.uexp_size = len(self.bin)

    def is_texture(self):
        return False


class UassetExport:
    """Meta data for an object that is contained within this file. (FObjectExport)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Private/UObject/ObjectResource.cpp
    """
    TEXTURE_CLASSES = ["Texture2D", "TextureCube", "LightMapTexture2D"]

    def __init__(self, f, version):
        self.object = None  # The actual data will be stored here
        self.class_import_id = io_util.read_int32(f)
        if version >= '4.14':
            io_util.read_null(f)  # TemplateIndex
        self.super_import_id = io_util.read_int32(f)
        self.outer_index = io_util.read_uint32(f)  # 0: main object, 1: not main
        self.name_id = io_util.read_uint32(f)
        self.name_number = io_util.read_uint32(f)  # another number for FName
        self.object_flags = io_util.read_uint32(f)  # & 8: main object
        if version <= '4.15':
            self.size = io_util.read_uint32(f)
        else:
            self.size = io_util.read_uint64(f)
        self.offset = io_util.read_uint32(f)

        # packageguid and other flags.
        self.remainings = f.read(64 - 4 * (version <= '4.10') - 4 * (version <= '4.15') - 20 * (version <= '4.13') +
                                 4 * (version == '5.0') - 8 * (version >= '5.1'))

    def write(self, f, version):
        io_util.write_int32(f, self.class_import_id)
        if version > '4.13':
            io_util.write_null(f)
        io_util.write_int32(f, self.super_import_id)
        io_util.write_uint32(f, self.outer_index)
        io_util.write_uint32(f, self.name_id)
        io_util.write_uint32(f, self.name_number)
        io_util.write_uint32(f, self.object_flags)
        if version <= '4.15':
            io_util.write_uint32(f, self.size)
        else:
            io_util.write_uint64(f, self.size)
        io_util.write_uint32(f, self.offset)
        f.write(self.remainings)

    def update(self, size, offset):
        self.size = size
        self.offset = offset

    def name_export(self, imports, name_list):
        self.name = name_list[self.name_id]
        self.class_name = imports[-self.class_import_id-1].name
        self.super_name = imports[-self.super_import_id-1].name

    def is_main(self):
        return self.object_flags & ObjectFlags.RF_Standalone > 0

    def is_texture(self):
        return self.class_name in UassetExport.TEXTURE_CLASSES

    def skip_uexp(self, uasset):
        self.object = Uunknown(uasset, self.size)

    def print(self, padding=2):
        pad = ' ' * padding
        print(pad + f'{self.name}')
        print(pad + f'  class: {self.class_name}')
        print(pad + f'  super: {self.super_name}')
        print(pad + f'  size: {self.size}')
        print(pad + f'  offset: {self.offset}')
        print(pad + f'  main object: {self.is_main()}')


class Uasset:
    def __init__(self, file_path, version="ff7r", verbose=False):
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

        with open(self.uasset_file, 'rb') as f:
            # read header
            self.header = UassetFileSummary(f, self.version)

            if verbose:
                self.header.print()
                print('Names')

            # read name map
            def read_names(f, i):
                name = io_util.read_str(f)
                if verbose:
                    print('  {}: {}'.format(i, name))
                if self.version <= "4.11":
                    return name, None
                hash = f.read(4)
                return name, hash
            names = [read_names(f, i) for i in range(self.header.name_count)]
            self.name_list = [x[0] for x in names]
            self.hash_list = [x[1] for x in names]

            # read imports
            self.imports = [UassetImport.read(f, self.version) for i in range(self.header.import_count)]
            list(map(lambda x: x.name_import(self.name_list), self.imports))
            if verbose:
                print('Imports')
                list(map(lambda x: x.print(), self.imports))

            # read exports
            self.exports = [UassetExport(f, self.version) for i in range(self.header.export_count)]
            list(map(lambda x: x.name_export(self.imports, self.name_list), self.exports))
            if verbose:
                print('Exports')
                list(map(lambda x: x.print(), self.exports))

            io_util.read_null_array(f, self.header.export_count)

            # read asset registry data
            io_util.check(self.header.asset_registry_data_offset, f.tell())
            io_util.read_null(f)  # zero length array?

            if self.has_uexp():
                # Preload dependencies (import and export ids that must be serialized before other exports)
                io_util.check(self.header.preload_dependency_offset, f.tell())
                self.preload_dependency_ids = io_util.read_int32_array(f, len=self.header.preload_dependency_count)

            io_util.check(f.tell(), self.get_size())

            if self.has_uexp():
                self.uexp_bin = None
                self.ubulk_bin = None
            else:
                self.uexp_size = self.header.bulk_offset - self.header.uasset_size
                self.uexp_bin = f.read(self.uexp_size)
                self.ubulk_bin = f.read(io_util.get_size(f) - f.tell() - 4)
                io_util.check(f.read(), UassetFileSummary.TAG)

        self.read_export_objects(verbose=verbose)

    def read_export_objects(self, verbose=False):
        uexp_io = self.get_uexp_io(rb=True)
        for exp in self.exports:
            if verbose:
                print(f"{exp.name}: (offset: {uexp_io.tell()})")
            if exp.is_texture():
                exp.object = Utexture(self, verbose=verbose, is_light_map="LightMap" in exp.class_name)
            else:
                exp.skip_uexp(self)
            io_util.check(exp.object.uexp_size, exp.size)
        self.close_uexp_io(rb=True)
        self.close_ubulk_io(rb=True)

    def write_export_objects(self, valid=False):
        uexp_io = self.get_uexp_io(rb=False)
        for exp in self.exports:
            exp.object.write(valid=valid)
            offset = uexp_io.tell()
            exp.update(exp.object.uexp_size, offset)
        self.close_uexp_io(rb=False)
        self.close_ubulk_io(rb=False)

    def save(self, file, valid=False):
        folder = os.path.dirname(file)
        if folder not in ['.', ''] and not os.path.exists(folder):
            io_util.mkdir(folder)

        self.uasset_file, self.uexp_file, self.ubulk_file = get_all_file_path(file)

        if not self.has_ubulk():
            self.ubulk_file = None

        print('save :' + self.uasset_file)

        self.write_export_objects(valid=valid)

        with open(self.uasset_file, 'wb') as f:
            # skip header part
            f.seek(self.header.name_offset)

            # write names
            for name, hash in zip(self.name_list, self.hash_list):
                io_util.write_str(f, name)
                if self.version >= "4.12":
                    f.write(hash)

            # write imports
            self.header.import_offset = f.tell()
            list(map(lambda x: x.write(f, self.version), self.imports))

            # skip exports part
            self.header.export_offset = f.tell()
            list(map(lambda x: x.write(f, self.version), self.exports))
            if self.version != ['4.15', '4.14']:
                self.header.depends_offset = f.tell()

            io_util.write_null_array(f, self.header.export_count)

            # write asset registry data
            self.header.asset_registry_data_offset = f.tell()
            io_util.write_null(f)

            # write preload dependencies
            self.header.preload_dependency_offset = f.tell()
            if self.version >= '4.16':
                io_util.write_int32_array(f, self.preload_dependency_ids)

            self.header.uasset_size = f.tell()
            self.header.bulk_offset = self.uexp_size + self.header.uasset_size
            self.header.name_count = len(self.name_list)

            # write header
            f.seek(0)
            self.header.write(f, self.version)

            # write exports
            f.seek(self.header.export_offset)
            offset = self.header.uasset_size
            for export in self.exports:
                export.update(export.size, offset)
                offset += export.size
            list(map(lambda x: x.write(f, self.version), self.exports))

            if not self.has_uexp():
                f.seek(self.header.uasset_size)
                f.write(self.uexp_bin)
                f.write(self.ubulk_bin)
                f.write(UassetFileSummary.TAG)

    def update_name_list(self, i, new_name):
        old_name = self.name_list[i]
        self.name_list[i] = new_name
        if self.version >= "4.12":
            self.hash_list[i] = generate_hash(new_name)

        def get_size(string):
            is_utf16 = not string.isascii()
            return (len(string) + 1) * (1 + is_utf16)

        # Update file size
        self.header.uasset_size += get_size(new_name) - get_size(old_name)

    def get_main_export(self):
        main_list = [exp for exp in self.exports if exp.is_main()]
        if len(main_list) != 1:
            raise RuntimeError("Failed to detect the main export object.")
        return main_list[0]

    def get_main_class_name(self):
        return self.get_main_export().class_name

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

    def get_texture_list(self):
        textures = []
        for exp in self.exports:
            if exp.is_texture():
                textures.append(exp.object)
        return textures

    def __get_io(self, file, bin, rb):
        if self.has_uexp():
            if rb:
                return open(file, 'rb')
            else:
                return open(file, 'wb')
        else:
            if rb:
                return io.BytesIO(bin)
            else:
                return io.BytesIO(b'')

    def get_uexp_io(self, rb=True):
        if self.uexp_io is None:
            self.uexp_io = self.__get_io(self.uexp_file, self.uexp_bin, rb)
        return self.uexp_io

    def get_ubulk_io(self, rb=True):
        if self.ubulk_io is None:
            self.ubulk_io = self.__get_io(self.ubulk_file, self.ubulk_bin, rb)
        return self.ubulk_io

    def close_uexp_io(self, rb=True):
        if self.uexp_io is None:
            return
        f = self.uexp_io
        self.uexp_size = f.tell()
        if self.has_uexp():
            if rb:
                io_util.check(f.read(4), UassetFileSummary.TAG, f)
            else:
                f.write(UassetFileSummary.TAG)
        else:
            if not rb:
                f.seek(0)
                self.uexp_bin = f.read()
        f.close()
        self.uexp_io = None

    def close_ubulk_io(self, rb=True):
        if self.ubulk_io is None:
            return
        f = self.ubulk_io
        if rb:
            size = io_util.get_size(f)
            io_util.check(size, f.tell())
        else:
            if not self.has_uexp():
                f.seek(0)
                self.ubulk_bin = f.read()
        f.close()
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

    def update_package_source(self, file_name=None, is_official=True):
        self.header.update_package_source(file_name=file_name, is_official=is_official)
