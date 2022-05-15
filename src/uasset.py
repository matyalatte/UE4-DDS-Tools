from io_util import *
import ctypes as c

#classes for .uasset

#header of .uasset
class UassetHeader: #185 ~ 193 bytes
    HEAD = b'\xC1\x83\x2A\x9E'

    def __init__(self, f, version):
        check(f.read(4), UassetHeader.HEAD)
        self.version = read_int32(f)
        check(-self.version-1, 6 - (version=='4.13'))
        self.null = f.read(16)
        self.uasset_size = read_uint32(f)
        check(read_str(f), "None")
        self.unk = f.read(4)
        self.name_count = read_uint32(f)
        self.name_offset = read_uint32(f)
        read_null_array(f, 2)
        self.export_count = read_uint32(f)
        self.export_offset = read_uint32(f)
        self.import_count = read_uint32(f)
        self.import_offset = read_uint32(f)
        self.end_to_export = read_uint32(f)
        if version in ['4.14', '4.13']:
            read_null(f)
            f.seek(4, 1)  #padding offset
            read_null(f)
        else:
            read_null_array(f, 4)
        self.guid = f.read(16)
        self.unk2 = read_uint32(f)
        self.padding_count = read_uint32(f)
        check(read_uint32(f), self.name_count)
        read_null_array(f, 9)
        self.unk3 = read_uint32(f)
        read_null(f)
        if version=='4.13':
            read_null(f)
        self.padding_offset = read_uint32(f) #file data offset - 4
        self.file_length = read_uint32(f) #.uasset + .uexp - 4
        read_null_array(f, 3)
        if version=='4.13':
            return
        self.file_data_count = read_int32(f)
        self.file_data_offset = read_uint32(f)

    def write(self, f, version):
        f.write(UassetHeader.HEAD)
        write_int32(f, self.version)
        f.write(self.null)
        write_uint32(f, self.uasset_size)
        write_str(f, "None")
        f.write(self.unk)
        write_uint32(f, self.name_count)
        write_uint32(f, self.name_offset)
        write_null_array(f, 2)
        write_uint32(f, self.export_count)
        write_uint32(f, self.export_offset)
        write_uint32(f, self.import_count)
        write_uint32(f, self.import_offset)
        write_uint32(f, self.end_to_export)
        if version in ['4.14', '4.13']:
            write_null(f)
            write_uint32(f, self.padding_offset)
            write_null(f)
        else:
            write_null_array(f, 4)
        f.write(self.guid)
        write_uint32(f, self.unk2)
        write_uint32(f, self.padding_count)
        write_uint32(f, self.name_count)
        write_null_array(f, 9)
        write_uint32(f, self.unk3)
        write_null(f)
        if version=='4.13':
            write_null(f)
        write_uint32(f, self.padding_offset)
        write_uint32(f, self.file_length)
        write_null_array(f, 3)
        if version=='4.13':
            return
        write_int32(f, self.file_data_count)
        write_uint32(f, self.file_data_offset)

    def print(self):
        print('Header info')
        print('  file size: {}'.format(self.uasset_size))
        print('  number of names: {}'.format(self.name_count))
        print('  name directory offset: 193')
        print('  number of exports: {}'.format(self.export_count))
        print('  export directory offset: {}'.format(self.export_offset))
        print('  number of imports: {}'.format(self.import_count))
        print('  import directory offset: {}'.format(self.import_offset))
        print('  end offset of export: {}'.format(self.end_to_export))
        print('  padding offset: {}'.format(self.padding_offset))
        print('  file length (uasset+uexp-4): {}'.format(self.file_length))
        #print('  file data count: {}'.format(self.file_data_count))
        #print('  file data offset: {}'.format(self.file_data_offset))

#import data of .uasset
class UassetImport(c.LittleEndianStructure): 
    _pack_=1
    _fields_ = [ #28 bytes
        ("parent_dir_id", c.c_uint64),
        ("class_id", c.c_uint64),
        ("parent_import_id", c.c_int32),
        ("name_id", c.c_uint32),
        ("unk", c.c_uint32),
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
class UassetExport: #80 ~ 104 bytes
    def __init__(self, f, version):
        self.class_id = read_int32(f)
        if version!='4.13':
            read_null(f)
        self.import_id = read_int32(f)
        read_null(f)
        self.name_id = read_uint32(f)
        self.unk_int = read_uint32(f)
        self.unk_int2 = read_uint32(f)
        if version in ['4.15', '4.14', '4.13']:
            self.size=read_uint32(f)
        else:
            self.size=read_uint64(f)
        self.offset = read_uint32(f)
        self.unk = f.read(64-4*(version in ['4.15', '4.14']) - 24*(version=='4.13'))

    def write(self, f, version):
        write_int32(f, self.class_id)
        if version!='4.13':
            write_null(f)
        write_int32(f, self.import_id)
        write_null(f)
        write_uint32(f, self.name_id)
        write_uint32(f, self.unk_int)
        write_uint32(f, self.unk_int2)
        if version in ['4.15', '4.14', '4.13']:
            write_uint32(f, self.size)
        else:
            write_uint64(f, self.size)
        write_uint32(f, self.offset)
        f.write(self.unk)

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

    def __init__(self, uasset_file, version, verbose=False):
        if uasset_file[-7:]!='.uasset':
            raise RuntimeError('Not .uasset. ({})'.format(uasset_file))

        if verbose:
            print('Loading '+uasset_file+'...')
        self.version=version
        self.file=os.path.basename(uasset_file)[:-7]
        with open(uasset_file, 'rb') as f:

            #read header
            self.header=UassetHeader(f, self.version)

            self.nouexp = self.version in ['4.15', '4.14', '4.13']
            self.size=self.header.uasset_size
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
            self.exports=[UassetExport(f, self.version) for i in range(self.header.export_count)]
            list(map(lambda x: x.name_export(self.imports, self.name_list), self.exports))
            
            if verbose:
                print('Export')
                list(map(lambda x: x.print(), self.exports))
            #file data ids
            read_null_array(f, self.header.padding_count)
            check(self.header.padding_offset, f.tell())
            read_null(f)
            if not self.nouexp:
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
            f.seek(193 - 4 * (self.version == '4.14') -  8 * (self.version == '4.13'))

            #write name table
            for name, hash in zip(self.name_list, self.hash_list):
                write_str(f, name)
                f.write(hash)

            #write imports
            self.header.import_offset = f.tell()
            list(map(lambda x: f.write(x), self.imports))

            #skip exports part
            self.header.export_offset = f.tell()
            list(map(lambda x: x.write(f, self.version), self.exports))
            if self.version not in ['4.15', '4.14']:
                self.header.end_to_export = f.tell()

            #file data ids
            write_null_array(f, self.header.padding_count)
            self.header.padding_offset = f.tell()

            write_null(f)
            self.header.file_data_offset = f.tell()
            if not self.nouexp:
                write_int32_array(f, self.file_data_ids)
            self.header.uasset_size = f.tell()
            self.header.file_length=uexp_size+self.header.uasset_size-4
            self.header.name_count = len(self.name_list)

            #write header
            f.seek(0)
            self.header.write(f, self.version)

            #write exports
            f.seek(self.header.export_offset)
            offset = self.header.uasset_size
            for export in self.exports:
                export.update(export.size, offset)
                offset+=export.size
            list(map(lambda x: x.write(f, self.version), self.exports))
