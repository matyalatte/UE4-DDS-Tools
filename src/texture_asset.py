import os
from io_util import *
from uasset import Uasset

BYTE_PER_PIXEL = {
    'DXT1/BC1': 0.5,
    'DXT5/BC3': 1,
    'BC4/ATI1': 0.5,
    'BC4(signed)': 0.5,
    'BC5/ATI2': 1,
    'BC5(signed)': 1, 
    'BC6H(unsigned)': 1,
    'BC6H(signed)': 1,
    'BC7': 1,
    'FloatRGBA': 8,
    'B8G8R8A8(sRGB)': 4
}

PF_FORMAT = {
    'PF_DXT1': 'DXT1/BC1',
    'PF_DXT5': 'DXT5/BC3',
    'PF_BC4': 'BC4/ATI1',
    'PF_BC5': 'BC5/ATI2',
    'PF_BC6H': 'BC6H(unsigned)',
    'PF_BC7': 'BC7', 
    'PF_FloatRGBA': 'FloatRGBA',
    'PF_B8G8R8A8': 'B8G8R8A8(sRGB)'
}

def is_power_of_2(n):
    if n==1:
        return True
    if n%2!=0:
        return False
    return is_power_of_2(n//2)

EXT = ['.uasset', '.uexp', '.ubulk']
def get_all_file_path(file):
    base_name, ext = os.path.splitext(file)

    if ext not in EXT:
        raise RuntimeError('Not Uasset. ({})'.format(file))

    return [base_name + ext for ext in EXT]

#mipmap meta data (size, offset , etc.)
class MipmapMetadata:
    UEXP_FLAG=[66817, 32]
    def __init__(self, data_size, offset, size, uexp):
        self.uexp=uexp
        if uexp:
            self.data_size=0
        else:
            self.data_size=data_size
        self.offset=offset
        self.width=size[0]
        self.height=size[1]
        self.pixel_num = self.width*self.height

    def read(f):
        read_const_uint32(f, 1)    #Entry Indicator?
        flag = read_uint32(f)      #uexp flag (32:uexp, 66817:ubulk)
        uexp=flag==MipmapMetadata.UEXP_FLAG[1]
        data_size = read_uint32(f)
        if uexp:
            check(data_size, 0)
        read_const_uint32(f, data_size)
        offset = read_uint32(f)
        read_null(f)
        width = read_uint32(f)
        height = read_uint32(f)
        return MipmapMetadata(data_size, offset, [width, height], uexp)

    def print(self, padding=2):
        pad = ' '*padding
        print(pad + 'file: ' + 'uexp'*self.uexp + 'ubluk'*(not self.uexp))
        if not self.uexp:
            print(pad + 'data size: {}'.format(self.data_size))
        print(pad + 'metadata'*self.uexp + 'texture data'*(not self.uexp) + ' offset: {}'.format(self.offset))
        print(pad + 'width: {}'.format(self.width))
        print(pad + 'height: {}'.format(self.height))

    def to_uexp(self):
        self.data_size=0
        self.uexp=True

    def write(self, f, uasset_size):
        new_offset = f.tell() + uasset_size+24

        write_uint32(f, 1)
        write_uint32(f, MipmapMetadata.UEXP_FLAG[self.uexp])
        write_uint32(f, self.data_size)
        write_uint32(f, self.data_size)
        if self.uexp:
            write_uint32(f, new_offset)
        else:
            write_uint32(f, self.offset)
        write_null(f)

        write_uint32(f, self.width)
        write_uint32(f, self.height)

class TextureUasset:
    UNREAL_SIGNATURE = b'\xC1\x83\x2A\x9E'
    UBULK_FLAG_FF7R = [0, 16384]
    UBULK_FLAG = [[72, 1281], [72, 66817]]
    
    def __init__(self, file_path, version='ff7r', verbose=False):
        self.version = version

        if not os.path.isfile(file_path):
            raise RuntimeError('Not File. ({})'.format(file_path))

        uasset_name, uexp_name, ubulk_name = get_all_file_path(file_path)

        self.uasset = Uasset(uasset_name)
        if len(self.uasset.exports)!=1:
            raise RuntimeError('Unexpected number of exports')

        self.uasset_size = self.uasset.size
        self.name_list = self.uasset.name_list
        self.texture_type = self.uasset.texture_type

        with open(uexp_name, 'rb') as f:
            if version=='ff7r':
                self.read_uexp_ff7r(f)
            else:
                self.read_uexp(f)
            self.none_name_id = read_uint64(f)
            if self.version=='4.27':
                read_null(f)
            foot=f.read()

            check(foot, TextureUasset.UNREAL_SIGNATURE)

        #read ubulk
        if self.has_ubulk:
            with open(ubulk_name, 'rb') as f:
                size = get_size(f)
                self.ubulk_map_data = [f.read(meta.data_size) for meta in self.ubulk_map_meta]
                check(size, f.tell())

        print('load: ' + uasset_name)
        self.print(verbose)

    def read_uexp_ff7r(self, f):
        
        f.read(1)
        b = f.read(1)
        while (b not in [b'\x03', b'\x05']):
            f.read(1)
            b = f.read(1)
        s = f.tell()
        f.seek(0)
        self.bin1=f.read(s)
        self.original_width = read_uint32(f)
        self.original_height = read_uint32(f)
        offset=f.tell()
        b = f.read(8)
        while (b!=b'\x01\x00\x01\x00\x01\x00\x00\x00'):
            b=b''.join([b[1:], f.read(1)])
        s=f.tell()-offset
        f.seek(offset)
        self.unk = f.read(s)
        self.type_name_id = read_uint64(f)
        end_offset = read_uint32(f) #Offset to end of uexp?
        f.seek(8, 1) #original width and height
        self.cube_flag = read_uint16(f)
        self.unk_int = read_uint16(f)
        if self.cube_flag==1:
            if self.texture_type!='2D':
                raise RuntimeError('')
        elif self.cube_flag==6:
            if self.texture_type!='Cube':
                raise RuntimeError('')
        else:
            print(self.cube_flag)
            raise RuntimeError('')
        
        self.type = read_str(f)

        if self.unk_int==TextureUasset.UBULK_FLAG_FF7R[1]:
            read_null(f)
            read_null(f)
            self.ubulk_map_num = read_uint32(f) #bulk map num + unk_map_num
        else:
            self.ubulk_map_num = 0

        self.unk_map_num=read_uint32(f) #number of some mipmaps in uexp
        map_num = read_uint32(f) #map num ?
        self.ubulk_map_num-=self.unk_map_num
        self.uexp_map_num=map_num-self.ubulk_map_num
        self.has_ubulk=self.ubulk_map_num>0

        
        #read mipmap data 
        read_const_uint32(f, 1) #Entry Indicator?
        read_const_uint32(f, 64)
        uexp_map_size = read_uint32(f) #Length of Mipmap Data
        read_const_uint32(f, uexp_map_size)
        self.offset = read_uint32(f) #Offset to start of Mipmap Data
        read_null(f)
        #check(self.offset, self.uasset_size+f.tell())
        uexp_map_data = f.read(uexp_map_size)
        

        self.uexp_max_width=read_uint32(f)
        self.uexp_max_height=read_uint32(f)
        read_const_uint32(f, self.cube_flag)
        read_const_uint32(f, self.uexp_map_num)

        #read mipmap meta data
        if self.has_ubulk:
            self.ubulk_map_meta = [MipmapMetadata.read(f) for i in range(self.ubulk_map_num)]
        self.uexp_map_meta = [MipmapMetadata.read(f) for i in range(self.uexp_map_num)]

        #get format name
        if self.type not in PF_FORMAT:
            raise RuntimeError('Unsupported format. ({})'.format(self.type))
        self.format_name = PF_FORMAT[self.type]
        self.byte_per_pixel = BYTE_PER_PIXEL[self.format_name]

        #split mipmap data
        self.uexp_map_data = []
        i=0
        for meta in self.uexp_map_meta:
            size = int(meta.pixel_num*self.byte_per_pixel*self.cube_flag)
            self.uexp_map_data.append(uexp_map_data[i:i+size])
            i+=size
        check(i, len(uexp_map_data))

    def read_uexp(self, f):
        top_name = self.name_list[read_uint32(f)]
        f.seek(0)
        if top_name=='ImportedSize':
            self.bin1 = f.read(49)
            self.original_width = read_uint32(f)
            self.original_height = read_uint32(f)
        else:
            self.bin1 = None
        offset=f.tell()
        b = f.read(8)
        while (b!=b'\x01\x00\x01\x00\x01\x00\x00\x00'):
            b=b''.join([b[1:], f.read(1)])
        s=f.tell()-offset
        f.seek(offset)
        self.unk = f.read(s)
        self.type_name_id = read_uint64(f)
        end_offset = read_uint32(f) #Offset to end of uexp?
        if self.version=='4.27':
            read_null(f)
        f.seek(8, 1) #original width and height
        self.cube_flag = read_uint16(f)
        self.unk_int = read_uint16(f)
        if self.cube_flag==1:
            if self.texture_type!='2D':
                raise RuntimeError('')
        elif self.cube_flag==6:
            if self.texture_type!='Cube':
                raise RuntimeError('')
        else:
            print(self.cube_flag)
            raise RuntimeError('')

        self.unk_map_num = 0
        
        self.type = read_str(f)
        #check(self.type, name_list[self.type_name_id])

        read_null(f)
        self.uexp_map_num = read_uint32(f) #mipmap num?
        self.uexp_map_meta=[]
        self.uexp_map_data = []
        self.ubulk_map_meta=[]
        for i in range(self.uexp_map_num):
            #read mipmap data 
            read_const_uint32(f, 1) #Entry Indicator?
            ubulk_flag = read_uint32(f)
            map_size = read_uint32(f) #Length of Mipmap Data
            read_const_uint32(f, map_size)
            offset = read_uint64(f) #Offset to start of Mipmap Data

            if TextureUasset.UBULK_FLAG[self.version=='4.27'].index(ubulk_flag)==0:
                self.uexp_map_data.append(f.read(map_size))

            width=read_uint32(f)
            height=read_uint32(f)

            if TextureUasset.UBULK_FLAG[self.version=='4.27'].index(ubulk_flag)==0:
                self.uexp_map_meta.append(MipmapMetadata(0, None, [width, height], True))
            else:
                self.ubulk_map_meta.append(MipmapMetadata(map_size, None, [width, height], False))
            if self.version=='4.27':
                read_const_uint32(f, 1)

        self.ubulk_map_num = len(self.ubulk_map_meta)
        self.has_ubulk=self.ubulk_map_num>0

        #get format name
        if self.type not in PF_FORMAT:
            raise RuntimeError('Unsupported format. ({})'.format(self.type))
        self.format_name = PF_FORMAT[self.type]
        self.byte_per_pixel = BYTE_PER_PIXEL[self.format_name]

        for data, meta in zip(self.uexp_map_data, self.uexp_map_meta):
            size = int(meta.pixel_num*self.byte_per_pixel*self.cube_flag)
            check(size, len(data))

    def get_max_size(self):
        if self.has_ubulk:
            meta = self.ubulk_map_meta
        else:
            meta = self.uexp_map_meta
        max_width=meta[0].width
        max_height=meta[0].height
        return max_width, max_height

    def get_mipmap_num(self):
        uexp_map_num = len(self.uexp_map_meta)      
        if self.has_ubulk:
            ubulk_map_num = len(self.ubulk_map_meta)
        else:
            ubulk_map_num = 0
        return uexp_map_num, ubulk_map_num

    def save(self, file):
        folder = os.path.dirname(file)
        if folder not in ['.', ''] and not os.path.exists(folder):
            mkdir(folder)

        uasset_name, uexp_name, ubulk_name = get_all_file_path(file)
        if not self.has_ubulk:
            ubulk_name = None
        
        with open(uexp_name, 'wb') as f:
            
            if self.version=='ff7r':
                self.write_uexp_ff7r(f)
            else:
                self.write_uexp(f)
            write_uint64(f, self.none_name_id)
            if self.version=='4.27':
                write_null(f)
            f.write(TextureUasset.UNREAL_SIGNATURE)
            size = f.tell()

        if self.has_ubulk:
            with open(ubulk_name, 'wb') as f:
                for data in self.ubulk_map_data:
                    f.write(data)

        
        self.uasset.exports[0].update(size -4, self.uasset_size)
        self.uasset.save(uasset_name, size)
        return uasset_name, uexp_name, ubulk_name

    def write_uexp_ff7r(self, f):

        max_width, max_height = self.get_max_size()
        uexp_map_num, ubulk_map_num = self.get_mipmap_num()
        uexp_map_data_size = 0
        for d in self.uexp_map_data:
            uexp_map_data_size += len(d)

        self.original_height=max(self.original_height, max_height)
        self.original_width=max(self.original_width, max_width)
        f.write(self.bin1)
        write_uint32(f, self.original_width)
        write_uint32(f, self.original_height)
        f.write(self.unk)
        write_uint64(f, self.type_name_id)

        new_end_offset = self.offset + uexp_map_data_size + uexp_map_num*32 + 16
        if self.has_ubulk:
            new_end_offset += ubulk_map_num*32
        write_uint32(f, new_end_offset)
        write_uint32(f, self.original_width)
        write_uint32(f, self.original_height)
        write_uint16(f, self.cube_flag)
        write_uint16(f, self.unk_int)
        write_str(f, self.type)

        if self.unk_int==TextureUasset.UBULK_FLAG_FF7R[1]:
            write_null(f)
            write_null(f)
            write_uint32(f, ubulk_map_num+self.unk_map_num)
        
        write_uint32(f, self.unk_map_num)
        write_uint32(f, uexp_map_num + ubulk_map_num)

        write_uint32(f, 1)
        write_uint32(f, 64)
        write_uint32(f, uexp_map_data_size)
        write_uint32(f, uexp_map_data_size)
        write_uint64(f, self.offset)

        for d in self.uexp_map_data:
            f.write(d)

        meta = self.uexp_map_meta
        max_width=meta[0].width
        max_height=meta[0].height
        write_uint32(f, max_width)
        write_uint32(f, max_height)

        write_uint32(f, self.cube_flag)
        write_uint32(f, uexp_map_num)

        #mip map meta data
        if self.has_ubulk:
            for meta in self.ubulk_map_meta:
                meta.write(f, self.uasset_size)

        for meta in self.uexp_map_meta:
            meta.write(f, self.uasset_size)

    def write_uexp(self, f):
        max_width, max_height = self.get_max_size()
        uexp_map_num, ubulk_map_num = self.get_mipmap_num()
        uexp_map_data_size = 0
        for d in self.uexp_map_data:
            uexp_map_data_size += len(d)+32
        if self.bin1 is not None:
            self.original_height=max(self.original_height, max_height)
            self.original_width=max(self.original_width, max_width)
            f.write(self.bin1)
            write_uint32(f, self.original_width)
            write_uint32(f, self.original_height)
        else:
            self.original_height=max_height
            self.original_width =max_width
        f.write(self.unk)
        write_uint64(f, self.type_name_id)
        new_end_offset = self.uasset_size+f.tell() + uexp_map_data_size+29+len(self.type)+ubulk_map_num*32 + (uexp_map_num+ubulk_map_num+2)*(self.version=='4.27')*4
        write_uint32(f, new_end_offset)
        if self.version=='4.27':
            write_null(f)
        
        write_uint32(f, self.original_width)
        write_uint32(f, self.original_height)
        write_uint16(f, self.cube_flag)
        write_uint16(f, self.unk_int)

        write_str(f, self.type)
        write_null(f)
        write_uint32(f, uexp_map_num+ubulk_map_num)
        if self.version=='4.27':
            offset = 0
        else:
            offset = -new_end_offset-8

        if self.has_ubulk:
            for data, meta in zip(self.ubulk_map_data, self.ubulk_map_meta):
                write_uint32(f, 1)
                write_uint32(f, TextureUasset.UBULK_FLAG[self.version=='4.27'][1])
                data_size = len(data)
                write_uint32(f, data_size)
                write_uint32(f, data_size)
                write_int64(f, offset)
                write_uint32(f, meta.width)
                write_uint32(f, meta.height)
                if self.version=='4.27':
                    write_uint32(f, 1)
                offset+=data_size
            
        for data, meta in zip(self.uexp_map_data, self.uexp_map_meta):
            write_uint32(f, 1)
            write_uint32(f, TextureUasset.UBULK_FLAG[self.version=='4.27'][0])
            write_uint32(f, len(data))
            write_uint32(f, len(data))
            write_uint64(f, self.uasset.size+f.tell()+8)
            f.write(data)
            write_uint32(f, meta.width)
            write_uint32(f, meta.height)
            if self.version=='4.27':
                write_uint32(f, 1)


    def unlink_ubulk(self):
        if not self.has_ubulk:
            return
        self.offset-=12
        self.has_ubulk=False
        self.ubulk_map_num=0
        print('ubulk has been unlinked.')

    def remove_mipmaps(self):
        uexp_map_num, ubulk_map_num = self.get_mipmap_num()
        old_mipmap_num = uexp_map_num + ubulk_map_num

        if self.has_ubulk:
            self.uexp_map_data = [self.ubulk_map_data[0]]
            self.uexp_map_meta = [self.ubulk_map_meta[0]]
            self.uexp_map_meta[0].to_uexp()
        else:
            self.uexp_map_data=[self.uexp_map_data[0]]
            self.uexp_map_meta=[self.uexp_map_meta[0]]

        self.unlink_ubulk()
        print('mipmaps have been removed.')
        print('  mipmap: {} -> 1'.format(old_mipmap_num))

    def inject_dds(self, dds):
        if '(signed)' in dds.header.format_name:
            raise RuntimeError('UE4 requires unsigned format but your dds is {}.'.format(dds.header.format_name))

        if dds.header.format_name!=self.format_name:
            raise RuntimeError('The format does not match. ({}, {})'.format(self.type, dds.header.format_name))

        if dds.header.texture_type!=self.texture_type:
            raise RuntimeError('Texture type does not match. ({}, {})'.format(self.texture_type, dds.header.texture_type))
        
        max_width, max_height = self.get_max_size()
        old_size = (max_width, max_height)
        uexp_map_num, ubulk_map_num = self.get_mipmap_num()
        old_mipmap_num = uexp_map_num + ubulk_map_num

        offset=0
        self.ubulk_map_data=[]
        self.ubulk_map_meta=[]
        self.uexp_map_data=[]
        self.uexp_map_meta=[]
        i=0

        for data, size in zip(dds.mipmap_data, dds.mipmap_size):
            if self.has_ubulk and i+1<len(dds.mipmap_data) and size[0]*size[1]>=1024**2:
                meta = MipmapMetadata(len(data), offset, size, False)
                offset+=len(data)
                self.ubulk_map_meta.append(meta)
                self.ubulk_map_data.append(data)
            else:
                meta = MipmapMetadata(0,0,size,True)
                self.uexp_map_data.append(data)
                self.uexp_map_meta.append(meta)
            i+=1

        if len(self.ubulk_map_meta)==0:
            self.has_ubulk=False

        max_width, max_height = self.get_max_size()
        new_size = (max_width, max_height)
        uexp_map_num, ubulk_map_num = self.get_mipmap_num()
        new_mipmap_num = uexp_map_num + ubulk_map_num

        print('dds has been injected.')
        print('  size: {} -> {}'.format(old_size, new_size))
        print('  mipmap: {} -> {}'.format(old_mipmap_num, new_mipmap_num))
        
        if new_mipmap_num>1 and (not is_power_of_2(max_width) or not is_power_of_2(max_height)):
            print('Warning: Mipmaps should have power of 2 as its width and height. ({}, {})'.format(max_width, max_height))
        if new_mipmap_num>1 and old_mipmap_num==1:
            print('Warning: The original texture has only 1 mipmap. But your dds has multiple mipmaps.')
            

    def print(self, verbose=False):
        if verbose:
            i=0
            if self.has_ubulk:
                for meta in self.ubulk_map_meta:
                    print('  Mipmap {}'.format(i))
                    meta.print(padding=4)
                    i+=1
            for meta in self.uexp_map_meta:
                print('  Mipmap {}'.format(i))
                meta.print(padding=4)
                i+=1
        if self.bin1 is not None:
            print('  original_width: {}'.format(self.original_width))
            print('  original_height: {}'.format(self.original_height))
        print('  format: {}'.format(self.type))
        print('  texture type: {}'.format(self.texture_type))
        print('  mipmap num: {}'.format(self.uexp_map_num + self.ubulk_map_num))
