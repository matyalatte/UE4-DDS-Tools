from io_util import *
import ctypes as c

#classes for .uasset

#header of .uasset
class UassetHeader(c.LittleEndianStructure):
    HEAD = b'\xC1\x83\x2A\x9E'
    _pack_=1
    _fields_ = [ #193 bytes
        ("head", c.c_char*4), #Unreal Header (193,131,42,158)
        ("version", c.c_int32), #-version-1=6
        ("null", c.c_ubyte*16),
        ("file_size", c.c_uint32), #size of .uasset
        ("str_length", c.c_uint32), #5
        ("none", c.c_char*5), #'None '
        ("unk", c.c_char*4),
        ("name_count", c.c_uint32),
        ("name_offset", c.c_uint32),
        ("null2", c.c_ubyte*8),
        ("export_count", c.c_uint32),
        ("export_offset", c.c_uint32),
        ("import_count", c.c_uint32),
        ("import_offset", c.c_uint32),
        ("end_to_export", c.c_uint32),
        ("null3", c.c_ubyte*16),
        ("guid_hash", c.c_char*16),
        ("unk2", c.c_uint32),
        ("padding_count", c.c_uint32),
        ("name_count2", c.c_uint32), #name count again?
        ("null4", c.c_ubyte*36),
        ("unk3", c.c_uint64),
        ("padding_offset", c.c_uint32), #file data offset - 4
        ("file_length", c.c_uint32), #.uasset + .uexp - 4
        ("null5", c.c_ubyte*12),
        ("file_data_count", c.c_uint32),
        ("file_data_offset", c.c_uint32)
    ]

    def check(self):
        check(self.head, UassetHeader.HEAD)
        check(-self.version-1, 6)

    def print(self):
        print('Header info')
        print('  file size: {}'.format(self.file_size))
        print('  number of names: {}'.format(self.name_count))
        print('  name directory offset: 193')
        print('  number of exports: {}'.format(self.export_count))
        print('  export directory offset: {}'.format(self.export_offset))
        print('  number of imports: {}'.format(self.import_count))
        print('  import directory offset: {}'.format(self.import_offset))
        print('  end offset of export: {}'.format(self.end_to_export))
        print('  padding offset: {}'.format(self.padding_offset))
        print('  file length (uasset+uexp-4): {}'.format(self.file_length))
        print('  file data count: {}'.format(self.file_data_count))
        print('  file data offset: {}'.format(self.file_data_offset))

#import data of .uasset
class UassetImport(c.LittleEndianStructure): 
    _pack_=1
    _fields_ = [ #28 bytes
        ("parent_dir_id", c.c_uint64),
        ("class_id", c.c_uint64),
        ("parent_import_id", c.c_int32),
        ("name_id", c.c_uint64),
    ]

    def name_import(self, name_list):
        self.name = name_list[self.name_id]
        self.class_name = name_list[self.class_id]
        self.parent_dir = name_list[self.parent_dir_id]
        return self.name

    def print(self, padding=2):
        pad = ' '*padding
        print(pad+self.name)
        print(pad+'  class: '+self.class_name)
        print(pad+'  parent dir: '+self.parent_dir)
        #print(pad+'  parent import: '+parent)

def name_imports(imports, name_list):
    import_names = list(map(lambda x: x.name_import(name_list), imports))
    #import_parent = [import_names[-import_.parent_import_id-1] for import_ in imports]

    if 'Texture2D' in import_names:
        texture_type='2D'
    elif 'TextureCube' in import_names:
        texture_type='Cube'
    else:
        raise RuntimeError('Not texture assets!')
            
    return texture_type

