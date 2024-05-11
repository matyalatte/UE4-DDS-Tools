from enum import IntEnum
import os

from .crc import strcrc_deprecated
from .archive import (ArchiveBase,
                      Uint32, Uint64, Int32, Int64, Int32Array,
                      Bytes, Buffer, String, SerializableBase)
from .import_export import (NameBase, ImportBase, ExportBase,
                            UassetName, UassetImport, UassetExport,
                            ZenName, ZenImport, ZenExport)
from .data_resource import DataResourceBase, UassetDataResource, BulkDataMapEntry


class PackageFlags(IntEnum):
    PKG_UnversionedProperties = 0x2000   # Uses unversioned property serialization
    PKG_FilterEditorOnly = 0x80000000  # Package has editor-only data filtered out


class FileSummaryBase(SerializableBase):
    """Info for .uasset file (FPackageFileSummary)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Private/UObject/PackageFileSummary.cpp
    """

    def serialize(self, ar: ArchiveBase):
        self.file_name = ar.name

    def serialize_version_info(self, ar: ArchiveBase):
        """
        Version info. But most assets have zeros for these variables. (unversioning)
        So, we can't get UE version from them.
        - LegacyUE3Version
        - FileVersionUE.FileVersionUE4
        - FileVersionUE.FileVersionUE5 (Added at 5.0)
        - FileVersionLicenseeUE
        - CustomVersionContainer
        """
        ar << (Bytes, self, "version_info", 16 + 4 * (ar.version >= "5.0"))

    def serialize_name_map(self, ar: ArchiveBase, name_list: list[NameBase]) -> list[NameBase]:
        pass

    def serialize_imports(self, ar: ArchiveBase, imports: list[ImportBase]) -> list[ImportBase]:
        pass

    def serialize_exports(self, ar: ArchiveBase, exports: list[ExportBase]) -> list[ExportBase]:
        pass

    def seek_to_name_map(self, ar: ArchiveBase):
        ar.seek(self.name_map_offset)

    def skip_exports(self, ar: ArchiveBase, count: int):
        pass

    def serialize_data_resources(self, ar: ArchiveBase, imports: list[DataResourceBase]) -> list[DataResourceBase]:
        pass

    def print(self):
        pass

    def is_unversioned(self):
        return (self.pkg_flags & PackageFlags.PKG_UnversionedProperties) > 0

    def update_package_source(self, file_name=None, is_official=True):
        pass

    def inc_file_size(self, diff: int):
        self.uasset_size += diff


