"""Main file for UE4-DDS-Tools."""
# std libs
import argparse
import json
import os
import time
from contextlib import redirect_stdout
import concurrent.futures
import functools

# my scripts
from util import (compare, get_ext, get_temp_dir,
                  get_file_list, get_base_folder, remove_quotes)
from unreal.uasset import Uasset, UASSET_EXT
from directx.dds import DDS
from directx.dxgi_format import DXGI_FORMAT
from directx.texconv import Texconv, is_windows

TOOL_VERSION = "0.5.5"

# UE version: 4.0 ~ 5.3, ff7r, borderlands3
UE_VERSIONS = ["4." + str(i) for i in range(28)] + ["5." + str(i) for i in range(4)] + ["ff7r", "borderlands3"]

# Supported file extensions.
TEXTURES = ["dds", "tga", "hdr"]
if is_windows():
    TEXTURES += ["bmp", "jpg", "png"]

# Supported image filters.
IMAGE_FILTERS = ["point", "linear", "cubic"]


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="uasset, texture file, or folder")
    parser.add_argument("texture", nargs="?", help="texture file for injection mode.")
    parser.add_argument("--save_folder", default="output", type=str, help="output folder")
    parser.add_argument("--mode", default="inject", type=str,
                        help="valid, parse, inject, export, remove_mipmaps, check, convert, and copy are available.")
    parser.add_argument("--version", default=None, type=str,
                        help="UE version. it will overwrite the argment in config.json.")
    parser.add_argument("--export_as", default="dds", type=str,
                        help="format for export mode. dds, tga, png, jpg, and bmp are available.")
    parser.add_argument("--convert_to", default="tga", type=str,
                        help=("format for convert mode."
                              " tga, hdr, png, jpg, bmp, and DXGI formats (e.g. BC1_UNORM) are available."))
    parser.add_argument("--no_mipmaps", action="store_true",
                        help="force no mips to dds and uasset.")
    parser.add_argument("--force_uncompressed", action="store_true",
                        help="use uncompressed format for compressed texture assets.")
    parser.add_argument("--disable_tempfile", action="store_true",
                        help="store temporary files in the tool's directory.")
    parser.add_argument("--skip_non_texture", action="store_true",
                        help="disable errors about non-texture assets.")
    parser.add_argument("--image_filter", default="linear", type=str,
                        help=("image filter for mip generation."
                              " point, linear, and cubic are available."))
    parser.add_argument("--save_detected_version", action="store_true",
                        help="save detected version for batch file methods. this is an option for check mode.")
    parser.add_argument("--max_workers", default=-1, type=int,
                        help=("The number of workers for multiprocessing."
                              " If -1, it will default to the number of processors on the machine."))
    return parser.parse_args()


def get_config():
    json_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(json_path):
        return {}
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    json_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def stdout_wrapper(func):
    """Stdout wrapper to order the outputs in multiprocessing."""
    @functools.wraps(func)
    def caller(*args, **kwargs):
        from io import StringIO
        import sys
        default_stdout = sys.stdout
        sys.stdout = StringIO()  # Store the outputs in a string

        def flush(stdout):
            """Print outputs to the true stdout."""
            stdout.seek(0)
            print(stdout.read()[:-1], file=default_stdout, flush=True)
            sys.stdout = default_stdout

        try:
            response = func(*args, **kwargs)
        except Exception as e:
            flush(sys.stdout)  # Print outputs after execution
            raise e
        flush(sys.stdout)  # Print outputs after execution
        return response
    return caller


@stdout_wrapper
def parse(folder, file, args, texture_file=None):
    """Parse mode (parse dds or uasset)"""
    file = os.path.join(folder, file)
    if get_ext(file) == "dds":
        DDS.load(file, verbose=True)
    else:
        Uasset(file, version=args.version, verbose=True)


