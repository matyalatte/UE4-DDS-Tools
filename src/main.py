'''Main file for UE4-DDS-Tools.'''
# std libs
import argparse
import json
import os
import time
from contextlib import redirect_stdout

# my scripts
from io_util import compare, get_ext, get_temp_dir, flush_stdout
from unreal.uasset import Uasset
from directx.dds import DDS
from directx.dxgi_format import DXGI_FORMAT
from file_list import get_file_list_from_folder, get_file_list_from_txt, get_base_folder
from directx.texconv import Texconv, is_windows

TOOL_VERSION = '0.4.4'

# UE version: 4.0 ~ 5.1, ff7r, borderlands3
UE_VERSIONS = ['4.' + str(i) for i in range(28)] + ['5.' + str(i) for i in range(2)] + ['ff7r', 'borderlands3']

# UE version for textures
UTEX_VERSIONS = [
    "5.1", "5.0",
    "4.26 ~ 4.27", "4.23 ~ 4.25", "4.20 ~ 4.22",
    "4.16 ~ 4.19", "4.15", "4.14", "4.12 ~ 4.13", "4.11", "4.10",
    "4.9", "4.8", "4.7", "4.4 ~ 4.6", "4.3", "4.0 ~ 4.2",
    "ff7r", "borderlands3"
]

TEXTURES = ['dds', 'tga', 'hdr']
if is_windows():
    TEXTURES += ["bmp", "jpg", "png"]


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='uasset, texture file, or folder')
    parser.add_argument('texture', nargs='?', help='Texture file for injection mode')
    parser.add_argument('--save_folder', default='output', type=str, help='Output folder')
    parser.add_argument('--mode', default='inject', type=str,
                        help='valid, parse, inject, export, remove_mipmaps, check and convert are available.')
    parser.add_argument('--version', default=None, type=str,
                        help='UE version. It will overwrite the argment in config.json.')
    parser.add_argument('--export_as', default='dds', type=str,
                        help='Format for export mode. dds, tga, png, jpg, and bmp are available.')
    parser.add_argument('--convert_to', default='tga', type=str,
                        help=("Format for convert mode."
                              "tga, hdr, png, jpg, bmp, or DXGI formats (e.g. BC1_UNORM) are available."))
    parser.add_argument('--no_mipmaps', action='store_true',
                        help='Force no mips to dds and uasset.')
    parser.add_argument('--force_uncompressed', action='store_true',
                        help='Use uncompressed format for BC1, BC6, and BC7.')
    parser.add_argument('--disable_tempfile', action='store_true',
                        help="Store temporary files in the tool's directory.")
    parser.add_argument('--skip_non_texture', action='store_true',
                        help="Disable errors about non-texture assets.")
    return parser.parse_args()


def get_config():
    json_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.exists(json_path):
        return {}
    with open(json_path, encoding='utf-8') as f:
        return json.load(f)


def parse(folder, file, args, texconv=None):
    '''Parse mode (parse dds or uasset)'''
    file = os.path.join(folder, file)
    if get_ext(file) == 'dds':
        DDS.load(file, verbose=True)
    else:
        Uasset(file, version=args.version, verbose=True)


def valid(folder, file, args, version=None, texconv=None):
    '''Valid mode (check if the tool can read and write a file correctly.)'''
    if version is None:
        version = args.version

    with get_temp_dir(disable_tempfile=args.disable_tempfile) as temp_dir:
        src_file = os.path.join(folder, file)
        new_file = os.path.join(temp_dir, file)

        if get_ext(file) == 'dds':
            # read and write dds
            dds = DDS.load(src_file)
            dds.save(new_file)

            # compare and remove files
            compare(src_file, new_file)

        else:
            # read and write uasset
            asset = Uasset(src_file, version=version, verbose=True)
            uasset_name, uexp_name, ubulk_name = asset.get_all_file_path()
            asset.save(new_file, valid=True)
            new_uasset_name, new_uexp_name, new_ubulk_name = asset.get_all_file_path()

            # compare and remove files
            compare(uasset_name, new_uasset_name)
            if new_uexp_name is not None:
                compare(uexp_name, new_uexp_name)
            if new_ubulk_name is not None:
                compare(ubulk_name, new_ubulk_name)


def search_texture_file(file_base, ext_list, index=None):
    if index is not None:
        file_base += f".{index}"
    for ext in ext_list:
        file = ".".join([file_base, ext])
        if os.path.exists(file):
            return file
    raise RuntimeError(f"Texture file not found. ({file_base})")


