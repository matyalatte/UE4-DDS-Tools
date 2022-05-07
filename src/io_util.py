import os, struct

def mkdir(dir):
    os.makedirs(dir, exist_ok=True)

def get_size(file):
    pos=file.tell()
    file.seek(0,2)
    size=file.tell()
    file.seek(pos)
    return size

def check(actual, expected, f=None, msg='Parse failed. Make sure you specified UE4 version correctly.'):
    if actual!=expected:
        if f is not None:
            print('offset: {}'.format(f.tell()))
        print('actual: {}'.format(actual))
        print('expected: {}'.format(expected))
        raise RuntimeError(msg)

def read_uint64(file):
    bin=file.read(8)
    return int.from_bytes(bin, "little")

def read_uint32(file):
    bin=file.read(4)
    return int.from_bytes(bin, "little")

def read_uint16(file):
    bin=file.read(2)
    return int.from_bytes(bin, "little")

def read_uint8(file):
    bin=file.read(1)
    return int(bin[0])

def read_int64(file):
    bin=file.read(8)
    return int.from_bytes(bin, "little", signed=True)

def read_int32(file):
    bin=file.read(4)
    return int.from_bytes(bin, "little", signed=True)

def read_array(file, read_func, len=None):
    if len is None:
        len = read_uint32(file)
    ary=[read_func(file) for i in range(len)]
    return ary

st_list = ['b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'f', 'd']
st_size = [1, 1, 2, 2, 4, 4, 8, 8, 4, 8]
def read_num_array(file, st, len=None):
    if st not in st_list:
        raise RuntimeError('Structure not found. {}'.format(st))
    if len is None:
        len = read_uint32(file)
    bin = file.read(st_size[st_list.index(st)]*len)
    return list(struct.unpack(st*len, bin))

def read_uint32_array(file, len=None):
    return read_num_array(file, 'I', len=len)

def read_uint16_array(file, len=None):
    return read_num_array(file, 'H', len=len)

def read_uint8_array(file, len=None):
    return read_num_array(file, 'B', len=len)

def read_int32_array(file, len=None):
    return read_num_array(file, 'i', len=len)

def read_str(file):
    num = read_uint32(file)
    if num==0:
        return None
    string = file.read(num-1).decode()
    file.seek(1,1)
    return string

def read_const_uint32(f, n, msg='Unexpected Value!'):
    const = read_uint32(f)
    check(const, n, f, msg)

def read_null(f, msg='Not NULL!'):
    read_const_uint32(f, 0, msg)

def read_null_array(f, len, msg='Not NULL!'):
    null=read_uint32_array(f, len=len)
    check(null, [0]*len, f, msg)

def read_struct_array(f, obj, len=None):
    if len is None:
        len = read_uint32(f)
    objects = [obj() for i in range(len)]
    list(map(lambda x: f.readinto(x), objects))
    return objects

def write_uint64(file, n):
    bin = n.to_bytes(8, byteorder="little")
    file.write(bin)

def write_uint32(file, n):
    bin = n.to_bytes(4, byteorder="little")
    file.write(bin)

def write_uint16(file, n):
    bin = n.to_bytes(2, byteorder="little")
    file.write(bin)

def write_uint8(file, n):
    bin = n.to_bytes(1, byteorder="little")
    file.write(bin)

def write_int64(file, n):
    bin = n.to_bytes(8, byteorder="little", signed=True)
    file.write(bin)

def write_int32(file, n):
    bin = n.to_bytes(4, byteorder="little", signed=True)
    file.write(bin)

def write_array(file, ary, write_func, with_length=False):
    if with_length:
        write_uint32(file, len(ary))
    for a in ary:
        write_func(file, a)

def write_uint32_array(file, ary, with_length=False):
    write_array(file, ary, write_uint32, with_length=with_length)

def write_uint16_array(file, ary, with_length=False):
    write_array(file, ary, write_uint16, with_length=with_length)

def write_uint8_array(file, ary, with_length=False):
    write_array(file, ary, write_uint8, with_length=with_length)

def write_int32_array(file, ary, with_length=False):
    write_array(file, ary, write_int32, with_length=with_length)

def write_str(file, s):
    num = len(s)+1
    write_uint32(file, num)
    str_byte = s.encode()
    file.write(str_byte + b'\x00')

def write_null(f):
    write_uint32(f, 0)

def write_null_array(f, len):
    write_uint32_array(f, [0]*len)

def compare(file1,file2):
    f1=open(file1, 'rb')
    f2=open(file2, 'rb')
    print('Comparing {} and {}...'.format(file1, file2))

    f1_size=get_size(f1)
    f2_size=get_size(f2)
    
    size=min(f1_size, f2_size)
    i=0
    f1_bin=f1.read()
    f2_bin=f2.read()
    f1.close()
    f2.close()

    if f1_size==f2_size and f1_bin==f2_bin:
        print('Same data!')
        return

    i=-1
    for b1, b2 in zip(f1_bin, f2_bin):
        i+=1
        if b1!=b2:
            break

    raise RuntimeError('Not same :{}'.format(i))
    