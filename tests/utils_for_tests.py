import json
import os


class Args:
    def __init__(self, json_args={}):
        self.file = None
        self.texture = None
        self.save_folder = "test_out"
        self.mode = "inject"
        self.version = None
        self.export_as = "dds"
        self.convert_to = "tga"
        self.no_mipmaps = False
        self.force_uncompressed = False
        self.disable_tempfile = False
        self.skip_non_texture = True
        self.image_filter = "linear"
        self.save_detected_version = False
        self.max_workers = -1

        if json_args != {}:
            self.init_with_json(json_args)

    def init_with_json(self, j):
        keys = vars(self).keys()
        for k in keys:
            if k in j:
                setattr(self, k, j[k])


def read_json(json_path):
    if not os.path.exists(json_path):
        return {}
    with open(json_path, encoding='utf-8') as f:
        return json.load(f)


def read_test_cases(json_name):
    json_path = os.path.join(os.path.dirname(__file__), json_name)
    return read_json(json_path)


test_cases = read_test_cases("test_cases.json")
local_test_cases = read_test_cases("local_test_cases.json")


def get_test_cases(key):
    cases = []
    if key in test_cases:
        cases += test_cases[key]
    if key in local_test_cases:
        cases += local_test_cases[key]
    return cases
