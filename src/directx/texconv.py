"""Texture converter.

Notes:
    You need to build dll from https://github.com/matyalatte/Texconv-Custom-DLL.
    And put the dll in the same directory as texconv.py.
"""
import ctypes
import os
import shutil
import tempfile

from .dds import DDS, DDSHeader, is_hdr
from .dxgi_format import DXGI_FORMAT
from util import mkdir, get_os_name, is_windows, is_mac, is_linux


class Texconv:
    """Texture converter."""
    def __init__(self, dll_path=None, com_initialized=False):
        self.load_dll(dll_path=dll_path, com_initialized=com_initialized)

    def load_dll(self, dll_path=None, com_initialized=False):
        if dll_path is None:
            file_path = os.path.realpath(__file__)
            if is_windows():
                dll_name = "texconv.dll"
            elif is_mac():
                dll_name = "libtexconv.dylib"
            elif is_linux():
                dll_name = "libtexconv.so"
            else:
                raise RuntimeError(f"This OS ({get_os_name()}) is unsupported.")
            dirname = os.path.dirname(file_path)
            dll_path = os.path.join(dirname, dll_name)
            dll_path2 = os.path.join(os.path.dirname(dirname), dll_name)  # allow ../texconv.dll

        if not os.path.exists(dll_path):
            if os.path.exists(dll_path2):
                dll_path = dll_path2
            else:
                raise RuntimeError(f"texconv not found. ({dll_path})")

        self.dll = ctypes.cdll.LoadLibrary(dll_path)
        self.com_initialized = com_initialized

    def convert_dds_to(self, file: str, out=None, fmt="tga",
                       cubemap_layout="h-cross", invert_normals=False, verbose=True):
        """Convert dds to non-dds."""
        dds_header = DDSHeader.read_from_file(file)

        if (dds_header.dxgi_format.value > DXGI_FORMAT.get_max_canonical() or
                dds_header.dxgi_format == DXGI_FORMAT.UNKNOWN):
            raise RuntimeError(
                f"DDS converter does NOT support {dds_header.get_format_as_str()}.")

        if dds_header.is_3d() or dds_header.is_array():
            dds = DDS.load(file)
            dds_list = dds.get_disassembled_dds_list()
            base_name = os.path.basename(file)
            with tempfile.TemporaryDirectory() as temp_dir:
                for new_dds, i in zip(dds_list, range(len(dds_list))):
                    new_name = ".".join(base_name.split(".")[:-1]) + f"-{i}.dds"
                    new_path = os.path.join(temp_dir, new_name)
                    new_dds.save(new_path)
                    name = self.convert_dds_to(new_path, out=out, fmt=fmt, cubemap_layout=cubemap_layout,
                                               invert_normals=invert_normals, verbose=verbose)
            return name

        if verbose:
            print(f"DXGI_FORMAT: {dds_header.get_format_as_str()}")

        args = []

        if dds_header.is_hdr():
            ext = "hdr"
            if fmt == "tga":
                fmt = ext
            if not dds_header.convertible_to_hdr():
                args += ["-f", "fp32"]
        else:
            ext = "tga"
            if not dds_header.convertible_to_tga():
                args += ["-f", "rgba"]

        if dds_header.is_int():
            msg = f"Int format detected. ({dds_header.get_format_as_str()})\n It might not be converted correctly."
            print(msg)

        args2 = ["-ft", fmt]

        if dds_header.is_normals():
            args2 += ["-reconstructz"]
            if invert_normals:
                args2 += ["-inverty"]

        if dds_header.is_cube():
            name = os.path.join(out, os.path.basename(file))
            name = ".".join(name.split(".")[:-1] + [fmt])
            temp = ".".join(file.split(".")[:-1] + [ext])
            self.__cube_to_image(file, temp, args, cubemap_layout=cubemap_layout, verbose=verbose)
            if fmt == ext:
                mkdir(os.path.dirname(name))
                shutil.copy(temp, name)
            else:
                self.__texconv(temp, args2, out=out, verbose=verbose)
        else:
            out = self.__texconv(file, args + args2, out=out, verbose=verbose)
            name = os.path.join(out, os.path.basename(file))
            name = ".".join(name.split(".")[:-1] + [fmt])
        return name

    def convert_to_dds(self, file: str, dxgi_format: DXGI_FORMAT, out=None,
                       invert_normals=False, no_mip=False,
                       image_filter="LINEAR",
                       export_as_cubemap=False,
                       cubemap_layout="h-cross",
                       verbose=True, allow_slow_codec=False):
        """Convert texture to dds."""

        dds_fmt = dxgi_format.name

        if ("BC6" in dds_fmt or "BC7" in dds_fmt) and (not is_windows()) and (not allow_slow_codec):
            raise RuntimeError(f"Can NOT use CPU codec for {dds_fmt}. Or enable the 'Allow Slow Codec' option.")
        if (dxgi_format.value > DXGI_FORMAT.get_max_canonical() or
                dxgi_format == DXGI_FORMAT.UNKNOWN):
            raise RuntimeError(
                f"DDS converter does NOT support {dds_fmt}.")

        if not DXGI_FORMAT.is_valid_format(dds_fmt):
            raise RuntimeError(f"Not DXGI format. ({dds_fmt})")

        if verbose:
            print(f"DXGI_FORMAT: {dds_fmt}")

        base_name = os.path.basename(file)
        base_name = ".".join(base_name.split(".")[:-1] + ["dds"])

        args = ["-f", dds_fmt]
        if no_mip:
            args += ["-m", "1"]
        if image_filter.upper() != "LINEAR":
            args += ["-if", image_filter.upper()]

        if ("BC5" in dds_fmt or dds_fmt == "R8G8_UNORM") and invert_normals:
            args += ["-inverty"]

        if export_as_cubemap:
            if is_hdr(dds_fmt):
                temp_args = ["-f", "fp32"]
            else:
                temp_args = ["-f", "rgba"]
            with tempfile.TemporaryDirectory() as temp_dir:
                temp = os.path.join(temp_dir, base_name)
                self.__image_to_cube(file, temp, temp_args, cubemap_layout=cubemap_layout, verbose=verbose)
                out = self.__texconv(temp, args, out=out, verbose=verbose, allow_slow_codec=allow_slow_codec)
        else:
            out = self.__texconv(file, args, out=out, verbose=verbose, allow_slow_codec=allow_slow_codec)
        name = os.path.join(out, base_name)
        return name

    def convert_nondds(self, file: str, out=None, fmt="tga", verbose=True):
        """Convert non-dds to non-dds."""
        out = self.__texconv(file, ["-ft", fmt], out=out, verbose=verbose)
        name = os.path.join(out, os.path.basename(file))
        name = ".".join(name.split(".")[:-1] + [fmt])
        return name

    def __texconv(self, file: str, args: list[str],
                  out=None, verbose=True, allow_slow_codec=False):
        """Run texconv."""
        if out is not None and isinstance(out, str):
            args += ["-o", out]
        else:
            out = "."

        if out not in [".", ""] and not os.path.exists(out):
            mkdir(out)

        args += ["-y", "--", os.path.normpath(file)]

        args_p = [ctypes.c_wchar_p(arg) for arg in args]
        args_p = (ctypes.c_wchar_p*len(args_p))(*args_p)
        err_buf = ctypes.create_unicode_buffer(512)
        result = self.dll.texconv(len(args), args_p, verbose, not self.com_initialized, allow_slow_codec, err_buf, 512)
        self.com_initialized = True

        if result != 0:
            raise RuntimeError(err_buf.value)

        return out

    def __cube_to_image(self, file: str, new_file: str, args: list[str],
                        cubemap_layout="h-cross", verbose=True):
        """Generate an image from a cubemap with texassemble."""
        if cubemap_layout.endswith("-fnz"):
            cubemap_layout = cubemap_layout[:-4]
        args = [cubemap_layout] + args
        self.__texassemble(file, new_file, args, verbose=verbose)

    def __image_to_cube(self, file: str, new_file: str, args: list[str],
                        cubemap_layout="h-cross", verbose=True):
        """Generate a cubemap from an image with texassemble."""
        cmd = "cube-from-" + cubemap_layout[0] + cubemap_layout[2]
        args = [cmd] + args
        self.__texassemble(file, new_file, args, verbose=verbose)

    def __texassemble(self, file: str, new_file: str, args: list[str], verbose=True):
        """Run texassemble."""
        out = os.path.dirname(new_file)
        if out not in [".", ""] and not os.path.exists(out):
            mkdir(out)
        args += ["-y", "-o", new_file, "--", file]

        args_p = [ctypes.c_wchar_p(arg) for arg in args]
        args_p = (ctypes.c_wchar_p*len(args_p))(*args_p)
        err_buf = ctypes.create_unicode_buffer(512)
        result = self.dll.texassemble(len(args), args_p, verbose, not self.com_initialized, err_buf, 512)
        self.com_initialized = True
        if result != 0:
            raise RuntimeError(err_buf.value)
