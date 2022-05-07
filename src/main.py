#std libs
import os, argparse, shutil, json, time
from contextlib import redirect_stdout

#my scripts
from io_util import mkdir, compare
from utexture import Utexture, get_all_file_path
from dds import DDS
from file_list import get_file_list_from_folder, get_file_list_from_txt, get_file_list_rec
import texconv

TOOL_VERSION = '0.3.0'
UE_VERSIONS = ['4.' + str(i+15) for i in range(13)] + ['ff7r'] #4.15~4.27, ff7r
TEXTURES = ['dds', 'tga', 'hdr', 'bmp', 'jpg', 'png']
TEXTURES += [fmt.upper() for fmt in TEXTURES]

#get arguments
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='.uasset, .uexp, .ubulk, or a folder')
    parser.add_argument('dds_file', nargs='?', help='dds')
    parser.add_argument('--save_folder', default='output', type=str, help='save folder')
    parser.add_argument('--mode', default='parse', type=str, help='valid, parse, copy_uasset, inject, remove_mipmaps, and check are available.')
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
def parse(folder, file, save_folder, version, export_as, no_mipmaps, clear=True):
    file = os.path.join(folder, file)
    if file[-3:].lower()=='dds':
        DDS.load(file, verbose=True)
    else:
        Utexture(file, version=version, verbose=True)

#valid mode (check if the tool can read and write a file correctly.)
def valid(folder, file, save_folder, version, export_as, no_mipmaps, clear=True):

    #make or clear workspace
    save_folder = 'workspace/valid'
    if clear and os.path.exists(save_folder):
        shutil.rmtree(save_folder)
        print('clear: {}'.format(save_folder))
    mkdir(save_folder)
    print('clear: {}'.format(save_folder))

    src_file = os.path.join(folder, file)
    new_file=os.path.join(save_folder, file)
    
    if file[-3:].lower()=='dds':
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

#copy mode (copy uasset to workspace)
def copy_uasset(folder, file, save_folder, version, export_as, no_mipmaps, clear=True):
    src_file = os.path.join(folder, file)
    #Utexture(src_file, version=version) #check if the asset can parse

    #make or clear workspace
    save_folder = 'workspace/uasset'
    if clear and os.path.exists(save_folder):
        shutil.rmtree(save_folder)
        print('clear: {}'.format(save_folder))
    mkdir(save_folder)

    #copy files
    uasset_name, uexp_name, ubulk_name = get_all_file_path(src_file)
    new_file = os.path.join(save_folder, file)    
    new_uasset_name, new_uexp_name, new_ubulk_name = get_all_file_path(new_file)

    folder = os.path.dirname(new_file)
    if folder not in ['.', ''] and not os.path.exists(folder):
        mkdir(folder)
    shutil.copy(uasset_name, new_uasset_name)
    print('copy: {} -> {}'.format(uasset_name, new_uasset_name))
    if os.path.exists(uexp_name):
        shutil.copy(uexp_name, new_uexp_name)
        print('copy: {} -> {}'.format(uexp_name, new_uexp_name))
    if os.path.exists(ubulk_name):
        shutil.copy(ubulk_name, new_ubulk_name)
        print('copy: {} -> {}'.format(ubulk_name, new_ubulk_name))

#inject mode (inject dds into the asset copied to workspace)
def inject_dds(folder, file, save_folder, version, export_as, no_mipmaps, clear=True):
    uasset_folder = 'workspace/uasset'
    if not os.path.exists(uasset_folder):
        raise RuntimeError('Uasset Not Found. Run 1_copy_uasset*.bat first.')
    if file[-3:] not in TEXTURES:
        raise RuntimeError('Can not inject uasset into uasset.')


    #determine which file should be injected
    file_list = get_file_list_rec(uasset_folder)
    uasset_list=[]
    for f in file_list:
        if f[-6:]=='uasset':
            uasset_list.append(f)
    if len(uasset_list)==0:
        raise RuntimeError('Uasset Not Found. Run 1_copy_uasset*.bat first.')
    elif len(uasset_list)==1:
        uasset_base=uasset_list[0]
    else:
        dds_base = os.path.splitext(os.path.basename(file))[0]
        uasset_base_list = [os.path.basename(file) for file in uasset_list]
        if dds_base+'.uasset' not in uasset_base_list:
            raise RuntimeError('The same name asset as dds not found. {}'.format(dds_base))
        id = uasset_base_list.index(dds_base+'.uasset')
        if id<0:
            raise RuntimeError('Uasset Not Found ({})'.format(os.path.join(uasset_folder, dds_base+'.uasset')))
        uasset_base=uasset_list[id]

    #read uasset
    uasset_file = os.path.join(uasset_folder, uasset_base)
    texture = Utexture(uasset_file, version=version)

    #read and inject dds
    src_file = os.path.join(folder, file)
    new_file = os.path.join(save_folder, uasset_base)
    if src_file[-3:].lower()=='dds':
        dds = DDS.load(src_file)
    else:
        mkdir('workspace/dds')
        temp_dds = os.path.join('workspace/dds', os.path.splitext(os.path.basename(src_file))[0]+'.dds')
        texconv.convert_to_dds(src_file, temp_dds, texture.format_name, texture.texture_type, nomip=len(texture.mipmaps)<=1 or no_mipmaps)
        dds = DDS.load(temp_dds)
        os.remove(temp_dds)

    texture.inject_dds(dds, force=False)
    if no_mipmaps:
        texture.remove_mipmaps()
    texture.save(new_file)

