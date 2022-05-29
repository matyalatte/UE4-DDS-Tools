#std libs
import os, argparse, shutil, json, time
from contextlib import redirect_stdout

#my scripts
from io_util import mkdir, compare
from utexture import Utexture, get_all_file_path
from dds import DDS
from file_list import get_file_list_from_folder, get_file_list_from_txt, get_ext
import texconv

TOOL_VERSION = '0.3.2'
UE_VERSIONS = ['4.' + str(i+13) for i in range(15)] + ['ff7r', 'borderlands3'] #4.13~4.27, ff7r
TEXTURES = ['dds', 'tga', 'hdr', 'bmp', 'jpg', 'png']
TEXTURES += [fmt.upper() for fmt in TEXTURES]

#get arguments
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='uasset, texture file, or folder')
    parser.add_argument('texture', nargs='?', help='texture file for injection mode')
    parser.add_argument('--save_folder', default='output', type=str, help='save folder')
    parser.add_argument('--mode', default='inject', type=str, help='valid, parse, inject, export, remove_mipmaps, and check are available.')
    parser.add_argument('--version', default=None, type=str, help='version of UE4. It will overwrite the argment in config.json.')
    parser.add_argument('--export_as', default='dds', type=str, help='format to export. dds, tga, png, jpg, and bmp is available.')
    parser.add_argument('--no_mipmaps', action='store_true', help='force no mips to dds and uasset.')
    #parser.add_argument('--force', default=None, type=str, help='ignore dds format.')
    args = parser.parse_args()
    return args

#get config
def get_config():
    json_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.exists(json_path):
        return {}
    with open(json_path, encoding='utf-8') as f:
        config = json.load(f)
    return config

#parse mode (parse dds or uasset)
def parse(folder, file, args):
    file = os.path.join(folder, file)
    if get_ext(file)=='dds':
        DDS.load(file, verbose=True)
    else:
        Utexture(file, version=args.version, verbose=True)

#valid mode (check if the tool can read and write a file correctly.)
def valid(folder, file, args, version=None):
    if version is None:
        version = args.version

    #make or clear workspace
    save_folder = 'workspace/valid'
    if os.path.exists(save_folder):
        shutil.rmtree(save_folder)
        print('clear: {}'.format(save_folder))
    mkdir(save_folder)
    print('clear: {}'.format(save_folder))

    src_file = os.path.join(folder, file)
    new_file=os.path.join(save_folder, file)
    
    if get_ext(file)=='dds':
        #read and write dds
        dds = DDS.load(src_file)
        dds.save(new_file)

        #compare and remove files
        compare(src_file, new_file)

    else:
        #read and write uasset
        uasset_name, uexp_name, ubulk_name = get_all_file_path(src_file)
        texture = Utexture(src_file, version=version, verbose=True)
        new_uasset_name, new_uexp_name, new_ubulk_name = texture.save(new_file)

        #compare and remove files
        compare(uasset_name, new_uasset_name)
        if new_uexp_name is not None:
            compare(uexp_name, new_uexp_name)
        if new_ubulk_name is not None:
            compare(ubulk_name, new_ubulk_name)

#inject mode (inject dds into the asset copied to workspace)
def inject(folder, file, args, texture_file=None):
    if texture_file is None:
        texture_file=args.texture_file
    if get_ext(texture_file) not in TEXTURES:
        raise RuntimeError('Unsupported texture format. ({})'.format(get_ext(texture_file)))

    #read uasset
    uasset_file = os.path.join(folder, file)
    texture = Utexture(uasset_file, version=args.version)

    #read and inject dds
    src_file = texture_file
    new_file = os.path.join(args.save_folder, file)
    if get_ext(src_file)=='dds':
        dds = DDS.load(src_file)
    else:
        mkdir('workspace/dds')
        temp_dds = os.path.join('workspace/dds', os.path.splitext(os.path.basename(src_file))[0]+'.dds')
        texconv.convert_to_dds(src_file, temp_dds, texture.format_name, texture.texture_type, nomip=len(texture.mipmaps)<=1 or args.no_mipmaps)
        dds = DDS.load(temp_dds)
        os.remove(temp_dds)

    texture.inject_dds(dds, force=False)
    if args.no_mipmaps:
        texture.remove_mipmaps()
    texture.save(new_file)