def inject(folder, file, args, texture_file=None, texconv=None):
    '''Inject mode (inject dds into the asset)'''
    if texture_file is None:
        texture_file = args.texture
    file_base, ext = os.path.splitext(texture_file)
    ext = ext[1:].lower()
    if ext not in TEXTURES:
        raise RuntimeError(f'Unsupported texture format. ({ext})')

    # read uasset
    uasset_file = os.path.join(folder, file)
    asset = Uasset(uasset_file, version=args.version)
    if not asset.has_textures():
        desc = f"(file: {uasset_file}, class: {asset.get_main_class_name()})"
        if args.skip_non_texture:
            print("Skipped a non-texture asset. " + desc)
            return
        raise RuntimeError("This uasset has no textures. " + desc)
    textures = asset.get_texture_list()

    # read and inject dds
    ext_list = [ext] + TEXTURES
    if len(textures) == 1:
        src_files = [search_texture_file(file_base, ext_list)]
    else:
        splitted = file_base.split(".")
        if len(splitted) >= 2 and splitted[-1] == "0":
            file_base = ".".join(splitted[:-1])
        src_files = [search_texture_file(file_base, ext_list, index=i) for i in range(len(textures))]
    new_file = os.path.join(args.save_folder, file)

    for tex, src in zip(textures, src_files):
        if args.force_uncompressed:
            tex.to_uncompressed()

        if get_ext(src) == 'dds':
            dds = DDS.load(src)
        else:
            with get_temp_dir(disable_tempfile=args.disable_tempfile) as temp_dir:
                temp_dds = texconv.convert_to_dds(src, tex.dxgi_format,
                                                  out=temp_dir, export_as_cubemap=tex.is_cube,
                                                  no_mip=len(tex.mipmaps) <= 1 or args.no_mipmaps,
                                                  allow_slow_codec=True, verbose=False)
                dds = DDS.load(temp_dds)

        tex.inject_dds(dds)
        if args.no_mipmaps:
            tex.remove_mipmaps()
        flush_stdout()

    asset.update_package_source(is_official=False)
    asset.save(new_file)


def export(folder, file, args, texconv=None):
    '''Export mode (export uasset as dds)'''
    src_file = os.path.join(folder, file)
    new_file = os.path.join(args.save_folder, file)
    new_dir = os.path.dirname(new_file)

    asset = Uasset(src_file, version=args.version)
    if not asset.has_textures():
        desc = f"(file: {src_file}, class: {asset.get_main_class_name()})"
        if args.skip_non_texture:
            print("Skipped a non-texture asset. " + desc)
            return
        raise RuntimeError("This uasset has no textures. " + desc)
    textures = asset.get_texture_list()
    multi = len(textures) > 1
    for tex, i in zip(textures, range(len(textures))):
        if multi:
            file_name = os.path.splitext(new_file)[0] + f'.{i}.dds'
        else:
            file_name = os.path.splitext(new_file)[0] + '.dds'
        if args.no_mipmaps:
            tex.remove_mipmaps()
        dds = tex.get_dds()
        if args.export_as == 'dds':
            dds.save(file_name)
        else:
            with get_temp_dir(disable_tempfile=args.disable_tempfile) as temp_dir:
                temp_dds = os.path.join(temp_dir, os.path.basename(file_name))
                dds.save(temp_dds)
                converted_file = texconv.convert_dds_to(temp_dds, out=new_dir, fmt=args.export_as, verbose=False)
                print(f"convert to: {converted_file}")
        flush_stdout()


def remove_mipmaps(folder, file, args, texconv=None):
    '''Remove mode (remove mipmaps from uasset)'''
    src_file = os.path.join(folder, file)
    new_file = os.path.join(args.save_folder, file)
    asset = Uasset(src_file, version=args.version)
    textures = asset.get_texture_list()
    for tex in textures:
        tex.remove_mipmaps()
    asset.save(new_file)


def check_version(folder, file, args, texconv=None):
    '''Check mode (check pixel format and file version)'''
    print('Running valid mode with each version...')
    passed_version = []
    for ver in UTEX_VERSIONS:
        try:
            with redirect_stdout(open(os.devnull, 'w')):
                valid(folder, file, args, ver.split(" ~ ")[0])
            print(f'  {(ver + " " * 11)[:11]}: Passed')
            passed_version.append(ver)
        except Exception:
            print(f'  {(ver + " " * 11)[:11]}: Failed')
    if len(passed_version) == 0:
        print('Failed for all supported versions. You can not mod the asset with this tool.')
    elif len(passed_version) == 1 and ("~" not in passed_version[0]):
        print(f'The version is {passed_version[0]}.')
    else:
        s = f'{passed_version}'[1:-1].replace("'", "")
        print(f'Found some versions can handle the asset. ({s})')


