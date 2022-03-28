
from io_util import *

class UassetHeader:
    HEAD = b'\xC1\x83\x2A\x9E'

    def __init__(self, f):
        head=f.read(4)
        check(head, UassetHeader.HEAD, f, 'NOT a uasset file.')
        self.version=-read_int32(f)-1
        check(self.version, 6, f, 'Unsupported version. (version {})'.format(self.version))
        read_null_array(f, 4, 'Parse Failed.')
        self.file_size=read_uint32(f)
        none=read_str(f)
        check(none, 'None', f, 'Parse Failed.')
        self.unk_ary=read_uint8_array(f, len=4)

        self.name_num = read_uint32(f)
        self.name_offset = read_uint32(f)
        check(self.name_offset, 193, f, 'Parse Failed.')
        read_null_array(f, 2, 'Parse Failed.')

        self.export_num = read_uint32(f)
        self.export_offset = read_uint32(f)
        self.import_num = read_uint32(f)
        self.import_offset = read_uint32(f)
        self.unk1=f.read(4)
        read_null_array(f, 4, 'Parse Failed.')

        self.guid_hash=f.read(16)

        self.unk2=f.read(8)

        name_num=read_uint32(f)
        check(name_num, self.name_num, f, 'Parse Failed.')
        read_null_array(f, 9, 'Parse Failed.')
        self.unk3=f.read(4)
        read_null(f, 'Parse Failed.')
        self.padding_offset = read_uint32(f)
        self.file_length=read_uint32(f)
        read_null_array(f, 3, 'Parse Failed.')
        self.unk4=f.read(4)
        self.file_data_offset = read_uint32(f)

    def read(f):
        return UassetHeader(f)
    
    def write(f, header):
        f.write(UassetHeader.HEAD)
        write_int32(f, -(header.version+1))
        write_null_array(f, 4)
        write_uint32(f, header.file_size)
        write_str(f, 'None')
        write_uint8_array(f, header.unk_ary)
        write_uint32(f, header.name_num)
        write_uint32(f, header.name_offset)
        write_null_array(f, 2)
        write_uint32(f, header.export_num)
        write_uint32(f, header.export_offset)
        write_uint32(f, header.import_num)
        write_uint32(f, header.import_offset)
        f.write(header.unk1)
        write_null_array(f, 4)
        f.write(header.guid_hash)
        f.write(header.unk2)
        write_uint32(f, header.name_num)
        write_null_array(f, 9)
        f.write(header.unk3)
        write_null(f)
        write_uint32(f, header.padding_offset)
        write_uint32(f, header.file_length)
        write_null_array(f, 3)
        f.write(header.unk4)
        write_uint32(f, header.file_data_offset)


    def print(self):
        print('Header info')
        print('  version: {}'.format(self.version))
        print('  file size: {}'.format(self.file_size))
        print('  number of names: {}'.format(self.name_num))
        print('  name directory offset: {}'.format(self.name_offset))
        print('  number of exports: {}'.format(self.export_num))
        print('  export directory offset: {}'.format(self.export_offset))
        print('  number of imports: {}'.format(self.import_num))
        print('  import directory offset: {}'.format(self.import_offset))
        print('  guid hash: {}'.format(self.guid_hash))
        print('  padding offset: {}'.format(self.padding_offset))
        print('  file length (uasset+uexp-4): {}'.format(self.file_length))
        print('  file data offset: {}'.format(self.file_data_offset))

class UassetImport: #28 bytes
    def __init__(self, f):
        self.bin1=f.read(8)
        self.class_id=read_uint32(f)
        self.bin2=f.read(8)
        self.name_id=read_uint32(f)
        self.bin3=f.read(4)
        self.material=False

    def read(f):
        return UassetImport(f)
    
    def write(f, import_):
        f.write(import_.bin1)
        write_uint32(f, import_.class_id)
        f.write(import_.bin2)
        write_uint32(f, import_.name_id)
        f.write(import_.bin3)

    def name_imports(imports, name_list):
        texture_type=None
        for import_ in imports:
            import_.name=name_list[import_.name_id]
            import_.class_name=name_list[import_.class_id]
            if import_.name=='Texture2D':
                texture_type='2D'
            if import_.name=='TextureCube':
                texture_type='Cube'
            
        if texture_type is None:
            raise RuntimeError('Not texture assets!')
        return texture_type

    def print(self, padding=2):
        pad=' '*padding
        print(pad+self.name)
        print(pad+'  class: '+self.class_name)

