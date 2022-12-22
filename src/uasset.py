'''Classes for .uasset'''
import os
import ctypes as c
import io_util
from crc import generate_hash


class UassetHeader:  # 185 ~ 193 bytes
    HEAD = b'\xC1\x83\x2A\x9E'

    def __init__(self, f, version):
        io_util.check(f.read(4), UassetHeader.HEAD)
        self.version = io_util.read_int32(f)
        file_version = -self.version - 1
        if (file_version < 5) or (file_version > 7):
            raise RuntimeError(f"Unsupported .uasset version ({file_version})")
        io_util.check(file_version, 6 - (version == '4.13') + (version == '5.0'))
        self.null = f.read(16 + 4 * (version == '5.0'))
        self.uasset_size = io_util.read_uint32(f)
        io_util.check(io_util.read_str(f), "None")
        self.pkg_flags = io_util.read_uint32(f)  # 00 20 00 00: unversioned header flag
        self.unversioned = (self.pkg_flags & 8192) != 0
        self.name_count = io_util.read_uint32(f)
        self.name_offset = io_util.read_uint32(f)
        io_util.read_null_array(f, 2)
        self.export_count = io_util.read_uint32(f)
        self.export_offset = io_util.read_uint32(f)
        self.import_count = io_util.read_uint32(f)
        self.import_offset = io_util.read_uint32(f)
        self.end_to_export = io_util.read_uint32(f)
        if version in ['4.14', '4.13']:
            io_util.read_null(f)
            f.seek(4, 1)  # padding offset
            io_util.read_null(f)
        else:
            io_util.read_null_array(f, 4)
        self.guid = f.read(16)
        self.unk2 = io_util.read_uint32(f)
        self.padding_count = io_util.read_uint32(f)
        io_util.check(io_util.read_uint32(f), self.name_count)
        io_util.read_null_array(f, 9)
        self.unk3 = io_util.read_uint32(f)
        io_util.read_null(f)
        if version == '4.13':
            io_util.read_null(f)
        self.padding_offset = io_util.read_uint32(f)  # file data offset - 4
        self.file_length = io_util.read_uint32(f)  # .uasset + .uexp - 4
        io_util.read_null_array(f, 3)
        if version == '4.13':
            return
        self.file_data_count = io_util.read_int32(f)
        self.file_data_offset = io_util.read_uint32(f)
        if version == '5.0':
            self.unk_count = io_util.read_uint32(f)
            for i in range(self.unk_count):
                io_util.check(io_util.read_int32(f), -1)

    def write(self, f, version):
        f.write(UassetHeader.HEAD)
        io_util.write_int32(f, self.version)
        f.write(self.null)
        io_util.write_uint32(f, self.uasset_size)
        io_util.write_str(f, "None")
        io_util.write_uint32(f, self.pkg_flags)
        io_util.write_uint32(f, self.name_count)
        io_util.write_uint32(f, self.name_offset)
        io_util.write_null_array(f, 2)
        io_util.write_uint32(f, self.export_count)
        io_util.write_uint32(f, self.export_offset)
        io_util.write_uint32(f, self.import_count)
        io_util.write_uint32(f, self.import_offset)
        io_util.write_uint32(f, self.end_to_export)
        if version in ['4.14', '4.13']:
            io_util.write_null(f)
            io_util.write_uint32(f, self.padding_offset)
            io_util.write_null(f)
        else:
            io_util.write_null_array(f, 4)
        f.write(self.guid)
        io_util.write_uint32(f, self.unk2)
        io_util.write_uint32(f, self.padding_count)
        io_util.write_uint32(f, self.name_count)
        io_util.write_null_array(f, 9)
        io_util.write_uint32(f, self.unk3)
        io_util.write_null(f)
        if version == '4.13':
            io_util.write_null(f)
        io_util.write_uint32(f, self.padding_offset)
        io_util.write_uint32(f, self.file_length)
        io_util.write_null_array(f, 3)
        if version == '4.13':
            return
        io_util.write_int32(f, self.file_data_count)
        io_util.write_uint32(f, self.file_data_offset)
        if version == '5.0':
            io_util.write_uint32(f, self.unk_count)
            for i in range(self.unk_count):
                io_util.write_int32(f, -1)

    def print(self):
        print('Header info')
        print(f'  file size: {self.uasset_size}')
        print(f'  number of names: {self.name_count}')
        print('  name directory offset: 193')
        print(f'  number of exports: {self.export_count}')
        print(f'  export directory offset: {self.export_offset}')
        print(f'  number of imports: {self.import_count}')
        print(f'  import directory offset: {self.import_offset}')
        print(f'  end offset of export: {self.end_to_export}')
        print(f'  padding offset: {self.padding_offset}')
        print(f'  file length (uasset+uexp-4): {self.file_length}')
        # print('  file data count: {}'.format(self.file_data_count))
        # print('  file data offset: {}'.format(self.file_data_offset))


