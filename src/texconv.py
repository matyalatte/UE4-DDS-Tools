import os
from io_util import mkdir

def texconv_exist():
    return os.path.exists('texconv/texconv.exe')

def convert_dds(dds_path, save_path, export_as, format_name, texture_type):
    if texture_type=='Cube':
        raise RuntimeError('Can not convert cubemap textures with texconv.')
    if export_as=='dds':
        raise RuntimeError('Can not convert dds to dds.')
    if ('BC6' in format_name or 'Float' in format_name) and export_as=='tga':
        export_as='hdr'
    if format_name not in FORMAT_FOR_TEXCONV.keys():
        raise RuntimeError(
            f"DDS converter does NOT support {format_name}.\n"
            "You should choose '.dds' as an export format."
        )

    save_folder=os.path.dirname(save_path)
    if save_folder not in ['.', ''] and not os.path.exists(save_folder):
        mkdir(save_folder)
    fmt = export_as
    if 'BC5' in format_name:
        fmt += ' -f rgba -reconstructz'
    cmd = 'texconv\\texconv.exe "{}" -o "{}" -ft {} -y'.format(dds_path, save_folder, fmt)
    print(cmd)
    os.system(cmd)
    if not os.path.exists(os.path.splitext(save_path)[0]+'.'+export_as):
        raise RuntimeError('Failed to convert dds. ({})'.format(dds_path))

FORMAT_FOR_TEXCONV = {
    'DXT1/BC1': 'DXT1',
    'DXT5/BC3': 'DXT5',
    'BC4/ATI1': 'BC4_UNORM',
    'BC5/ATI2': 'BC5_UNORM',
    'BC6H(unsigned)': 'BC6H_UF16',
    'BC7': 'BC7_UNORM',
    'FloatRGBA': 'R16G16B16A16_FLOAT',
    'B8G8R8A8': 'B8G8R8A8_UNORM'
}

def convert_to_dds(file_path, save_path, format_name, texture_type, nomip=False):
    if texture_type=='Cube':
        raise RuntimeError('Can not convert cubemap textures with texconv.')
    if ('BC6' in format_name or 'Float' in format_name) and file_path[-3:].lower()!='hdr':
        raise RuntimeError('Use .dds or .hdr to inject HDR textures. ({})'.format(file_path))
    if format_name not in FORMAT_FOR_TEXCONV.keys():
        raise RuntimeError(
            f"DDS converter does NOT support {format_name}.\n"
            "You should convert it to dds with another tool first."
        )

    save_folder=os.path.dirname(save_path)
    if save_folder not in ['.', ''] and not os.path.exists(save_folder):
        mkdir(save_folder)

    fmt=FORMAT_FOR_TEXCONV[format_name]
    cmd = 'texconv\\texconv.exe "{}" -o "{}" -f {} -y '.format(file_path, save_folder, fmt)
    if nomip:
        cmd += '-m 1 '
    print(cmd)
    os.system(cmd)
    if not os.path.exists(save_path):
        print(save_path)
        raise RuntimeError('Failed to convert. ({})'.format(file_path))
