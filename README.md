[![discord](https://badgen.net/badge/icon/discord?icon=discord&label)](https://discord.gg/Qx2Ff3MByF)
![build](https://github.com/matyalatte/UE4-DDS-tools/actions/workflows/main.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# UE4-DDS-Tools ver0.3.3
Texture modding tools for UE games.<br>
You can inject texture files (.dds, .tga, .hdr, etc.) into UE assets.<br>

## Features

- Inject any size textures into assets
- Extract textures from assets
- Check the UE versions of assets
- Convert textures with [texconv](https://github.com/microsoft/DirectXTex/wiki/Texconv)

## Supported UE versions
- UE5.0
- UE4.13 ~ 4.27
- FF7R
- Borderlands3

## Supported Formats

- DXT1/BC1
- DXT5/BC3
- BC4/ATI1
- BC5/ATI2
- BC6H
- BC7
- B8G8R8A8 (Uncompressed color map)
- FloatRGBA (Uncompressed HDR)
- ASTC_4x4

You will get the `Unsupported pixel format.` error for other pixel formats.  

## Download
Download `UE4-DDS-tools*.zip` from [here](https://github.com/matyalatte/UE4-DDS-tools/releases)

## How to Use
[How to Use · matyalatte/UE4-DDS-tools Wiki](https://github.com/matyalatte/UE4-DDS-Tools/wiki/How-to-Use)

## FAQ
[FAQ · matyalatte/UE4-DDS-Tools Wiki](https://github.com/matyalatte/UE4-DDS-Tools/wiki/FAQ)

## License
* The files in this repository are licensed under [MIT license](https://github.com/matyalatte/UE4-DDS-Tools/blob/main/LICENSE).
* UE4 DDS Tools uses [Simple Command Runner](https://github.com/matyalatte/Simple-Command-Runner) for GUI. It is licensed under [wxWindows Library Licence](https://github.com/wxWidgets/wxWidgets/blob/master/docs/licence.txt).
* UE4 DDS Tools uses [Windows embeddable package](https://www.python.org/downloads/windows/) for python. It is licensed under [PSF license](https://docs.python.org/3/license.html).
* UE4 DDS Tools uses [texconv](https://github.com/microsoft/DirectXTex/wiki/Texconv) as a texture converter. It is licensed under [MIT license](https://github.com/matyalatte/UE4-DDS-Tools/blob/main/LICENSE).

