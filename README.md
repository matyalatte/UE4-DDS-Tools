[![discord](https://badgen.net/badge/icon/discord?icon=discord&label)](https://discord.gg/Qx2Ff3MByF)
![build](https://github.com/matyalatte/UE4-DDS-tools/actions/workflows/main.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# UE4-DDS-Tools ver0.3.2
Texture modding tools for UE4 games.<br>
You can inject texture files (.dds, .tga, .hdr, etc.) into UE4 assets.<br>

## Features

- Inject any size textures into assets
- Extract textures from assets
- Check the UE versions of assets
- Convert textures with [texconv](https://github.com/microsoft/DirectXTex/wiki/Texconv)

## Supported UE versions
- UE4.13 ~ 4.27
- FF7R
- Borderlands3

If you want me to add support for your game, please contact me with [discord](https://discord.gg/Qx2Ff3MByF).

## Supported Formats

- DXT1/BC1
- DXT5/BC3
- BC4/ATI1
- BC5/ATI2
- BC6H
- BC7
- B8G8R8A8 (Uncompressed color map)
- FloatRGBA (Uncompressed HDR)

## Download
Download `UE4-DDS-tools*.zip` from [here](https://github.com/matyalatte/UE4-DDS-tools/releases)

## How to Use
[How to Use · matyalatte/UE4-DDS-tools Wiki](https://github.com/matyalatte/UE4-DDS-Tools/wiki/How-to-Use)

## License
* The files in this repository are licensed under [MIT license](https://github.com/matyalatte/UE4-DDS-Tools/blob/main/LICENSE).
* UE4 DDS Tools uses [Simple Command Runner](https://github.com/matyalatte/Simple-Command-Runner) for GUI. It is licensed under [wxWindows Library Licence](https://github.com/wxWidgets/wxWidgets/blob/master/docs/licence.txt).
* UE4 DDS Tools uses [Windows embeddable package](https://www.python.org/downloads/windows/) for python. It is licensed under [PSF license](https://docs.python.org/3/license.html).
* UE4 DDS Tools uses [texconv](https://github.com/microsoft/DirectXTex/wiki/Texconv) as a texture converter. It is licensed under [MIT license](https://github.com/matyalatte/UE4-DDS-Tools/blob/main/LICENSE).

## FAQ

### I got `VCRUNTIME140_1.dll was not found.`
Install the dll with this.
[https://aka.ms/vs/17/release/vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### I got `UE4 requires BC6H(unsigned)...`
There are two types of BC6H: `signed` and `unsigned`.<br>
And you should use the `unsigned` format.<br>
See here for the details.<br>
[How to Inject .HDR textures · matyalatte/UE4-DDS-tools Wiki](https://github.com/matyalatte/UE4-DDS-tools/wiki/How-to-Inject-.HDR-textures)

### I got `Mipmaps should have power of 2 as...`
Change its width and height to power of 2.<br>
Or export dds without mipmaps.