class UassetFileSummary(FileSummaryBase):
    """Info for .uasset file (FPackageFileSummary)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Private/UObject/PackageFileSummary.cpp
    """

    def serialize(self, ar: ArchiveBase):
        super().serialize(ar)

        ar << (Bytes, self, "tag", 4)

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
            -8 + (ar.version <= "4.6") * 2 + (ar.version <= "4.9")
            + (ar.version <= "4.13") + (ar.version <= "4.27")
        )
        ar == (Int32, expected_version, "header.file_version")

        self.serialize_version_info(ar)

        ar << (Int32, self, "uasset_size")  # TotalHeaderSize
        ar << (String, self, "package_name")

        # PackageFlags
        ar << (Uint32, self, "pkg_flags")
        if ar.is_reading:
            ar.check(self.pkg_flags & PackageFlags.PKG_FilterEditorOnly > 0, True,
                     msg="Unsupported file format detected. (PKG_FilterEditorOnlyitorOnly is false.)")

        # Name table
        ar << (Int32, self, "name_count")
        ar << (Int32, self, "name_map_offset")

        if ar.version >= "5.1":
            # SoftObjectPaths
            ar == (Int32, 0, "soft_object_count")
            if ar.is_writing:
                self.soft_object_offset = self.import_offset
            ar << (Int32, self, "soft_object_offset")

        if ar.version >= "4.9":
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

        if ar.version >= "4.4" and ar.version <= "4.14":
            # StringAssetReferencesCount
            ar == (Int32, 0, "string_asset_count")
            if ar.is_writing:
                self.string_asset_offset = self.asset_registry_data_offset
            ar << (Int32, self, "string_asset_offset")
        elif ar.version >= "4.15":
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
        ar << (Bytes, self, "empty_engine_version", 14 * (1 + (ar.version >= "4.8")))

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

        if ar.version <= "4.13":
            ar == (Int32, 0, "num_texture_allocations")
        ar << (Int32, self, "asset_registry_data_offset")
        ar << (Int32, self, "bulk_offset")  # .uasset + .uexp - 4 (BulkDataStartOffset)

        # WorldTileInfoDataOffset
        ar == (Int32, 0, "world_tile_info_offset")

        # ChunkIDs (zero length array), ChunkID
        ar == (Int32Array, [0, 0], "ChunkID", 2)

        if ar.version <= "4.13":
            return

        # PreloadDependency
        ar << (Int32, self, "preload_dependency_count")
        ar << (Int32, self, "preload_dependency_offset")

        if ar.version <= "4.27":
            return

        # Number of names that are referenced from serialized export data
        ar << (Int32, self, "referenced_names_count")

        # Location into the file on disk for the payload table of contents data
        ar << (Int64, self, "payload_toc_offset")

        if ar.version <= "5.1":
            return

        # Location into the file of the data resource
        ar << (Int32, self, "data_resource_offset")

    def serialize_name_map(self, ar: ArchiveBase, name_list: list[UassetName]) -> list[UassetName]:
        if ar.is_reading:
            name_list = [UassetName() for i in range(self.name_count)]
        else:
            self.name_count = len(name_list)
        list(map(lambda x: x.serialize(ar), name_list))
        return name_list

    def serialize_imports(self, ar: ArchiveBase, imports: list[UassetImport]) -> list[UassetImport]:
        ar.update_with_current_offset(self, "import_offset")
        if ar.is_reading:
            imports = [UassetImport() for i in range(self.import_count)]
        else:
            self.import_count = len(imports)
        list(map(lambda x: x.serialize(ar), imports))
        return imports

    def serialize_exports(self, ar: ArchiveBase, exports: list[UassetExport]) -> list[UassetExport]:
        ar.update_with_current_offset(self, "export_offset")
        if ar.is_reading:
            exports = [UassetExport() for i in range(self.export_count)]
        else:
            self.export_count = len(exports)
        list(map(lambda x: x.serialize(ar), exports))
        return exports

    def skip_exports(self, ar: ArchiveBase, count: int):
        ar.seek(UassetExport.get_struct_size(ar.version) * count, 1)

    def serialize_data_resources(self, ar: ArchiveBase,
                                 data_resources: list[UassetDataResource]) -> list[UassetDataResource]:
        if ar.is_reading:
            if self.data_resource_offset == -1:
                return []
            ar.update_with_current_offset(self, "data_resource_offset")
        else:
            if len(data_resources) == 0:
                self.data_resource_offset = -1
                return []
            self.data_resource_count = len(data_resources)

        ar == (Int32, 1, "deta_resource_version")
        ar << (Int32, self, "data_resource_count")

        if ar.is_reading:
            data_resources = [UassetDataResource() for i in range(self.data_resource_count)]
        list(map(lambda x: x.serialize(ar), data_resources))
        return data_resources

    def print(self):
        print("File Summary")
        print(f"  file size: {self.uasset_size}")
        print(f"  number of names: {self.name_count}")
        print("  name directory offset: 193")
        print(f"  number of exports: {self.export_count}")
        print(f"  export directory offset: {self.export_offset}")
        print(f"  number of imports: {self.import_count}")
        print(f"  import directory offset: {self.import_offset}")
        print(f"  depends offset: {self.depends_offset}")
        print(f"  file length (uasset+uexp-4): {self.bulk_offset}")
        print(f"  official asset: {self.is_official()}")
        print(f"  unversioned: {self.is_unversioned()}")

    def update_package_source(self, file_name=None, is_official=True):
        if file_name is not None:
            self.file_name = file_name
        if is_official:
            crc = strcrc_deprecated("".join(os.path.basename(self.file_name).split(".")[:-1]))
        else:
            # UE doesn't care this value. So, we can embed any four bytes here.
            crc = int.from_bytes(b"MOD ", "little")
        self.package_source = crc

    def is_official(self):
        crc = strcrc_deprecated("".join(os.path.basename(self.file_name).split(".")[:-1]))
        return self.package_source == crc


