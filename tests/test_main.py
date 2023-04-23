"""Tests for main.py"""
import os
import shutil

import pytest

from . import utils_for_tests as util
from main import main, get_config


def base(json_args):
    """Base function for tests."""
    args = util.Args(json_args)
    main(args=args, texconv=util.get_texconv())


@pytest.mark.parametrize("json_args", util.get_test_cases("valid"))
def test_valid_mode(json_args):
    """Test uasset i/o."""
    json_args["mode"] = "valid"
    base(json_args)


@pytest.mark.parametrize("json_args", util.get_test_cases("valid_error"))
def test_valid_mode_fail(json_args):
    """Test uasset i/o."""
    with pytest.raises(Exception) as e:
        json_args["mode"] = "valid"
        base(json_args)
    assert str(e.value) == json_args["error"]


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


@pytest.mark.parametrize("json_args", util.get_test_cases("save_version"))
def test_save_version(json_args):
    """Test save_detected_version option."""
    args = util.Args(json_args)
    args.mode = "check"
    config = get_config()
    main(args=args, config=config, texconv=util.get_texconv())
    args = util.Args(json_args)
    args.mode = "valid"
    config = get_config()
    main(args=args, config=config, texconv=util.get_texconv())


@pytest.mark.parametrize("json_args", util.get_test_cases("dds"))
def test_dds_io(json_args):
    """Test dds io."""
    base(json_args)


@pytest.mark.parametrize("json_args", util.get_test_cases("batch"))
def test_batch_method(json_args):
    """Test with _file_path_.txt"""
    base(json_args)


@pytest.mark.parametrize("json_args", util.get_test_cases("empty"))
def test_empty(json_args):
    """Test with empty textures."""
    json_args["mode"] = "valid"
    base(json_args)
    json_args["mode"] = "export"
    base(json_args)