#export mode (export uasset as dds)
def export_as_dds(folder, file, args):
    src_file = os.path.join(folder, file)
    new_file = os.path.join(args.save_folder, file)
    new_file=os.path.splitext(new_file)[0]+'.dds'

    texture = Utexture(src_file, version=args.version)
    if args.no_mipmaps:
        texture.remove_mipmaps()
    dds = DDS.asset_to_DDS(texture)
    if args.export_as=='dds':
        dds.save(new_file)
    else:
        mkdir('workspace/dds')
        temp_dds = os.path.join('workspace/dds', os.path.splitext(os.path.basename(file))[0]+'.dds')
        
        dds.save(temp_dds)
        texconv.convert_dds(temp_dds, new_file, args.export_as, texture.format_name, texture.texture_type)
        os.remove(temp_dds)
        
#remove mode (remove mipmaps from uasset)
def remove_mipmaps(folder, file, args):
    src_file = os.path.join(folder, file)
    new_file = os.path.join(args.save_folder, file)
    texture = Utexture(src_file, version=args.version)
    texture.remove_mipmaps()
    texture.save(new_file)

#confirm mode (check)
def check_version(folder, file, args):
    print('Running valid mode with each version...')
    passed_version = []
    for v in UE_VERSIONS:
        try:
            with redirect_stdout(open(os.devnull, 'w')):
                valid(folder, file, args, v)
            print('  {}: Passed'.format(v))
            passed_version.append(v)
        except:
            print('  {}: Failed'.format(v))
    if len(passed_version)==0:
        print('Failed for all supported versions. You can not mod the asset with this tool.')
    elif len(passed_version)==1:
        print('The version is {}.'.format(passed_version[0]))
    else:
        s = '{}'.format(passed_version)[1:-1].replace("'", "")
        print('Found some versions can handle the asset. ({})'.format(s))

#main
if __name__=='__main__':
    start_time = time.time()
    
    print('UE4 DDS Tools ver{} by Matyalatte'.format(TOOL_VERSION))

    #get config
    config = get_config()
    if 'version' in config:
        version = config['version']

    #get arguments
    args = get_args()
    file = args.file
    texture_file = args.texture
    mode = args.mode

    force = False
    
    if args.version is not None:
        version = args.version
    if version is None:
        version = '4.27'
    
    print('UE version: {}'.format(version))
    print('Mode: {}'.format(mode))

    mode_functions = {
        'valid': valid,
        'inject': inject,
        'remove_mipmaps': remove_mipmaps,
        'parse': parse,
        'export': export_as_dds,
        'check': check_version
    }

    #cehck configs
    if os.path.isfile(args.save_folder):
        raise RuntimeError("Output path is not a folder.")
    if file=="":
        raise RuntimeError("Specify files.")
    if mode=='inject' and (texture_file is None or texture_file==""):
        raise RuntimeError("Specify texture file.")
    if mode not in mode_functions:
        raise RuntimeError('Unsupported mode. ({})'.format(mode))
    if version not in UE_VERSIONS:
        raise RuntimeError('Unsupported version. ({})'.format(version))
    if force:
        raise RuntimeError('force injection is unsupported yet')
    if args.export_as not in ['tga', 'png', 'dds', 'jpg', 'bmp']:
        raise RuntimeError('Unsupported format to export ({})'.format(args.export_as))
    if args.export_as!='dds' and not texconv.texconv_exist():
        raise RuntimeError('texconv not fould. put texconv.exe in texconv folder.')

    func = mode_functions[mode]
    
    if os.path.isfile(file):
        if get_ext(file)=='txt':
            #txt method (file list)
            folder, file_list = get_file_list_from_txt(file)
            if mode=='inject':
                file_list = [file_list[i*2:i*2+2] for i in range(len(file_list)//2)]
                for uasset_file, texture_file in file_list:
                    func(folder, uasset_file, args, texture_file=os.path.join(folder, texture_file))
            else:
                for file in file_list:
                    func(folder, file, args)
        else:
            folder = os.path.dirname(file)
            file = os.path.basename(file)
            func(folder, file, args)
    else:
        #folder method
        if mode=='inject':
            base = os.path.basename(file)
            folder = os.path.dirname(file)
            texture_folder = texture_file
            if not os.path.isdir(texture_folder):
                raise RuntimeError('The 1st parameter is a folder but the 2nd parameter is NOT a folder. ({})'.format(texture_folder))
            texture_folder, texture_file_list = get_file_list_from_folder(texture_folder, ext=TEXTURES, include_base=False)
            for texture_file in texture_file_list:
                uasset_file = texture_file[:-len(get_ext(texture_file))]+'uasset'
                uasset_file = os.path.join(base, uasset_file)
                func(folder, uasset_file, args, texture_file=os.path.join(texture_folder, texture_file))
        else:
            folder, file_list = get_file_list_from_folder(file, ext=['uasset'])
            for file in file_list:
                func(folder, file, args)

    if mode!="check":
        print('Success! Run time (s): {}'.format(time.time()-start_time))
