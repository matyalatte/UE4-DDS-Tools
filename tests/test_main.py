import os
import shutil

import pytest

from . import util
from main import main


@pytest.mark.parametrize("json_args", util.get_test_cases("valid"))
def test_valid_mode(json_args):
    """Test uasset i/o."""
    json_args["mode"] = "valid"
    args = util.Args(json_args)
    main(args=args, texconv=util.get_texconv())


test_file = util.get_test_cases("files")[0]


@pytest.mark.parametrize("mode", ["parse", "check", "remove_mipmaps"])
def test_minor_modes(mode):
    """Test minor modes."""
    args = util.Args(test_file)
    args.mode = mode
    main(args=args, texconv=util.get_texconv())
    if mode == "remove_mipmaps":
        shutil.rmtree("test_out")


def test_convert():
    """Test convert mode."""
    args = util.Args(test_file)
    args.mode = "export"
    args.export_as = "png"
    main(args=args, texconv=util.get_texconv())
    uasset = os.path.basename(args.file)
    texture = ".".join(uasset.split(".")[:-1]) + "." + args.export_as
    args.file = os.path.join("test_out", texture)
    args.mode = "convert"
    args.conver_to = "jpg"
    main(args=args, texconv=util.get_texconv())
    shutil.rmtree("test_out")


@pytest.mark.parametrize("json_args", util.get_test_cases("folders"))
def test_inject_folder(json_args):
    """Test folder injection."""
    args = util.Args(json_args)
    args.mode = "export"
    main(args=args, texconv=util.get_texconv())
    args.texture = os.path.join("test_out", os.path.basename(args.file))
    args.mode = "inject"
    main(args=args, texconv=util.get_texconv())
    shutil.rmtree("test_out")


@pytest.mark.parametrize("json_args", util.get_test_cases("files"))
def test_inject_file(json_args):
    """Test file injection."""
    args = util.Args(json_args)
    args.mode = "export"
    main(args=args, texconv=util.get_texconv())
    uasset = os.path.basename(args.file)
    texture = ".".join(uasset.split(".")[:-1])
    args.texture = os.path.join("test_out", texture + "." + args.export_as)
    args.mode = "inject"
    main(args=args, texconv=util.get_texconv())
    shutil.rmtree("test_out")


@pytest.mark.parametrize("json_args", util.get_test_cases("options"))
def test_options(json_args):
    """Test file injection with some options."""
    args = util.Args(json_args)
    args.mode = "export"
    main(args=args, texconv=util.get_texconv())
    uasset = os.path.basename(args.file)
    texture = ".".join(uasset.split(".")[:-1])
    args.texture = os.path.join("test_out", texture + "." + args.export_as)
    args.mode = "inject"
    main(args=args, texconv=util.get_texconv())
    shutil.rmtree("test_out")


@pytest.mark.parametrize("json_args", util.get_test_cases("files"))
def test_offset_data(json_args):
    """Test if the tool can save offset data correctly."""
    args = util.Args(json_args)
    args.mode = "export"
    args.export_as = "png"
    args.force_uncompressed = True
    main(args=args, texconv=util.get_texconv())
    uasset = os.path.basename(args.file)
    texture = ".".join(uasset.split(".")[:-1])
    args.texture = os.path.join("test_out", texture + "." + args.export_as)
    args.mode = "inject"
    main(args=args, texconv=util.get_texconv())
    args.mode = "valid"
    args.file = os.path.join("test_out", uasset)
    main(args=args, texconv=util.get_texconv())
    shutil.rmtree("test_out")
