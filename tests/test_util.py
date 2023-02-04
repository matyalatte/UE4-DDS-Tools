"""Tests for crc.py and version.py"""
import pytest
from unreal.crc import generate_hash, strcrc_deprecated
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
    ]
}


@pytest.mark.parametrize("name, true_hash", test_cases["name_hash"])
def test_name_hash(name, true_hash):
    name_hash = generate_hash(name)
    assert name_hash == true_hash


@pytest.mark.parametrize("package, true_hash", test_cases["package_hash"])
def test_package_hash(package, true_hash):
    package_hash = strcrc_deprecated(package)
    assert package_hash == true_hash


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
