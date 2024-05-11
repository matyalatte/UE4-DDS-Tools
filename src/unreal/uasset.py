"""Classes for .uasset"""
import io
from io import IOBase
import os

from util import mkdir
from .import_export import ExportBase
from .utexture import Utexture
from .version import VersionInfo
from .archive import (ArchiveBase, ArchiveRead, ArchiveWrite,
                      Int32, Int32Array, Bytes, Buffer,
                      SerializableBase)
from .file_summary import (UassetFileSummary, ZenPackageSummary, ZenPackageSummary4)


UASSET_EXT = ["uasset", "uexp", "ubulk", "uptnl"]


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


class Uasset:
    TAG = b"\xC1\x83\x2A\x9E"  # Magic for uasset files
    TAG_SWAPPED = b"\x9E\x2A\x83\xC1"  # for big endian files
    TAG_UCAS = b"\x00\x00\x00\x00"  # ucas assets don't have tag and file version.

    def __init__(self, file_path: str, version: str = "ff7r", verbose=False):
        if not os.path.isfile(file_path):
            raise RuntimeError(f"Not File. ({file_path})")

        self.name_list = None
        self.imports = None
        self.exports = None
        self.data_resources = []
        self.texture = None
        self.io_dict = {}
        self.bin_dict = {}
        for k in UASSET_EXT[1:]:
            self.io_dict[k] = None
            self.bin_dict[k] = None
        self.file_name, ext = os.path.splitext(file_path)

        if not ext or ext[1:] not in UASSET_EXT:
            raise RuntimeError(f"Not Uasset. ({file_path})")
        uasset_file = self.file_name + ".uasset"
        print("load: " + uasset_file)

        self.version = VersionInfo(version)
        self.context_verbose = verbose
        self.context_valid = False
        self.is_ucas = False
        self.has_end_tag = True
        ar = ArchiveRead(open(uasset_file, "rb"), context=self.get_ar_context())
        self.serialize(ar)
        ar.close()
        self.read_export_objects(verbose=verbose)

    def get_ar_context(self):
        context = {
            "version": self.version,
            "verbose": self.context_verbose,
            "valid": self.context_valid,
            "is_ucas": self.is_ucas,
            "uasset": self
        }
        return context

    def print_name_map(self):
        print("Names")
        for i, name in zip(range(len(self.name_list)), self.name_list):
            print("  {}: {}".format(i, name))

    def serialize(self, ar: ArchiveBase):
        # read header
        self.check_tag(ar)
        if ar.is_reading:
            if not ar.is_ucas:
                ar << (UassetFileSummary, self, "header")
            elif ar.version >= "5.0":
                ar << (ZenPackageSummary, self, "header")
            else:
                ar << (ZenPackageSummary4, self, "header")
            if ar.verbose:
                self.header.print()
        else:
            self.header.seek_to_name_map(ar)

        # read name map
        self.name_list = self.header.serialize_name_map(ar, self.name_list)
        if ar.verbose:
            self.print_name_map()

        if ar.is_ucas and ar.version >= "5.0":
            if ar.version >= "5.2":
                # read bulk data map entries
                self.data_resources = self.header.serialize_data_resources(ar, self.data_resources)
            self.header.serialize_export_hashes(ar)

        # read imports
        self.imports = self.header.serialize_imports(ar, self.imports)
        if ar.is_reading:
            list(map(lambda x: x.name_import(self.imports, self.name_list), self.imports))
            if ar.verbose:
                print("Imports")
                list(map(lambda x: x.print(), self.imports))

        if ar.is_reading:
            # read exports
            self.exports = self.header.serialize_exports(ar, self.exports)
            list(map(lambda x: x.name_export(self.exports, self.imports, self.name_list), self.exports))
            if ar.verbose:
                print("Exports")
                list(map(lambda x: x.print(), self.exports))
                print(f"Main Export Class: {self.get_main_class_name()}")
        else:
            # skip exports part
            self.header.export_offset = ar.tell()
            self.header.skip_exports(ar, len(self.exports))
            if self.version not in ["4.15", "4.14"]:
                self.header.depends_offset = ar.tell()

        if ar.is_ucas:
            self.header.serialize_others(ar)
        else:
            # read depends map
            ar << (Int32Array, self, "depends_map", self.header.export_count)

            # write asset registry data
            ar.update_with_current_offset(self.header, "asset_registry_data_offset")
            ar == (Int32, 0, "asset_registry_data")

            # Preload dependencies (import and export ids that must be serialized before other exports)
            if self.has_uexp():
                ar.update_with_current_offset(self.header, "preload_dependency_offset")
                ar << (Int32Array, self, "preload_dependency_ids", self.header.preload_dependency_count)

            if ar.version >= "5.2":
                self.data_resources = self.header.serialize_data_resources(ar, self.data_resources)

        if ar.is_reading:
            ar.check(ar.tell(), self.get_size())
            if self.is_ucas:
                self.uexp_size = ar.size - self.header.uasset_size
                self.bin_dict["uexp"] = ar.read(self.uexp_size)
            elif not self.has_uexp():
                self.uexp_size = self.header.bulk_offset - self.header.uasset_size
                self.bin_dict["uexp"] = ar.read(self.uexp_size)
                self.bin_dict["ubulk"] = ar.read(ar.size - ar.tell() - 4)
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
            if self.is_ucas:
                if ar.version >= "5.3":
                    offset = 0
                else:
                    offset = self.header.cooked_header_size
            else:
                offset = self.header.uasset_size
            for export in self.exports:
                export.update(export.size, offset)
                offset += export.size
            self.exports = self.header.serialize_exports(ar, self.exports)

            if self.is_ucas:
                ar.seek(self.header.uasset_size)
                ar.write(self.bin_dict["uexp"])
            elif not self.has_uexp():
                ar.seek(self.header.uasset_size)
                ar.write(self.bin_dict["uexp"])
                ar.write(self.bin_dict["ubulk"])
                ar.write(self.header.tag)

    def check_tag(self, ar: ArchiveBase):
        if ar.is_reading:
            self.tag = ar.read(4)
            ar.seek(0)
        if self.tag == Uasset.TAG:
            ar.endian = "little"
            self.is_ucas = False
        elif self.tag == Uasset.TAG_SWAPPED:
            ar.endian = "big"
            self.is_ucas = False
        else:
            if ar.version <= "4.24":
                raise ar.raise_error(f"Invalid tag detected. ({self.tag})")
            elif ar.version >= "5.0":
                if self.tag != b"\x00\x00\x00\x00" and self.tag != b"\x01\x00\x00\x00":
                    raise ar.raise_error(f"Invalid tag detected. ({self.tag})")
            ar.endian = "little"
            self.is_ucas = True
        ar.update_context(self.get_ar_context())

    def read_export_objects(self, verbose=False):
        uexp_io = self.get_io(ext="uexp", rb=True)
        for exp in self.exports:
            if verbose:
                print(f"{exp.name}: (offset: {uexp_io.tell()})")
            if exp.is_texture():
                exp.object = Utexture(self, class_name=exp.class_name)
            else:
                exp.object = Uunknown(self, exp.size)
            exp.object.serialize(uexp_io)
            uexp_io.check(exp.object.uexp_size, exp.size)
        self.close_all_io(rb=True)

    def write_export_objects(self):
        if self.has_textures():
            self.data_resources.clear()
        uexp_io = self.get_io(ext="uexp", rb=False)
        for exp in self.exports:
            exp.object.serialize(uexp_io)
            offset = uexp_io.tell()
            exp.update(exp.object.uexp_size, offset)
        self.uexp_size = uexp_io.tell()
        for exp in self.exports:
            if exp.is_texture():
                exp.object.rewrite_offset_data()
        self.close_all_io(rb=False)

    def save(self, file: str, valid=False):
        folder = os.path.dirname(file)
        if folder not in [".", ""] and not os.path.exists(folder):
            mkdir(folder)

        self.file_name, ext = os.path.splitext(file)
        if ext[1:] not in UASSET_EXT:
            raise RuntimeError(f"Not Uasset. ({file})")

        uasset_file = self.file_name + ".uasset"
        print("save :" + uasset_file)

        self.context_verbose = False
        self.context_valid = valid
        self.write_export_objects()

        ar = ArchiveWrite(open(uasset_file, "wb"), context=self.get_ar_context())

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
        diff = get_size(new_name) - get_size(old_name)
        self.header.inc_file_size(diff)

    def get_main_export(self) -> ExportBase:
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
        return self.is_ucas or self.version >= "4.16" and (self.header.preload_dependency_count >= 0)

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

    def __get_io_base(self, file: str, bin: bytes, rb: bool) -> IOBase:
        if (self.is_ucas and file.endswith("uexp")) or not self.has_uexp():
            opened_io = io.BytesIO(bin if rb else b"")
        else:
            opened_io = open(file, "rb" if rb else "wb")

        if rb:
            return ArchiveRead(opened_io, context=self.get_ar_context())
        else:
            return ArchiveWrite(opened_io, context=self.get_ar_context())

    def get_io(self, ext="uexp", rb=True) -> IOBase:
        if ext not in self.io_dict or self.io_dict[ext] is None:
            self.io_dict[ext] = self.__get_io_base(f"{self.file_name}.{ext}", self.bin_dict[ext], rb)
        return self.io_dict[ext]

    def __close_io(self, ext="uexp", rb=True):
        if ext not in self.io_dict or self.io_dict[ext] is None:
            return
        ar = self.io_dict[ext]
        if ext == "uexp":
            self.uexp_size = ar.tell()
            if self.has_end_tag and ((self.has_uexp() and not ar.is_ucas) or ar.version >= "5.3"):
                if rb:
                    if ar.is_eof():
                        self.has_end_tag = False
                    else:
                        ar.check(ar.read(4), Uasset.TAG)
                else:
                    ar.write(Uasset.TAG)
        else:
            if rb:
                ar.check(ar.tell(), ar.size)
        if not rb and ((self.is_ucas and ext == "uexp") or not self.has_uexp()):
            ar.seek(0)
            self.bin_dict[ext] = ar.read()
        ar.close()
        self.io_dict[ext] = None

    def close_all_io(self, rb=True):
        for ext in UASSET_EXT[1:]:
            self.__close_io(ext=ext, rb=rb)

    def get_size(self):
        return self.header.uasset_size

    def get_uexp_size(self):
        return self.uexp_size

    def update_package_source(self, file_name=None, is_official=True):
        self.header.update_package_source(file_name=file_name, is_official=is_official)
