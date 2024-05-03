"""Tests for crc.py and version.py"""
import pytest
from unreal.crc import strcrc, strcrc_deprecated
from unreal.city_hash import city_hash_64, fetch64
from unreal.version import VersionInfo

test_cases = {
    "name_hash": [
        ("Texture2D", b"\xFE\xFD\x40\xD1"),
        ("color", b"\xAC\x91\x6E\x37"),
        ("強制FootIK無効", b"\x21\xE8\x34\xD4")
    ],
    "package_hash": [
        ("color", 459187122),
        ("Normal", 1556301383),
        ("テスト", 1329585195)
    ],
    "zen_name_hash": [
        ("None", fetch64(b"\xC2\x2D\x35\xA6\x5B\x0F\x37\x75")),
        ("mrv", fetch64(b"\xC6\x78\x92\x85\x10\x70\x35\x6A")),
        ("/Game/mrv", fetch64(b"\xF6\x64\xE1\x2E\x0B\x45\x36\x16")),
        ("T_GP29Lightning_PositionArray", fetch64(b"\xC0\xF8\x1F\xB5\xA1\x2E\x18\xAC")),
        ("/Game/Effects/Fort_Effects/GameplayPulginsAssets"
         "/ToonLightning/GP29/Texture/T_GP29Lightning_PositionArray",
         fetch64(b"\x58\xCB\xA0\x64\x2F\x3E\x34\x88")),
    ],
    "zen_import_hash": [
        ("/Script/Engine/Texture2D", 0x1b93bca796d1fa6f),
        ("/Script/Engine/Default__VolumeTexture", 0x015b0407da6ae563),
    ],
}


@pytest.mark.parametrize("name, true_hash", test_cases["name_hash"])
def test_name_hash(name, true_hash):
    name_hash = strcrc(name)
    assert name_hash == true_hash


@pytest.mark.parametrize("package, true_hash", test_cases["package_hash"])
def test_package_hash(package, true_hash):
    package_hash = strcrc_deprecated(package)
    assert package_hash == true_hash


@pytest.mark.parametrize("name, true_hash", test_cases["zen_name_hash"])
def test_zen_name_hash(name, true_hash):
    string = name.lower()
    if string.isascii():
        binary = string.encode("ascii")
    else:
        binary = string.encode("utf-16-le")
    name_hash = city_hash_64(binary)
    assert name_hash == true_hash


@pytest.mark.parametrize("path, true_hash", test_cases["zen_import_hash"])
def test_zen_import_hash(path, true_hash):
    object_path = path.lower()
    binary = object_path.encode("utf-16-le")
    import_hash = city_hash_64(binary) & ~(3 << 62)
    assert import_hash == true_hash


def test_versioninfo_op():
    """Test operators of VersionInfo."""
    ver = VersionInfo('4.20')
    assert ver == '4.20'
    assert ver in ['4.20', '5']
    assert ver != '4.20.2'
    assert ver not in ['4.20.2', '5']
    assert ver <= '4.20'
    assert ver <= '5.0.2'
    assert ver > '4'
    assert ver < '4.20.1'
    assert ver >= '4.20'
    assert ver >= '3'
    assert str(ver) == '4.20'
    assert ver.copy() == '4.20'


@pytest.mark.parametrize("base, custom", [("4.18", "ff7r"), ("4.22", "borderlands3")])
def test_versioninfo_custom(base, custom):
    ver = VersionInfo(custom)
    assert ver == base
    assert ver == custom
    assert str(ver) == custom
    assert ver in [custom, '5']
    assert ver in [base, '5']


def test_versioninfo_const_error():
    """Test VersionInfo.__init__."""
    with pytest.raises(Exception) as e:
        VersionInfo('5.0.2.1')
    assert str(e.value) == 'Unsupported version info.(5.0.2.1)'