#export data of .uasset
class UassetExport(c.LittleEndianStructure): 
    _pack_=1
    _fields_ = [ #104 bytes
        ("class_id", c.c_int32),
        ("null", c.c_uint32),
        ("import_id", c.c_int32),
        ("null2", c.c_uint32),
        ("name_id", c.c_uint64),
        ("unk_int", c.c_uint32),
        ("size", c.c_uint64),
        ("offset", c.c_uint32),
        ("unk", c.c_ubyte*64),
    ]

    def update(self, size, offset):
        self.size=size
        self.offset=offset

    def name_export(self, imports, name_list):
        self.name = name_list[self.name_id]
        self.class_name = imports[-self.class_id-1].name
        self.import_name = imports[-self.import_id-1].name

    def print(self, padding=2):
        pad=' '*padding
        print(pad+self.name)
        print(pad+'  class: {}'.format(self.class_name))
        print(pad+'  import: {}'.format(self.import_name))
        print(pad+'  size: {}'.format(self.size))
        print(pad+'  offset: {}'.format(self.offset))

class Uasset:

    def __init__(self, uasset_file, verbose=False):
        if uasset_file[-7:]!='.uasset':
            raise RuntimeError('Not .uasset. ({})'.format(uasset_file))

        if verbose:
            print('Loading '+uasset_file+'...')

        self.file=os.path.basename(uasset_file)[:-7]
        with open(uasset_file, 'rb') as f:
            self.size=get_size(f)

            #read header
            self.header=UassetHeader()
            f.readinto(self.header)
            self.header.check()
            if verbose:
                self.header.print()
                print('Name list')

            #read name table
            def read_names(f, i):
                name = read_str(f)
                hash = f.read(4)
                if verbose:
                    print('  {}: {}'.format(i, name))
                return name, hash
            names = [read_names(f, i) for i in range(self.header.name_count)]
            self.name_list = [x[0] for x in names]
            self.hash_list = [x[1] for x in names]

            #read imports
            self.imports=read_struct_array(f, UassetImport, len=self.header.import_count)
            self.texture_type = name_imports(self.imports, self.name_list)
            if verbose:
                print('Import')
                list(map(lambda x: x.print(), self.imports))

            #read exports
            self.exports=read_struct_array(f, UassetExport, len=self.header.export_count)
            list(map(lambda x: x.name_export(self.imports, self.name_list), self.exports))
            if verbose:
                print('Export')
                list(map(lambda x: x.print(), self.exports))

            #file data ids
            read_null_array(f, self.header.padding_count)
            check(self.header.padding_offset, f.tell())
            read_null(f)
            check(self.header.file_data_offset, f.tell())
            self.file_data_ids = read_int32_array(f, len=self.header.file_data_count)
            
            '''
            for i in self.file_data_ids:
                if i<0:
                    i = -i-1
                    print(self.imports[i].name)
                else:
                    print(self.name_list[i])
            '''
            
            check(f.tell(), self.size)
    
    def save(self, file, uexp_size):
        print('save :' + file)
        with open(file, 'wb') as f:
            #skip header part
            f.seek(193)

            #write name table
            for name, hash in zip(self.name_list, self.hash_list):
                write_str(f, name)
                f.write(hash)

            #write imports
            self.header.import_offset = f.tell()
            list(map(lambda x: f.write(x), self.imports))

            #skip exports part
            self.header.export_offset = f.tell()
            f.seek(len(self.exports)*104, 1)

            #file data ids
            write_null_array(f, self.header.padding_count+1)
            self.header.padding_offset = f.tell()-4
            self.header.file_data_offset = f.tell()
            write_int32_array(f, self.file_data_ids)
            self.header.uasset_size = f.tell()
            self.header.file_length=uexp_size+self.header.uasset_size-4
            self.header.name_count = len(self.name_list)
            self.header.name_count2 = len(self.name_list)

            #write header
            f.seek(0)
            f.write(self.header)

            #write exports
            f.seek(self.header.export_offset)
            offset = self.header.uasset_size
            for export in self.exports:
                export.update(export.size, offset)
                offset+=export.size
            list(map(lambda x: f.write(x), self.exports))
