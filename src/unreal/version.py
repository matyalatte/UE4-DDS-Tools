"""Class for version info.

Notes:
    Variables:
        base: Base version like 1.2, 2.3.0.
        base_int: Base version as int. 1 will be 10000. 4.27 will be 42700. 5.0.2 will be 50002.
        custom: custom string for customized version.
    Operators:
        ==, !=, in: Comparison operators for base and custom.
        <, <=, >, >=: Comparison operators for base_int.
"""


class VersionInfo:
    """Class for version info."""

    base: str
    custom: str
    base_int: int

    def __init__(self, version: str, base_int: int = None):
        """Constractor."""
        if version == 'ff7r':
            base = '4.18'
            custom = version
        elif version == 'borderlands3':
            base = '4.22'
            custom = version
        else:
            base = version
            custom = None

        self.base = base
        self.custom = custom
        if base_int is None:
            self.base_int = version_as_int(self.base)
        else:
            self.base_int = base_int

    def copy(self) -> "VersionInfo":
        if self.custom is None:
            return VersionInfo(self.base, base_int=self.base_int)
        else:
            return VersionInfo(self.custom, base_int=self.base_int)

    def __eq__(self, v: str):  # self == string
        return v in [self.base, self.custom]

    def __contains__(self, versions: list[str]):  # self in list
        return (self.base not in versions) and (self.custom not in versions)

    def __ne__(self, v: str):  # self != string
        return self.base != v and self.custom != v

    def __lt__(self, v: str):  # self < string
        return self.base_int < version_as_int(v)

    def __le__(self, v: str):  # self <= string
        return self.base_int <= version_as_int(v)

    def __gt__(self, v: str):  # self > string
        return self.base_int > version_as_int(v)

    def __ge__(self, v: str):  # self >= string
        return self.base_int >= version_as_int(v)

    def __str__(self):  # str(self)
        if self.custom is not None:
            return self.custom
        return self.base


def version_as_int(ver: str):  # ver (string): like "x.x.x"
    """Convert a string to int."""
    ver_str = [int(s) for s in ver.split('.')]
    if len(ver_str) > 3:
        raise RuntimeError(f'Unsupported version info.({ver})')
    return sum(s * (10 ** ((2 - i) * 2)) for s, i in zip(ver_str, range(len(ver_str))))
