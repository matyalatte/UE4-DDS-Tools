# std libs
import argparse
import json
import os
import tempfile
import time
from contextlib import redirect_stdout

# my scripts
from io_util import compare, get_ext
from utexture import Utexture, get_all_file_path
from dds import DDS, DXGI_FORMAT
from file_list import get_file_list_from_folder, get_file_list_from_txt
from texconv import Texconv, is_windows
from utexture import get_pf_from_uexp, PF_TO_DXGI

TOOL_VERSION = '0.4.0'

# UE version: 4.13 ~ 5.0, ff7r, borderlands3
UE_VERSIONS = ['4.' + str(i+13) for i in range(15)] + ['5.0', 'ff7r', 'borderlands3']

TEXTURES = ['dds', 'tga', 'hdr']
if is_windows():
    TEXTURES += ["bmp", "jpg", "png"]


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='uasset, texture file, or folder')
    parser.add_argument('texture', nargs='?', help='texture file for injection mode')
    parser.add_argument('--save_folder', default='output', type=str, help='save folder')
    parser.add_argument('--mode', default='inject', type=str,
                        help='valid, parse, inject, export, remove_mipmaps, check and convert are available.')
    parser.add_argument('--version', default=None, type=str,
                        help='version of UE4. It will overwrite the argment in config.json.')
    parser.add_argument('--export_as', default='dds', type=str,
                        help='format for export mode. dds, tga, png, jpg, and bmp are available.')
    parser.add_argument('--convert_to', default='tga', type=str,
                        help=("format for convert mode."
                              "tga, hdr, png, jpg, bmp, or DXGI formats (e.g. BC1_UNORM) are available."))
    parser.add_argument('--no_mipmaps', action='store_true',
                        help='force no mips to dds and uasset.')
    # parser.add_argument('--force', default=None, type=str, help='ignore dds format.')
    args = parser.parse_args()
    return args


def get_config():
    json_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.exists(json_path):
        return {}
    with open(json_path, encoding='utf-8') as f:
        config = json.load(f)
    return config


def parse(folder, file, args, texconv=None):
    '''Parse mode (parse dds or uasset)'''
    file = os.path.join(folder, file)
    if get_ext(file) == 'dds':
        DDS.load(file, verbose=True)
    else:
        Utexture(file, version=args.version, verbose=True)


def valid(folder, file, args, version=None, texconv=None):
    '''Valid mode (check if the tool can read and write a file correctly.)'''
    if version is None:
        version = args.version

    with tempfile.TemporaryDirectory() as temp_dir:
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
            uasset_name, uexp_name, ubulk_name = get_all_file_path(src_file)
            texture = Utexture(src_file, version=version, verbose=True)
            new_uasset_name, new_uexp_name, new_ubulk_name = texture.save(new_file, valid=True)

            # compare and remove files
            compare(uasset_name, new_uasset_name)
            if new_uexp_name is not None:
                compare(uexp_name, new_uexp_name)
            if new_ubulk_name is not None:
                compare(ubulk_name, new_ubulk_name)


def inject(folder, file, args, texture_file=None, texconv=None):
    '''Inject mode (inject dds into the asset)'''
    if texture_file is None:
        texture_file = args.texture
    if get_ext(texture_file) not in TEXTURES:
        raise RuntimeError('Unsupported texture format. ({})'.format(get_ext(texture_file)))

    # read uasset
    uasset_file = os.path.join(folder, file)
    texture = Utexture(uasset_file, version=args.version)

    # read and inject dds
    src_file = texture_file
    new_file = os.path.join(args.save_folder, file)
    if get_ext(src_file) == 'dds':
        dds = DDS.load(src_file)
    else:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dds = texconv.convert_to_dds(src_file, texture.dxgi_format,
                                              out=temp_dir, export_as_cubemap=texture.texture_type == "Cube",
                                              no_mip=len(texture.mipmaps) <= 1 or args.no_mipmaps,
                                              allow_slow_codec=True, verbose=False)
            dds = DDS.load(temp_dds)

    texture.inject_dds(dds, force=False)
    if args.no_mipmaps:
        texture.remove_mipmaps()
    texture.save(new_file)


