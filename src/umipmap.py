from io_util import *
import ctypes as c

#mipmap class for texture asset
class Umipmap(c.LittleEndianStructure):
    _pack_=1
    _fields_ = [
        #("one", c.c_uint32), #1
        ("ubulk_flag", c.c_uint16), #1281->ubulk, 72->uexp, 32 or 64->ff7r uexp
        ("unk_flag", c.c_uint16), #ubulk and 1->ue4.27 or ff7r
        ("data_size", c.c_uint32), #0->ff7r uexp
        ("data_size2", c.c_uint32), #data size again
        ("offset", c.c_uint64)
        #data, c_ubyte*
        #width, c_uint32
        #height, c_uint32
        #if version>=4.20:
        #   depth, c_uint32 (==1 for 2d and cube. maybe !=1 for 3d textures)
    ]

    def __init__(self, version, bl3=False):
        self.version = version
        self.bl3 = bl3

    def update(self, data, size, uexp):
        self.uexp=uexp
        self.meta=False
        self.data_size=len(data)
        self.data_size2=len(data)
        self.data = data
        self.offset=0
        self.width=size[0]
        self.height=size[1]
        self.pixel_num = self.width*self.height

    def read(f, version, bl3=False):
        mip = Umipmap(version, bl3)
        if version!='5.0':
            read_const_uint32(f, 1)
        f.readinto(mip)
        mip.uexp = mip.ubulk_flag not in [1025, 1281, 1]
        mip.meta = mip.ubulk_flag==32
        if mip.uexp:
            mip.data = f.read(mip.data_size)
        
        if bl3:
            read_int = read_uint16
        else:
            read_int = read_uint32

        mip.width = read_int(f)
        mip.height = read_int(f)
        if version in ['4.22', '4.25', '4.27', '5.0']:
            depth = read_int(f)
            check(depth, 1 ,msg='3d texture is unsupported.')

        check(mip.data_size, mip.data_size2)
        mip.pixel_num = mip.width*mip.height
        return mip
    
    def print(self, padding=2):
        pad = ' '*padding
        print(pad + 'file: ' + 'uexp'*self.uexp + 'ubluk'*(not self.uexp))
        print(pad + 'data size: {}'.format(self.data_size))
        print(pad + 'offset: {}'.format(self.offset))
        print(pad + 'width: {}'.format(self.width))
        print(pad + 'height: {}'.format(self.height))

    def write(self, f, uasset_size):
        if self.uexp:
            if self.meta:
                self.ubulk_flag=32
            else:
                self.ubulk_flag=72 if self.version!='ff7r' else 64
            self.unk_flag = 0
        else:
            if self.version=='4.13':
                self.ubulk_flag=1
            elif self.version in ['4.15', '4.14']:
                self.ubulk_flag=1025
            else:
                self.ubulk_flag=1281
            self.unk_flag = self.version in ['5.0', '4.27', 'ff7r']
        if self.uexp and self.meta:
            self.data_size=0
            self.data_size2=0

        if self.version!='5.0':
            write_uint32(f, 1)
        f.write(self)
        if self.uexp and not self.meta:
            f.write(self.data)

        if self.bl3:
            write_int = write_uint16
        else:
            write_int = write_uint32

        write_int(f, self.width)
        write_int(f, self.height)
        if self.version in ['4.22', '4.25', '4.27', '5.0']:
            write_int(f, 1)