@stdout_wrapper
def valid(folder, file, args, version=None, texture_file=None):
    """Valid mode (check if the tool can read and write a file correctly.)"""
    if version is None:
        version = args.version

    with get_temp_dir(disable_tempfile=args.disable_tempfile) as temp_dir:
        src_file = os.path.join(folder, file)
        new_file = os.path.join(temp_dir, file)

        if get_ext(file) == "dds":
            # read and write dds
            dds = DDS.load(src_file)
            dds.save(new_file)

            # compare files
            compare(src_file, new_file)

        else:
            # read and write uasset
            asset = Uasset(src_file, version=version, verbose=True)
            old_name = asset.file_name
            asset.save(new_file, valid=True)
            new_name = asset.file_name
            # compare files
            for ext in UASSET_EXT:
                if (os.path.exists(f"{old_name}.{ext}") and (asset.has_textures() or ext == "uasset")):
                    compare(f"{old_name}.{ext}", f"{new_name}.{ext}")


def search_texture_file(file_base, ext_list, index=None, index2=None):
    """Sarch a texture file for injection mode."""
    if index is not None:
        file_base += index
    for ext in ext_list:
        file = file_base
        if index2 is not None and ext != "dds":
            file += index2
        file = ".".join([file, ext])
        if os.path.exists(file):
            return file
    raise RuntimeError(f"Texture file not found. ({file_base})")


@stdout_wrapper
def inject(folder, file, args, texture_file=None):
    """Inject mode (inject dds into the asset)"""

    # Read uasset
    uasset_file = os.path.join(folder, file)
    asset = Uasset(uasset_file, version=args.version)

    if not asset.has_textures():
        # Skip or raise an error for non-texture asset
        desc = f"(file: {uasset_file}, class: {asset.get_main_class_name()})"
        if args.skip_non_texture:
            print("Skipped a non-texture asset. " + desc)
            return
        raise RuntimeError("This uasset has no textures. " + desc)

    if texture_file is None:
        texture_file = args.texture
    file_base, ext = os.path.splitext(texture_file)
    ext = ext[1:].lower()
    if ext == "uasset":
        raise RuntimeError("Can NOT inject uasset file into another uasset file.")
    if ext not in TEXTURES:
        raise RuntimeError(f"Unsupported texture format. ({ext})")

    textures = asset.get_texture_list()
    ext_list = [ext] + TEXTURES
    if len(textures) == 1:
        if textures[0].is_empty():
            src_files = [None]
        else:
            index2 = "-0" if textures[0].is_array or textures[0].is_3d else None
            src_files = [search_texture_file(file_base, ext_list, index2=index2)]
    else:
        # Find other files for multiple textures
        splitted = file_base.split(".")
        if len(splitted) >= 2 and (splitted[-1] == "0" or splitted[-1] == "0-0"):
            file_base = ".".join(splitted[:-1])
        src_files = []
        for i, tex in zip(range(len(textures)), textures):
            if tex.is_empty():
                src_files.append(None)
            index = f".{i}"
            index2 = "-0" if tex.is_array or tex.is_3d else None
            src_files.append(search_texture_file(file_base, ext_list, index=index, index2=index2))

    if any([(src is not None) and (get_ext(src) != "dds") for src in src_files]):
        texconv = Texconv()

    for tex, src in zip(textures, src_files):
        if tex.is_empty():
            print("Skipped an empty texture.")
            continue

        if args.force_uncompressed:
            tex.to_uncompressed()
        elif "ASTC" in tex.dxgi_format.name:
            print("Warning: DDS converter doesn't support ASTC. "
                  "The texture will use an uncompressed format.")
            tex.to_uncompressed()

        # Get a image as a DDS object
        if get_ext(src) == "dds":
            dds = DDS.load(src)
        else:
            with get_temp_dir(disable_tempfile=args.disable_tempfile) as temp_dir:
                print(f"convert: {src}")
                if tex.is_array or tex.is_3d:
                    src_base, src_ext = os.path.splitext(src)
                    src_base = src_base[:-2]
                    i = 0
                    dds_list = []
                    while True:
                        src = f"{src_base}-{i}{src_ext}"
                        if not os.path.exists(src):
                            break
                        temp_dds = texconv.convert_to_dds(src, tex.dxgi_format,
                                                          out=temp_dir, export_as_cubemap=tex.is_cube,
                                                          no_mip=len(tex.mipmaps) <= 1 or args.no_mipmaps,
                                                          image_filter=args.image_filter,
                                                          allow_slow_codec=True, verbose=False)
                        dds_list.append(DDS.load(temp_dds))
                        i += 1
                    dds = DDS.assemble(dds_list, is_array=tex.is_array)
                else:
                    temp_dds = texconv.convert_to_dds(src, tex.dxgi_format,
                                                      out=temp_dir, export_as_cubemap=tex.is_cube,
                                                      no_mip=len(tex.mipmaps) <= 1 or args.no_mipmaps,
                                                      image_filter=args.image_filter,
                                                      allow_slow_codec=True, verbose=False)
                    dds = DDS.load(temp_dds)

        # inject the DDS
        tex.inject_dds(dds)
        if args.no_mipmaps:
            tex.remove_mipmaps()

    # Write uasset
    asset.update_package_source(is_official=False)
    new_file = os.path.join(args.save_folder, file)
    asset.save(new_file)