class ZenPackageSummary(FileSummaryBase):
    """Info for ucas assets (FZenPackageSummary)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Public/Serialization/AsyncLoading2.h
    """

    def serialize(self, ar: ArchiveBase):
        super().serialize(ar)

        ar << (Uint32, self, "has_version_info")
        ar << (Uint32, self, "uasset_size")
        ar << (Uint32, self, "package_name_id")
        ar << (Uint32, self, "package_name_number")
        ar << (Uint32, self, "pkg_flags")
        ar << (Uint32, self, "cooked_header_size")  # uasset_size when using UassetFileSummary
        ar << (Int32, self, "export_hashes_offset")
        ar << (Int32, self, "import_offset")
        ar << (Int32, self, "export_offset")
        ar << (Int32, self, "export_bundle_entries_offset")
        if ar.version >= "5.3":
            ar << (Int32, self, "dependency_bundle_headers_offset")
            ar << (Int32, self, "dependency_bundle_entries_offset")
            ar << (Int32, self, "imported_package_names_offset")
        else:
            ar << (Int32, self, "graph_data_offset")
        if self.has_version_info:
            self.serialize_version_info(ar)
        self.name_map_offset = ar.tell()

    def print(self):
        print("File Summary")
        print(f"  file size: {self.uasset_size}")
        print(f"  cooked header size: {self.cooked_header_size}")
        print(f"  name directory offset: {self.name_map_offset}")
        print(f"  import directory offset: {self.import_offset}")
        print(f"  export directory offset: {self.export_offset}")
        print(f"  unversioned: {self.is_unversioned()}")

    def serialize_name_map(self, ar: ArchiveBase, name_list: list[ZenName]) -> list[ZenName]:
        if ar.is_writing:
            self.name_count = len(name_list)
            self.name_map_size = sum(len(str(n)) for n in name_list)
        ar << (Uint32, self, "name_count")
        ar << (Uint32, self, "name_map_size")
        ar == (Uint64, 0xC1640000, "hash_version")
        if ar.is_reading:
            ar.check_buffer_size(self.name_map_size)
            name_list = [ZenName() for i in range(self.name_count)]
        list(map(lambda x: x.serialize_hash(ar), name_list))
        list(map(lambda x: x.serialize_head(ar), name_list))
        list(map(lambda x: x.serialize_string(ar), name_list))
        if ar.version >= "5.4":
            if ar.is_writing and self.align_name_map:
                self.pad_size = (8 - (ar.tell() % 8)) % 8
            ar << (Uint64, self, "pad_size")
            ar == (Buffer, b"\x00" * self.pad_size, "pad", self.pad_size)
            if ar.is_reading:
                # Some assets don't use alignment somehow.
                self.align_name_map = ar.tell() % 8 == 0

        return name_list

    def serialize_data_resources(self, ar: ArchiveBase,
                                 data_resources: list[BulkDataMapEntry]) -> list[BulkDataMapEntry]:
        struct_size = BulkDataMapEntry.get_struct_size(ar)

        if ar.is_writing:
            self.bulk_data_map_size = len(data_resources) * struct_size

        ar << (Int64, self, "bulk_data_map_size")

        if ar.is_reading:
            ar.check_buffer_size(self.bulk_data_map_size)
            data_resource_count = self.bulk_data_map_size // struct_size
            data_resources = [BulkDataMapEntry() for i in range(data_resource_count)]

        list(map(lambda x: x.serialize(ar), data_resources))
        return data_resources

    def serialize_export_hashes(self, ar: ArchiveBase):
        size = self.import_offset - self.export_hashes_offset
        ar.update_with_current_offset(self, "export_hashes_offset")
        ar << (Buffer, self, "export_hashes", size)

    def serialize_imports(self, ar: ArchiveBase, imports: list[ZenImport]) -> list[ZenImport]:
        ar.update_with_current_offset(self, "import_offset")
        if ar.is_reading:
            struct_size = ZenImport.get_struct_size(ar)
            import_count = (self.export_offset - self.import_offset) // struct_size
            imports = [ZenImport() for i in range(import_count)]
        list(map(lambda x: x.serialize(ar), imports))
        return imports

    def serialize_exports(self, ar: ArchiveBase, exports: list[ZenExport]) -> list[ZenExport]:
        ar.update_with_current_offset(self, "export_offset")
        if ar.is_reading:
            struct_size = ZenExport.get_struct_size(ar)
            export_count = (self.export_bundle_entries_offset - self.export_offset) // struct_size
            exports = [ZenExport() for i in range(export_count)]
        list(map(lambda x: x.serialize(ar), exports))
        return exports

    def skip_exports(self, ar: ArchiveBase, count: int):
        ar.seek(ZenExport.get_struct_size(ar.version) * count, 1)

    def serialize_others(self, ar: ArchiveBase):
        if ar.version >= "5.3":
            export_bundle_entries_size = (self.dependency_bundle_headers_offset
                                          - self.export_bundle_entries_offset)
            dependency_bundle_headers_size = (self.dependency_bundle_entries_offset
                                              - self.dependency_bundle_headers_offset)
            dependency_bundle_entries_size = (self.imported_package_names_offset
                                              - self.dependency_bundle_entries_offset)
            imported_package_names_size = self.uasset_size - self.imported_package_names_offset
            ar.update_with_current_offset(self, "export_bundle_entries_offset")
            ar << (Buffer, self, "export_bundle_entries", export_bundle_entries_size)
            ar.update_with_current_offset(self, "dependency_bundle_headers_offset")
            ar << (Buffer, self, "dependency_bundle_headers", dependency_bundle_headers_size)
            ar.update_with_current_offset(self, "dependency_bundle_entries_offset")
            ar << (Buffer, self, "dependency_bundle_entries", dependency_bundle_entries_size)
            ar.update_with_current_offset(self, "imported_package_names_offset")
            ar << (Buffer, self, "imported_package_names", imported_package_names_size)
        else:
            export_bundle_entries_size = self.graph_data_offset - self.export_bundle_entries_offset
            graph_data_size = self.uasset_size - self.graph_data_offset
            ar.update_with_current_offset(self, "export_bundle_entries_offset")
            ar << (Buffer, self, "export_bundle_entries", export_bundle_entries_size)
            ar.update_with_current_offset(self, "graph_data_offset")
            ar << (Buffer, self, "graph_data", graph_data_size)

    def inc_file_size(self, diff: int):
        self.uasset_size += diff
        self.cooked_header_size += diff


