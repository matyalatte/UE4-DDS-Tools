[![discord](https://badgen.net/badge/icon/discord?icon=discord&label)](https://discord.gg/Qx2Ff3MByF)
![build](https://github.com/matyalatte/UE4-DDS-tools/actions/workflows/main.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# UE4-DDS-Tools ver0.4.0

Texture modding tools for UE games.  
You can inject texture files (.dds, .tga, .hdr, etc.) into UE assets.  

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

## Supported DXGI Formats

- DXT1/BC1
- DXT5/BC3
- BC4/ATI1
- BC5/ATI2
- BC6H
- BC7
- B8G8R8A8 (Uncompressed color map)
- FloatRGBA (Uncompressed HDR)
- ASTC_4x4

> Note that Unreal Engine supports more DXGI formats.  
> You will get the `Unsupported pixel format.` error for them.  

## Supported File Formats

This tool can convert textures between the following file formats.  

- .uasset (for texture assets)
- .dds
- .tga
- .hdr
- .bmp
- .jpg
- .png

> Note that this tool can not convert non-official DXGI formats (e.g. ASTC_4x4) from and to non-dds files.  
> It means you can not use .bmp, .png, and .jpg if the assets have non-official DXGI formats.  

## Download

Download `UE4-DDS-tools*.zip` from [here](https://github.com/matyalatte/UE4-DDS-tools/releases)

## How to Use

[How to Use · matyalatte/UE4-DDS-tools Wiki](https://github.com/matyalatte/UE4-DDS-Tools/wiki/How-to-Use)

## FAQ

[FAQ · matyalatte/UE4-DDS-Tools Wiki](https://github.com/matyalatte/UE4-DDS-Tools/wiki/FAQ)

## External Projects

### Texconv-Custom-DLL

[Texconv](https://github.com/microsoft/DirectXTex/wiki/Texconv)
is a texture converter developed by Microsoft.  
It's the best DDS converter as far as I know.  
And [Texconv-Custom-DLL](https://github.com/matyalatte/Texconv-Custom-DLL) is a cross-platform implementation I made.  
The official Texconv only supports Windows but you can use it on Unix systems.  

### Simple-Command-Runner

[Simple Command Runner](https://github.com/matyalatte/Simple-Command-Runner) is a GUI wrapper for executing commands.  
It can define a simple GUI with a json file.  

## License

* The files in this repository are licensed under [MIT license](https://github.com/matyalatte/UE4-DDS-Tools/blob/main/LICENSE).
* Released packeges use [Simple Command Runner](https://github.com/matyalatte/Simple-Command-Runner) for GUI. It is licensed under [wxWindows Library Licence](https://github.com/wxWidgets/wxWidgets/blob/master/docs/licence.txt).
* Released packeges use [Windows embeddable package](https://www.python.org/downloads/windows/) for python. It is licensed under [PSF license](https://docs.python.org/3/license.html).