@stdout_wrapper
def export(folder, file, args, texture_file=None):
    """Export mode (export uasset as dds)"""
    src_file = os.path.join(folder, file)
    new_file = os.path.join(args.save_folder, file)
    new_dir = os.path.dirname(new_file)

    asset = Uasset(src_file, version=args.version)

    if not asset.has_textures():
        # Skip or raise an error for non-texture asset
        desc = f"(file: {src_file}, class: {asset.get_main_class_name()})"
        if args.skip_non_texture:
            print("Skipped a non-texture asset. " + desc)
            return
        raise RuntimeError("This uasset has no textures. " + desc)

    textures = asset.get_texture_list()
    has_multi = len(textures) > 1
    if args.export_as != "dds":
        texconv = Texconv()

    for tex, i in zip(textures, range(len(textures))):
        if tex.is_empty():
            print("Skipped an empty texture.")
            continue

        if has_multi:
            # Add indices for multiple textures
            file_name = os.path.splitext(new_file)[0] + f".{i}.dds"
        else:
            file_name = os.path.splitext(new_file)[0] + ".dds"

        if args.no_mipmaps:
            tex.remove_mipmaps()

        # Save texture
        dds = tex.get_dds()
        if args.export_as == "dds":
            dds.save(file_name)
        elif "ASTC" in dds.header.dxgi_format.name:
            print("Warning: DDS converter doesn't support ASTC. The texture will be exported as DDS.")
            dds.save(file_name)
        else:
            # Convert if the export format is not DDS
            with get_temp_dir(disable_tempfile=args.disable_tempfile) as temp_dir:
                temp_dds = os.path.join(temp_dir, os.path.basename(file_name))
                dds.save(temp_dds)
                converted_file = texconv.convert_dds_to(temp_dds, out=new_dir, fmt=args.export_as, verbose=False)
                print(f"convert to: {converted_file}")


@stdout_wrapper
def remove_mipmaps(folder, file, args, texture_file=None):
    """Remove mode (remove mipmaps from uasset)"""
    src_file = os.path.join(folder, file)
    new_file = os.path.join(args.save_folder, file)
    asset = Uasset(src_file, version=args.version)
    textures = asset.get_texture_list()
    for tex in textures:
        if tex.is_empty():
            print("Skipped an empty texture.")
            continue
        tex.remove_mipmaps()
    asset.save(new_file)


@stdout_wrapper
def copy(folder, file, args, texture_file=None):
    """Copy mode (copy texture assets)"""
    # Read uasset
    uasset_file = os.path.join(folder, file)
    asset = Uasset(uasset_file, version=args.version)
    if not asset.has_textures():
        print("Skipped a non-texture asset.")
        return
    new_file = os.path.join(args.save_folder, file)
    asset.save(new_file)


