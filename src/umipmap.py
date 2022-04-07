from io_util import *
import ctypes as c

#mipmap class for texture asset
class Umipmap(c.LittleEndianStructure):
    _pack_=1
    _fields_ = [
        ("one", c.c_uint32), #1
        ("ubulk_flag", c.c_uint16), #1281->ubulk, 72->uexp, 32 or 64->ff7r uexp
        ("unk_flag", c.c_uint16), #ubulk and 1->ue4.27 or ff7r
        ("data_size", c.c_uint32), #0->ff7r uexp
        ("data_size2", c.c_uint32), #data size again
        ("offset", c.c_uint64)
        #data, c_ubyte*
        #width, c_uint32
        #height, c_uint32
        #if version==4.27 or bloodstained:
        #   null, c_uint32
    ]

    def __init__(self, version):
        self.version = version

    def update(self, data, size, uexp):
        self.uexp=uexp
        self.data_size=len(data)
        self.data_size2=len(data)
        self.data = data
        self.offset=0
        self.width=size[0]
        self.height=size[1]
        self.pixel_num = self.width*self.height
        self.one=1

    def read(f, version):
        mip = Umipmap(version)
        f.readinto(mip)
        mip.uexp = mip.ubulk_flag!=1281
        if mip.uexp:
            mip.data = f.read(mip.data_size)
        mip.width = read_uint32(f)
        mip.height = read_uint32(f)
        if version in ['4.27', 'bloodstained']:
            read_const_uint32(f, 1)
        check(mip.one, 1)
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
            self.ubulk_flag=72 - 40*(self.version=='ff7r') - 8*(self.version=='ff7r_bulk')
            self.unk_flag = 0
        else:
            self.ubulk_flag=1281
            self.unk_flag = self.version in ['4.27', 'ff7r']
        if self.uexp and self.version=='ff7r':
            self.data_size=0
            self.data_size2=0
        f.write(self)
        if self.uexp and self.version!='ff7r':
            f.write(self.data)

        write_uint32(f, self.width)
        write_uint32(f, self.height)
        if self.version in ['4.27', 'bloodstained']:
            write_uint32(f, 1)