class UassetImport(c.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [  # 28 bytes
        ("parent_dir_id", c.c_uint64),
        ("class_id", c.c_uint64),
        ("parent_import_id", c.c_int32),
        ("name_id", c.c_uint32),
        ("unk", c.c_uint32),
    ]

    @staticmethod
    def read(f, version):
        imp = UassetImport()
        f.readinto(imp)
        if version == '5.0':
            imp.unk2 = io_util.read_uint32(f)
        return imp

    def write(self, f, version):
        f.write(self)
        if version == '5.0':
            io_util.write_uint32(f, self.unk2)

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
        # print(pad+'  parent import: '+parent)


def name_imports(imports, name_list):
    import_names = list(map(lambda x: x.name_import(name_list), imports))
    # import_parent = [import_names[-import_.parent_import_id-1] for import_ in imports]

    if 'Texture2D' in import_names:
        texture_type = '2D'
    elif 'TextureCube' in import_names:
        texture_type = 'Cube'
    else:
        raise RuntimeError('Not texture assets!')

    return texture_type


class UassetExport:  # 80 ~ 104 bytes
    def __init__(self, f, version):
        self.class_id = io_util.read_int32(f)
        if version != '4.13':
            io_util.read_null(f)
        self.import_id = io_util.read_int32(f)
        io_util.read_null(f)
        self.name_id = io_util.read_uint32(f)
        self.unk_int = io_util.read_uint32(f)
        self.unk_int2 = io_util.read_uint32(f)
        if version in ['4.15', '4.14', '4.13']:
            self.size = io_util.read_uint32(f)
        else:
            self.size = io_util.read_uint64(f)
        self.offset = io_util.read_uint32(f)
        self.unk = f.read(64 - 4 * (version in ['4.15', '4.14']) - 24 * (version == '4.13') + 4 * (version == '5.0'))

    def write(self, f, version):
        io_util.write_int32(f, self.class_id)
        if version != '4.13':
            io_util.write_null(f)
        io_util.write_int32(f, self.import_id)
        io_util.write_null(f)
        io_util.write_uint32(f, self.name_id)
        io_util.write_uint32(f, self.unk_int)
        io_util.write_uint32(f, self.unk_int2)
        if version in ['4.15', '4.14', '4.13']:
            io_util.write_uint32(f, self.size)
        else:
            io_util.write_uint64(f, self.size)
        io_util.write_uint32(f, self.offset)
        f.write(self.unk)

    def update(self, size, offset):
        self.size = size
        self.offset = offset

    def name_export(self, imports, name_list):
        self.name = name_list[self.name_id]
        self.class_name = imports[-self.class_id-1].name
        self.import_name = imports[-self.import_id-1].name

    def print(self, padding=2):
        pad = ' ' * padding
        print(pad+self.name)
        print(pad+f'  class: {self.class_name}')
        print(pad+f'  import: {self.import_name}')
        print(pad+f'  size: {self.size}')
        print(pad+f'  offset: {self.offset}')


class Uasset:
    def __init__(self, uasset_file, version, verbose=False):
        if uasset_file[-7:] != '.uasset':
            raise RuntimeError(f'Not .uasset. ({uasset_file})')

        if verbose:
            print('Loading '+uasset_file+'...')
        self.version = version
        self.file = os.path.basename(uasset_file)[:-7]

        with open(uasset_file, 'rb') as f:
            # read header
            self.header = UassetHeader(f, self.version)

            self.nouexp = self.version in ['4.15', '4.14', '4.13']
            self.size = self.header.uasset_size
            if verbose:
                self.header.print()
                print('Name list')

            # read name table
            def read_names(f, i):
                name = io_util.read_str(f)
                hash = f.read(4)
                if verbose:
                    print('  {}: {}'.format(i, name))
                return name, hash
            names = [read_names(f, i) for i in range(self.header.name_count)]
            self.name_list = [x[0] for x in names]
            self.hash_list = [x[1] for x in names]

            # read imports
            self.imports = [UassetImport.read(f, self.version) for i in range(self.header.import_count)]
            self.texture_type = name_imports(self.imports, self.name_list)
            if verbose:
                print('Import')
                list(map(lambda x: x.print(), self.imports))

            # read exports
            self.exports = [UassetExport(f, self.version) for i in range(self.header.export_count)]
            list(map(lambda x: x.name_export(self.imports, self.name_list), self.exports))

            if verbose:
                print('Export')
                list(map(lambda x: x.print(), self.exports))

            # file data ids
            io_util.read_null_array(f, self.header.padding_count)
            io_util.check(self.header.padding_offset, f.tell())
            io_util.read_null(f)
            if not self.nouexp:
                io_util.check(self.header.file_data_offset, f.tell())
                self.file_data_ids = io_util.read_int32_array(f, len=self.header.file_data_count)

            '''
            for i in self.file_data_ids:
                if i<0:
                    i = -i-1
                    print(self.imports[i].name)
                else:
                    print(self.name_list[i])
            '''

            io_util.check(f.tell(), self.size)

    def save(self, file, uexp_size):
        print('save :' + file)
        with open(file, 'wb') as f:
            # skip header part
            f.seek(self.header.name_offset)

            # write name table
            for name, hash in zip(self.name_list, self.hash_list):
                io_util.write_str(f, name)
                f.write(hash)

            # write imports
            self.header.import_offset = f.tell()
            list(map(lambda x: x.write(f, self.version), self.imports))

            # skip exports part
            self.header.export_offset = f.tell()
            list(map(lambda x: x.write(f, self.version), self.exports))
            if self.version not in ['4.15', '4.14']:
                self.header.end_to_export = f.tell()

            # file data ids
            io_util.write_null_array(f, self.header.padding_count)
            self.header.padding_offset = f.tell()

            io_util.write_null(f)
            self.header.file_data_offset = f.tell()
            if not self.nouexp:
                io_util.write_int32_array(f, self.file_data_ids)
            self.header.uasset_size = f.tell()
            self.header.file_length = uexp_size+self.header.uasset_size-4
            self.header.name_count = len(self.name_list)

            # write header
            f.seek(0)
            self.header.write(f, self.version)

            # write exports
            f.seek(self.header.export_offset)
            offset = self.header.uasset_size
            for export in self.exports:
                export.update(export.size, offset)
                offset += export.size
            list(map(lambda x: x.write(f, self.version), self.exports))

    def update_name_list(self, i, new_name):
        self.name_list[i] = new_name
        self.hash_list[i] = generate_hash(new_name)