# UE version for textures
UTEX_VERSIONS = [
    "5.3", "5.2", "5.1", "5.0",
    "4.26 ~ 4.27", "4.24 ~ 4.25", "4.23", "4.20 ~ 4.22",
    "4.16 ~ 4.19", "4.15", "4.14", "4.12 ~ 4.13", "4.11", "4.10",
    "4.9", "4.8", "4.7", "4.4 ~ 4.6", "4.3", "4.0 ~ 4.2",
    "ff7r", "borderlands3"
]


@stdout_wrapper
def check_version(folder, file, args, texture_file=None):
    """Check mode (check file version)"""

    print("Running valid mode with each version...")
    passed_version = []
    for ver in UTEX_VERSIONS:
        try:
            # try to parse with null stdout
            with redirect_stdout(open(os.devnull, "w")):
                valid(folder, file, args, ver.split(" ~ ")[0])
            print(f"  {(ver + ' ' * 11)[:11]}: Passed")
            passed_version.append(ver)
        except Exception:
            print(f"  {(ver + ' ' * 11)[:11]}: Failed")

    # Show the result.
    if len(passed_version) == 0:
        raise RuntimeError(
            "Failed for all supported versions. You can not mod the asset with this tool.\n"
            f"({folder}/{file})")
    elif len(passed_version) == 1 and ("~" not in passed_version[0]):
        print(f"The version is {passed_version[0]}.")
    else:
        s = f"{passed_version}"[1:-1].replace("'", "")
        print(f"Found some versions can handle the asset. ({s})")

    passed_version = [ver.split(" ~ ")[0] for ver in passed_version]
    return passed_version


@stdout_wrapper
def convert(folder, file, args, texture_file=None):
    """Convert mode (convert texture files)"""
    src_file = os.path.join(folder, file)
    new_file = os.path.join(args.save_folder, file)

    if args.convert_to.lower() in TEXTURES[1:]:
        # not DDS
        ext = args.convert_to.lower()
    else:
        if not DXGI_FORMAT.is_valid_format(args.convert_to):
            raise RuntimeError(f"The specified format is undefined. ({args.convert_to})")
        # a DXGI format
        ext = "dds"

    new_file = os.path.splitext(new_file)[0] + "." + ext

    print(f"Converting {src_file} to {new_file}...")

    texconv = Texconv()
    if ext == "dds":
        # image to dds
        texconv.convert_to_dds(src_file, DXGI_FORMAT[args.convert_to],
                               out=os.path.dirname(new_file), export_as_cubemap=False,
                               no_mip=args.no_mipmaps,
                               image_filter=args.image_filter,
                               allow_slow_codec=True, verbose=False)
    elif get_ext(file) == "dds":
        # dds to non-dds
        texconv.convert_dds_to(src_file, out=os.path.dirname(new_file), fmt=args.convert_to, verbose=False)
    else:
        # non-dds to non-dds
        texconv.convert_nondds(src_file, out=os.path.dirname(new_file), fmt=args.convert_to, verbose=False)


MODE_FUNCTIONS = {
    "valid": valid,
    "inject": inject,
    "remove_mipmaps": remove_mipmaps,
    "parse": parse,
    "export": export,
    "check": check_version,
    "convert": convert,
    "copy": copy
}


def fix_args(args, config):
    # get config
    if (args.version is None) and ("version" in config) and (config["version"] is not None):
        args.version = config["version"]

    if args.version is None:
        args.version = "4.27"

    if args.file.endswith(".txt"):
        # file path for batch file injection.
        # you can set an asset path with "echo some_path > some.txt"
        with open(args.file, "r", encoding="utf-8") as f:
            args.file = remove_quotes(f.readline())

    if args.mode == "check":
        if isinstance(args.version, str):
            args.version = [args.version]
    else:
        if isinstance(args.version, list):
            args.version = args.version[0]

    if args.max_workers is not None and args.max_workers <= 0:
        args.max_workers = None


