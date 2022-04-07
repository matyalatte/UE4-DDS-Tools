import os, argparse, shutil, traceback, json
from io_util import mkdir, compare
from utexture import Utexture, get_all_file_path
from dds import DDS
from file_list import get_file_list_from_folder, get_file_list_from_txt, get_file_list_rec

TOOL_VERSION = '0.2.3'
UE_VERSIONS = ['4.27', '4.19', '4.18', 'ff7r', 'bloodstained']

#get arguments
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='.uasset, .uexp, .ubulk, or a folder')
    parser.add_argument('--save_folder', default='output', type=str, help='save folder')
    parser.add_argument('--mode', default='parse', type=str, help='valid, parse, copy_uasset, inject, and remove_mipmaps are available.')
    parser.add_argument('--version', default=None, type=str, help='version of UE4. It will overwrite the argment in config.json.')
    parser.add_argument('--force', default=None, type=str, help='ignore dds format.')
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
def parse(folder, file, save_folder, version, force, clear=True):
    file = os.path.join(folder, file)
    if file[-3:] in ['dds', 'DDS']:
        DDS.load(file, verbose=True)
    else:
        Utexture(file, version=version, verbose=True)

#valid mode (check if the tool can read and write a file correctly.)
def valid(folder, file, save_folder, version, force, clear=True):

    #make or clear workspace
    save_folder = 'workspace/valid'
    if clear and os.path.exists(save_folder):
        shutil.rmtree(save_folder)
        print('clear: {}'.format(save_folder))
    mkdir(save_folder)
    print('clear: {}'.format(save_folder))

    src_file = os.path.join(folder, file)
    new_file=os.path.join(save_folder, file)
    
    if file[-3:] in ['dds', 'DDS']:
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
        compare(uexp_name, new_uexp_name)
        if new_ubulk_name is not None:
            compare(ubulk_name, new_ubulk_name)

#copy mode (copy uasset to workspace)
def copy_uasset(folder, file, save_folder, version, force, clear=True):
    src_file = os.path.join(folder, file)
    Utexture(src_file, version=version) #check if the asset can parse

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
    shutil.copy(uexp_name, new_uexp_name)
    print('copy: {} -> {}'.format(uasset_name, new_uasset_name))
    print('copy: {} -> {}'.format(uexp_name, new_uexp_name))
    if os.path.exists(ubulk_name):
        shutil.copy(ubulk_name, new_ubulk_name)
        print('copy: {} -> {}'.format(ubulk_name, new_ubulk_name))

#inject mode (inject dds into the asset copied to workspace)
def inject_dds(folder, file, save_folder, version, force, clear=True):
    uasset_folder = 'workspace/uasset'
    if not os.path.exists(uasset_folder):
        raise RuntimeError('Uasset Not Found. Run 1_copy_uasset*.bat first.')

    #determine which file should be injected
    file_list = get_file_list_rec(uasset_folder)
    uexp_list=[]
    for f in file_list:
        if f[-4:]=='uexp':
            uexp_list.append(f)
    if len(uexp_list)==0:
        raise RuntimeError('Uasset Not Found. Run 1_copy_uasset*.bat first.')
    elif len(uexp_list)==1:
        uasset_base=uexp_list[0]
    else:
        dds_base = os.path.splitext(os.path.basename(file))[0]
        uexp_base_list = [os.path.basename(file) for file in uexp_list]
        if dds_base+'.uexp' not in uexp_base_list:
            raise RuntimeError('The same name asset as dds not found. {}'.format(dds_base))
        id = uexp_base_list.index(dds_base+'.uexp')
        if id<0:
            raise RuntimeError('Uasset Not Found ({})'.format(os.path.join(uasset_folder, dds_base+'.uexp')))
        uasset_base=uexp_list[id]

    #read uasset
    uasset_file = os.path.join(uasset_folder, uasset_base)
    texture = Utexture(uasset_file, version=version)

    #read and inject dds
    src_file = os.path.join(folder, file)
    new_file = os.path.join(save_folder, uasset_base)
    dds = DDS.load(src_file)
    texture.inject_dds(dds, force=force)
    texture.save(new_file)

#export mode (export uasset as dds)
def export_as_dds(folder, file, save_folder, version, force, clear=True):
    src_file = os.path.join(folder, file)
    new_file = os.path.join(save_folder, file)
    new_file=os.path.splitext(new_file)[0]+'.dds'

    texture = Utexture(src_file, version=version)
    dds = DDS.asset_to_DDS(texture)
    dds.save(new_file)

#remove mode (remove mipmaps from uasset)
def remove_mipmaps(folder, file, save_folder, version, force, clear=True):
    src_file = os.path.join(folder, file)
    new_file = os.path.join(save_folder, file)
    print(save_folder)
    print(file)
    print(new_file)
    texture = Utexture(src_file, version=version)
    texture.remove_mipmaps()
    texture.save(new_file)



#main
if __name__=='__main__':
    print('UE4 DDS Tools ver{} by Matyalatte'.format(TOOL_VERSION))

    #get config
    config = get_config()
    if 'version' in config:
        version = config['version']

    #get arguments
    args = get_args()
    file = args.file
    save_folder = args.save_folder
    mode = args.mode
    force = args.force

    
    if args.version is not None:
        version = args.version
    if version is None:
        version = '4.18'
    
    print('UE version: {}'.format(version))

    try:
        mode_functions = {
            'valid': valid,
            'copy_uasset': copy_uasset,
            'inject': inject_dds,
            'remove_mipmaps': remove_mipmaps,
            'parse': parse,
            'export': export_as_dds,
        }

        #cehck configs
        if mode not in mode_functions:
            raise RuntimeError('Unsupported mode. ({})'.format(mode))
        if version not in UE_VERSIONS:
            raise RuntimeError('Unsupported version. ({})'.format(version))
        if force:
            raise RuntimeError('force injection is unsupported yet')

        func = mode_functions[mode]

        if os.path.isfile(file) and file[-3:]!='txt':
            #if input is a file
            folder = os.path.dirname(file)
            file = os.path.basename(file)
            func(folder, file, save_folder, version, force)

        else:
            if os.path.isfile(file):
                #if input file is txt (file list)
                folder, file_list = get_file_list_from_txt(file)
                func= [copy_uasset, inject_dds]
                inject=0
                for file in file_list:
                    func[inject](folder, file, save_folder, version, force)
                    inject = not inject
            else:
                #if input is a folder
                folder = file
                clear=True
                folder, file_list = get_file_list_from_folder(file)
                for file in file_list:
                    if file[-4:]=='uexp' or file[-3:] in ['dds', 'DDS']:
                        func(folder, file, save_folder, version, force, clear=clear)
                        clear=False
        print('Success!')
    
    except Exception as e:
        print(traceback.format_exc()[:-1])