#export mode (export uasset as dds)
def export_as_dds(folder, file, save_folder, version, export_as, no_mipmaps, clear=True):
    src_file = os.path.join(folder, file)
    new_file = os.path.join(save_folder, file)
    new_file=os.path.splitext(new_file)[0]+'.dds'

    texture = Utexture(src_file, version=version)
    if no_mipmaps:
        texture.remove_mipmaps()
    dds = DDS.asset_to_DDS(texture)
    if export_as=='dds':
        dds.save(new_file)
    else:
        mkdir('workspace/dds')
        temp_dds = os.path.join('workspace/dds', os.path.splitext(os.path.basename(file))[0]+'.dds')
        
        dds.save(temp_dds)
        texconv.convert_dds(temp_dds, new_file, export_as, texture.format_name, texture.texture_type)
        os.remove(temp_dds)
        



#remove mode (remove mipmaps from uasset)
def remove_mipmaps(folder, file, save_folder, version, export_as, no_mipmaps, clear=True):
    src_file = os.path.join(folder, file)
    new_file = os.path.join(save_folder, file)
    print(save_folder)
    print(file)
    print(new_file)
    texture = Utexture(src_file, version=version)
    texture.remove_mipmaps()
    texture.save(new_file)

#confirm mode (check)
def check_version(folder, file, save_folder, version, export_as, no_mipmaps, clear=True):
    print('Running valid mode with each version...')
    passed_version = []
    for v in UE_VERSIONS:
        try:
            with redirect_stdout(open(os.devnull, 'w')):
                valid(folder, file, save_folder, v, export_as, no_mipmaps, clear=True)
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
    dds_file = args.dds_file
    save_folder = args.save_folder
    mode = args.mode
    export_as = args.export_as
    no_mipmaps = args.no_mipmaps
    #force = args.force
    force = False
    
    if args.version is not None:
        version = args.version
    if version is None:
        version = '4.18'
    
    print('UE version: {}'.format(version))

    mode_functions = {
        'valid': valid,
        'copy_uasset': copy_uasset,
        'inject': inject_dds,
        'remove_mipmaps': remove_mipmaps,
        'parse': parse,
        'export': export_as_dds,
        'check': check_version
    }

    def main(file, mode):
        #cehck configs
        if mode not in mode_functions:
            raise RuntimeError('Unsupported mode. ({})'.format(mode))
        if version not in UE_VERSIONS:
            raise RuntimeError('Unsupported version. ({})'.format(version))
        if force:
            raise RuntimeError('force injection is unsupported yet')
        if export_as not in ['tga', 'png', 'dds', 'jpg', 'bmp']:
            raise RuntimeError('Unsupported format to export ({})'.format(export_as))
        if export_as!='dds' and not texconv.texconv_exist():
            raise RuntimeError('texconv not fould. put texconv.exe in texconv folder.')



        func = mode_functions[mode]

        if os.path.isfile(file) and file[-3:]!='txt':
            #if input is a file
            folder = os.path.dirname(file)
            file = os.path.basename(file)
            func(folder, file, save_folder, version, export_as, no_mipmaps)

        else:
            if os.path.isfile(file):
                #if input file is txt (file list)
                folder, file_list = get_file_list_from_txt(file)
                func= [copy_uasset, inject_dds]
                inject=0
                for file in file_list:
                    func[inject](folder, file, save_folder, version, export_as, no_mipmaps)
                    inject = not inject
            else:
                #if input is a folder
                folder = file
                clear=True
                folder, file_list = get_file_list_from_folder(file)
                for file in file_list:
                    if file[-6:]=='uasset' or file[-3:] in TEXTURES:
                        func(folder, file, save_folder, version, export_as, no_mipmaps, clear=clear)
                        clear=False

    if os.path.isfile(save_folder):
        raise RuntimeError("Output path is not a folder.")
    if file=="":
        raise RuntimeError("Specify files.")
    if file[-4:]==".txt" and os.path.isfile(file):
        print('Mode: {}'.format(mode))
        main(file, mode)
    if dds_file is None:
        print('Mode: {}'.format(mode))
        main(file, mode)
    elif dds_file=="":
        raise RuntimeError("Specify dds file.")
    else:
        print('Mode: inject')
        main(file, "copy_uasset")
        main(dds_file, "inject")
    if mode!="check":
        print('Success! Run time (s): {}'.format(time.time()-start_time))