class UassetExport: #104 bytes
    KNOWN_EXPORTS=[]
    IGNORE=[]
    #'BodySetup'
    def __init__(self, f):
        self.bin1=f.read(16)
        self.name_id=read_uint32(f)
        self.bin2=f.read(8)
        self.size=read_uint32(f)
        read_null(f)
        self.offset=read_uint32(f)
        self.bin3=f.read(64)

    def read(f):
        return UassetExport(f)
    
    def write(f, export):
        f.write(export.bin1)
        write_uint32(f, export.name_id)
        f.write(export.bin2)
        write_uint32(f, export.size)
        write_null(f)
        write_uint32(f, export.offset)
        f.write(export.bin3)

    def update(self, size, offset):
        self.size=size
        self.offset=offset

    def name_exports(exports, name_list, file_name):
        for export in exports:
            name=name_list[export.name_id]
            export.id=-1
            export.ignore=False

            #if name in UassetExport.KNOWN_EXPORTS:
            #    export.id=UassetExport.KNOWN_EXPORTS.index(name)
            #    export.ignore=UassetExport.IGNORE[export.id]
            #elif name in file_name:
            #    export.id=-1
            #    export.ignore=False
            #else:
            #    raise RuntimeError('Unsupported exports. ({}, {})'.format(name, file_name))

            export.name=name

    def read_uexp(self, f):
        self.bin=f.read(self.size)

    def write_uexp(self, f):
        f.write(self.bin)

    def print(self, padding=2):
        pad=' '*padding
        print(pad+self.name)
        print(pad+'  size: {}'.format(self.size))
        print(pad+'  offset: {}'.format(self.offset))


class Uasset:

    def __init__(self, uasset_file, verbose=False):
        if uasset_file[-7:]!='.uasset':
            raise RuntimeError('Not .uasset. ({})'.format(uasset_file))

        if verbose:
            print('Loading '+uasset_file+'...')

        self.file=os.path.basename(uasset_file)[:-7]
        f=open(uasset_file, 'rb')
        self.size=get_size(f)
        self.header=UassetHeader.read(f)
        self.bin1 = f.read(self.header.name_offset-193)
        if verbose:
            print('size: {}'.format(self.size))
            self.header.print()
            print('Name list')
        
        self.name_list = []
        self.flag_list = []
        for i in range(self.header.name_num):
            name = read_str(f)
            flag = f.read(4)
            if verbose:
                print('  {}: {}'.format(i, name))
            self.name_list.append(name)
            self.flag_list.append(flag)
        offset=f.tell()
        self.bin2=f.read(self.header.import_offset-offset)

        self.imports=read_array(f, UassetImport.read, len=self.header.import_num)
        self.texture_type = UassetImport.name_imports(self.imports, self.name_list)
        if verbose:
            print('Import')
            for import_ in self.imports:
                import_.print()

        offset=f.tell()
        self.bin3=f.read(self.header.export_offset-offset)
        self.exports=read_array(f, UassetExport.read, len=self.header.export_num)
        UassetExport.name_exports(self.exports, self.name_list, self.file)

        if verbose:
            print('Export')
            for export in self.exports:
                export.print()

        self.bin4=f.read()
        f.close()
    
    def save(self, file, uexp_size):
        self.header.file_length=uexp_size+self.size-4
        print('save :' + file)
        with open(file, 'wb') as f:
            UassetHeader.write(f, self.header)
            f.write(self.bin1)
            for name, flag in zip(self.name_list, self.flag_list):
                write_str(f, name)
                f.write(flag)

            f.write(self.bin2)
            write_array(f, self.imports, UassetImport.write)                
            f.write(self.bin3)
            write_array(f, self.exports, UassetExport.write)
            f.write(self.bin4)