class ZenPackageSummary4(ZenPackageSummary):
    """Zen package summary for UE4 (FPackageSummary)

    Notes:
        UnrealEngine/Engine/Source/Runtime/CoreUObject/Public/Serialization/AsyncLoading2.h
    """

    def serialize(self, ar: ArchiveBase):
        FileSummaryBase.serialize(self, ar)

        ar << (Uint32, self, "name_id")
        ar << (Uint32, self, "name_number")
        ar << (Uint32, self, "source_name_id")
        ar << (Uint32, self, "source_name_number")
        ar << (Uint32, self, "pkg_flags")
        ar << (Uint32, self, "cooked_header_size")  # uasset_size when using UassetFileSummary
        ar << (Int32, self, "name_map_offset")
        ar << (Int32, self, "name_map_size")
        ar << (Int32, self, "name_hashes_offset")
        ar << (Int32, self, "name_hashes_size")
        ar << (Int32, self, "import_offset")
        ar << (Int32, self, "export_offset")
        ar << (Int32, self, "export_bundle_entries_offset")
        ar << (Int32, self, "graph_data_offset")
        ar << (Int32, self, "graph_data_size")
        ar == (Int32, 0, "pad")
        self.uasset_size = self.graph_data_offset + self.graph_data_size

    def print(self):
        print("File Summary")
        print(f"  file size: {self.uasset_size}")
        print(f"  cooked header size: {self.cooked_header_size}")
        print(f"  name directory offset: {self.name_map_offset}")
        print(f"  name hashes offset: {self.name_hashes_offset}")
        print(f"  name hashes size: {self.name_hashes_size}")
        print(f"  import directory offset: {self.import_offset}")
        print(f"  export directory offset: {self.export_offset}")
        print(f"  unversioned: {self.is_unversioned()}")

    def serialize_name_map(self, ar: ArchiveBase, name_list: list[ZenName]) -> list[ZenName]:
        ar.update_with_current_offset(self, "name_map_offset")
        if ar.is_reading:
            self.name_count = (self.name_hashes_size - 8) // 8
            ar.check_buffer_size(self.name_map_size)
            name_list = [ZenName() for i in range(self.name_count)]

        list(map(lambda x: x.serialize_head_and_string(ar), name_list))

        ar.update_with_current_offset(self, "name_map_size", base=self.name_map_offset)
        ar.align(8)

        ar.update_with_current_offset(self, "name_hashes_offset")
        ar == (Uint64, 0xC1640000, "hash_version")
        list(map(lambda x: x.serialize_hash(ar), name_list))

        ar.update_with_current_offset(self, "name_hashes_size", base=self.name_hashes_offset)
        ar.check(self.name_hashes_size, len(name_list) * 8 + 8)
        return name_list

    def serialize_others(self, ar: ArchiveBase):
        export_bundle_entries_size = self.graph_data_offset - self.export_bundle_entries_offset
        ar.update_with_current_offset(self, "export_bundle_entries_offset")
        ar << (Buffer, self, "export_bundle_entries", export_bundle_entries_size)
        ar.update_with_current_offset(self, "graph_data_offset")
        ar << (Buffer, self, "graph_data", self.graph_data_size)