def export(folder, file, args, texconv=None):
    '''Export mode (export uasset as dds)'''
    src_file = os.path.join(folder, file)
    new_file = os.path.join(args.save_folder, file)
    new_file = os.path.splitext(new_file)[0] + '.dds'

    texture = Utexture(src_file, version=args.version)
    if args.no_mipmaps:
        texture.remove_mipmaps()
    dds = DDS.utexture_to_DDS(texture)
    if args.export_as == 'dds':
        dds.save(new_file)
    else:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dds = os.path.join(temp_dir, os.path.splitext(os.path.basename(file))[0]+'.dds')
            dds.save(temp_dds)
            texconv.convert_dds_to(temp_dds, out=os.path.dirname(new_file), fmt=args.export_as, verbose=False)


def remove_mipmaps(folder, file, args, texconv=None):
    '''Remove mode (remove mipmaps from uasset)'''
    src_file = os.path.join(folder, file)
    new_file = os.path.join(args.save_folder, file)
    texture = Utexture(src_file, version=args.version)
    texture.remove_mipmaps()
    texture.save(new_file)


def check_version(folder, file, args, texconv=None):
    '''Check mode (check pixel format and file version)'''
    pixel_format = get_pf_from_uexp(os.path.join(folder, file[:-len(get_ext(file))]+'uasset'))
    print(f'Pixel format: {pixel_format}')
    if pixel_format not in PF_TO_DXGI.keys():
        raise RuntimeError(f"Unsupported pixel format. ({pixel_format})")

    print('Running valid mode with each version...')
    passed_version = []
    for v in UE_VERSIONS:
        try:
            with redirect_stdout(open(os.devnull, 'w')):
                valid(folder, file, args, v)
            print(f'  {v}: Passed')
            passed_version.append(v)
        except Exception:
            print(f'  {v}: Failed')
    if len(passed_version) == 0:
        print('Failed for all supported versions. You can not mod the asset with this tool.')
    elif len(passed_version) == 1:
        print('The version is {}.'.format(passed_version[0]))
    else:
        s = '{}'.format(passed_version)[1:-1].replace("'", "")
        print('Found some versions can handle the asset. ({})'.format(s))


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


# main
if __name__ == '__main__':
    start_time = time.time()

    print('UE4 DDS Tools ver{} by Matyalatte'.format(TOOL_VERSION))

    # get config
    config = get_config()
    if 'version' in config:
        version = config['version']

    # get arguments
    args = get_args()
    file = args.file
    texture_file = args.texture
    mode = args.mode

    force = False

    if args.version is not None:
        version = args.version
    if version is None:
        version = '4.27'

    print(f'UE version: {version}')
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
        raise RuntimeError('Unsupported mode. ({})'.format(mode))
    if version not in UE_VERSIONS:
        raise RuntimeError('Unsupported version. ({})'.format(version))
    if force:
        raise RuntimeError('force injection is unsupported yet')
    if args.export_as not in ['tga', 'png', 'dds', 'jpg', 'bmp']:
        raise RuntimeError('Unsupported format to export ({})'.format(args.export_as))

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
                file_list = [file_list[i*2:i*2+2] for i in range(len(file_list)//2)]
                for uasset_file, texture_file in file_list:
                    func(folder, uasset_file, args, texture_file=os.path.join(folder, texture_file), texconv=texconv)
            else:
                for file in file_list:
                    func(folder, file, args, texconv=texconv)
        else:
            folder = os.path.dirname(file)
            file = os.path.basename(file)
            func(folder, file, args, texconv=texconv)
    else:
        # folder method
        if mode == 'inject':
            base = os.path.basename(file)
            folder = os.path.dirname(file)
            texture_folder = texture_file
            if not os.path.isdir(texture_folder):
                raise RuntimeError(
                    f'The 1st parameter is a folder but the 2nd parameter is NOT a folder. ({texture_folder})'
                )
            texture_folder, texture_file_list = \
                get_file_list_from_folder(texture_folder, ext=TEXTURES, include_base=False)
            for texture_file in texture_file_list:
                uasset_file = texture_file[:-len(get_ext(texture_file))] + 'uasset'
                uasset_file = os.path.join(base, uasset_file)
                func(folder, uasset_file, args,
                     texture_file=os.path.join(texture_folder, texture_file), texconv=texconv)
        else:
            folder, file_list = get_file_list_from_folder(file, ext=['uasset'])
            for file in file_list:
                func(folder, file, args, texconv=texconv)

    if mode != "check":
        print(f'Success! Run time (s): {(time.time() - start_time)}')