def convert(folder, file, args, texconv=None):
    '''Convert mode (convert texture files)'''
    src_file = os.path.join(folder, file)
    new_file = os.path.join(args.save_folder, file)

    if args.convert_to.lower() in TEXTURES[1:]:
        ext = args.convert_to.lower()
    else:
        if not DXGI_FORMAT.is_valid_format("DXGI_FORMAT_" + args.convert_to):
            raise RuntimeError(f"The specified format is undefined. ({args.convert_to})")
        ext = "dds"

    new_file = os.path.splitext(new_file)[0] + "." + ext

    print(f"Converting {src_file} to {new_file}...")

    if ext == "dds":
        texconv.convert_to_dds(src_file, DXGI_FORMAT["DXGI_FORMAT_" + args.convert_to],
                               out=os.path.dirname(new_file), export_as_cubemap=False,
                               no_mip=args.no_mipmaps,
                               allow_slow_codec=True, verbose=False)
    elif get_ext(file) == "dds":
        texconv.convert_dds_to(src_file, out=os.path.dirname(new_file), fmt=args.convert_to, verbose=False)
    else:
        texconv.convert_nondds(src_file, out=os.path.dirname(new_file), fmt=args.convert_to, verbose=False)


if __name__ == '__main__':
    start_time = time.time()

    print(f'UE4 DDS Tools ver{TOOL_VERSION} by Matyalatte')

    # get arguments
    args = get_args()
    file = args.file
    texture_file = args.texture
    mode = args.mode

    # get config
    config = get_config()
    if (args.version is None) and ('version' in config) and (config['version'] is not None):
        args.version = config['version']

    if args.version is None:
        args.version = '4.27'

    print(f'UE version: {args.version}')
    print(f'Mode: {mode}')

    mode_functions = {
        'valid': valid,
        'inject': inject,
        'remove_mipmaps': remove_mipmaps,
        'parse': parse,
        'export': export,
        'check': check_version,
        "convert": convert
    }

    # cehck configs
    if os.path.isfile(args.save_folder):
        raise RuntimeError("Output path is not a folder.")
    if file == "":
        raise RuntimeError("Specify files.")
    if mode == 'inject' and (texture_file is None or texture_file == ""):
        raise RuntimeError("Specify texture file.")
    if mode not in mode_functions:
        raise RuntimeError(f'Unsupported mode. ({mode})')
    if args.version not in UE_VERSIONS:
        raise RuntimeError(f'Unsupported version. ({args.version})')
    if args.export_as not in ['tga', 'png', 'dds', 'jpg', 'bmp']:
        raise RuntimeError(f'Unsupported format to export ({args.export_as})')

    # load texconv
    texconv = None
    if (mode == "export" and args.export_as != "dds") or mode in ["inject", "convert"]:
        texconv = Texconv()

    func = mode_functions[mode]

    if os.path.isfile(file):
        if get_ext(file) == 'txt':
            # txt method (file list)
            folder, file_list = get_file_list_from_txt(file)
            if mode == 'inject':
                file_list = [file_list[i * 2: i * 2 + 2] for i in range(len(file_list) // 2)]
                for uasset_file, texture_file in file_list:
                    func(folder, uasset_file, args, texture_file=os.path.join(folder, texture_file), texconv=texconv)
            else:
                for file in file_list:
                    func(folder, file, args, texconv=texconv)
                    flush_stdout()
        else:
            folder = os.path.dirname(file)
            file = os.path.basename(file)
            func(folder, file, args, texconv=texconv)
    else:
        # folder method
        if mode == 'convert':
            ext_list = TEXTURES
        else:
            ext_list = ['uasset']
        folder, file_list = get_file_list_from_folder(file, ext=ext_list, include_base=mode != "inject")

        if mode == 'inject':
            texture_folder = texture_file
            if not os.path.isdir(texture_folder):
                raise RuntimeError(
                    f'The 1st parameter is a folder but the 2nd parameter is NOT a folder. ({texture_folder})'
                )
            texture_file_list = [os.path.join(texture_folder, file[:-6] + TEXTURES[0]) for file in file_list]
            base_folder, folder = get_base_folder(folder)
            file_list = [os.path.join(folder, file) for file in file_list]
            for file, texture in zip(file_list, texture_file_list):
                func(base_folder, file, args, texture_file=texture, texconv=texconv)
                flush_stdout()
        else:
            for file in file_list:
                func(folder, file, args, texconv=texconv)
                flush_stdout()
    if mode != "check":
        print(f'Success! Run time (s): {(time.time() - start_time)}')