def print_args(args):
    mode = args.mode
    print("-" * 16)
    print(f"Mode: {mode}")
    if mode != "check":
        print(f"UE version: {args.version}")
    print(f"File: {args.file}")
    if mode == "inject":
        print(f"Texture: {args.texture}")
    if mode not in ["check", "parse", "valid"]:
        print(f"Save folder: {args.save_folder}")
    if mode == "export":
        print(f"Export as: {args.export_as}")
    if mode == "convert":
        print(f"Convert to: {args.convert_to}")
    if mode in ["inject", "export"]:
        print(f"No mipmaps: {args.no_mipmaps}")
        print(f"Skip non textures: {args.skip_non_texture}")
    if mode == "inject":
        print(f"Force uncompressed: {args.force_uncompressed}")
        print(f"Image filter: {args.image_filter}")
    with concurrent.futures.ProcessPoolExecutor(args.max_workers) as executor:
        print(f"Max workers: {executor._max_workers}")
    print("-" * 16, flush=True)


def check_args(args):
    mode = args.mode
    if os.path.isfile(args.save_folder):
        raise RuntimeError(f"Output path is not a folder. ({args.save_folder})")
    if not os.path.exists(args.file):
        raise RuntimeError(f"Path not found. ({args.file})")
    if mode == "inject":
        if args.texture is None or args.texture == "":
            raise RuntimeError("Specify texture file.")
        if os.path.isdir(args.file):
            if not os.path.isdir(args.texture):
                raise RuntimeError(
                    f"Specified a folder as uasset path. But texture path is not a folder. ({args.texture})"
                )
        elif os.path.isdir(args.texture):
            raise RuntimeError(
                f"Specified a file as uasset path. But texture path is a folder. ({args.texture})"
            )
    if mode not in MODE_FUNCTIONS:
        raise RuntimeError(f"Unsupported mode. ({mode})")
    if mode != "check" and args.version not in UE_VERSIONS:
        raise RuntimeError(f"Unsupported version. ({args.version})")
    if args.export_as not in ["tga", "png", "dds", "jpg", "bmp"]:
        raise RuntimeError(f"Unsupported format to export. ({args.export_as})")
    if args.image_filter.lower() not in IMAGE_FILTERS:
        raise RuntimeError(f"Unsupported image filter. ({args.image_filter})")


def main(args, config={}):
    fix_args(args, config)
    print_args(args)
    check_args(args)

    mode = args.mode

    func = MODE_FUNCTIONS[mode]

    if os.path.isfile(args.file):
        # args.file is a file
        file = args.file
        folder = os.path.dirname(file)
        file = os.path.basename(file)
        results = [func(folder, file, args)]
    else:
        # args.file is a folder
        if mode == "convert":
            ext_list = TEXTURES
        else:
            ext_list = ["uasset"]

        folder = args.file
        file_list = get_file_list(folder, ext=ext_list)
        texture_folder = args.texture

        if mode == "inject":
            texture_file_list = [os.path.join(texture_folder, file[:-6] + TEXTURES[0]) for file in file_list]
        else:
            texture_file_list = [None] * len(file_list)

        folder, base_folder = get_base_folder(folder)
        file_list = [os.path.join(base_folder, file) for file in file_list]

        # multiprocessing
        with concurrent.futures.ProcessPoolExecutor(args.max_workers) as executor:
            futures = [
                executor.submit(func, folder, file, args, texture_file=texture)
                for file, texture in zip(file_list, texture_file_list)
            ]
            concurrent.futures.wait(futures)
            results = [future.result() for future in futures]

    if mode == "check" and args.save_detected_version:
        passed_versions = args.version
        for res in results:
            # res: a list of passed versions for a file
            common = list(set(res) & set(passed_versions))
            if len(common) > 0:
                passed_versions = common
            else:
                passed_versions = res
        if len(passed_versions) == 1:
            passed_versions = passed_versions[0]
        config["version"] = passed_versions
        print(f"Saved the detected version ({passed_versions}) in src/config.json", flush=True)
        save_config(config)


if __name__ == "__main__":  # pragma: no cover
    start_time = time.time()

    print(f"UE4 DDS Tools ver{TOOL_VERSION} by Matyalatte")

    args = get_args()
    config = get_config()
    main(args, config=config)

    if args.mode != "check":
        print(f"Success! Run time (s): {(time.time() - start_time)}")
