[![discord](https://badgen.net/badge/icon/discord?icon=discord&label)](https://discord.gg/Qx2Ff3MByF)
![build](https://github.com/matyalatte/UE4-DDS-tools/actions/workflows/main.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# UE4-DDS-Tools ver0.2.5
Texture modding tools for UE4 games.<br>
You can inject dds files into UE4 assets.<br>

## Features

- Inject any size DDS and any number of mipmaps.
- Export assets as DDS.

## Supported Games

- UE4.25 ~ 4.27 games
- UE4.19 games
- UE4.18 games
- FF7R
- Bloodstained (UE4.27)

If you want me to add support for your game, please contact me with [discord](https://discord.gg/Qx2Ff3MByF).

## Supported Formats

- DXT1/BC1
- DXT5/BC3
- BC4/ATI1
- BC5/ATI2
- BC6H
- BC7
- B8G8R8A8(sRGB)
- FloatRGBA

## Download
Download `UE4-DDS-tools*.zip` from [here](https://github.com/matyalatte/UE4-DDS-tools/releases)

## How to Use
[How to Use · matyalatte/UE4-DDS-tools Wiki](https://github.com/matyalatte/UE4-DDS-Tools/wiki/How-to-Use)

## License
* The files in this repository are licensed under [MIT license](https://github.com/matyalatte/UE4-DDS-Tools/blob/main/LICENSE).
* We use [Simple Command Runner](https://github.com/matyalatte/Simple-Command-Runner) for GUI. It is licensed under [wxWindows Library Licence](https://github.com/wxWidgets/wxWidgets/blob/master/docs/licence.txt).
* We use [Windows embeddable package](https://www.python.org/downloads/windows/) for python. It is licensed under [PSF license](https://docs.python.org/3/license.html).

## FAQ

### I got the `UE4 requires BC6H(unsigned)...` warning. What should I do?
There are two types of BC6H: `signed` and `unsigned`.<br>
And you should use the `unsigned` format.<br>
See here for the details.<br>
[How to Inject .HDR textures · matyalatte/UE4-DDS-tools Wiki](https://github.com/matyalatte/UE4-DDS-tools/wiki/How-to-Inject-.HDR-textures)

### I got the `Mipmaps should have power of 2 as...` warning. What should I do?
Change its width and height to power of 2.<br>
Or export dds without mipmaps.
