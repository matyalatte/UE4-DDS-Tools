[![discord](https://badgen.net/badge/icon/discord?icon=discord&label)](https://discord.gg/Qx2Ff3MByF)
![build](https://github.com/matyalatte/UE4-DDS-tools/actions/workflows/main.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# UE4-DDS-Tools
Texture modding tools for UE4 games<br>
All you need is drop files or folders on batch files.<br>

## Features

- Inject any size DDS and any number of mipmaps.
- Export assets as DDS.

## Supported Games

- FF7R
- UE4.18 games
- UE4.19 games

If you want me to add support for your game, please contact me with discord.

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

## Setup
You need to specify the UE4 version of your game.<br>
Open `./src/config.json` with notepad and edit the version.<br>
`ff7r`, `4.18`, and `4.19` are available.<br>
![config.json](https://user-images.githubusercontent.com/69258547/160256947-391f72e1-b7c1-49d2-bdd7-8834c1d6418d.png)

## Basic Usage
1. Drop `.uexp` onto `1_copy_uasset*.bat`.<br>
   The asset will be copied in `./workspace/uasset`.<br>

2. Drop `.dds` onto `2_inject_dds*.bat`.<br>
   A new asset will be generated in `./injected`.<br>

## Advanced Usage
You can inject multiple assets at the same time.<br>
See here for the details.<br>
[Advanced Usage · matyalatte/UE4-DDS-tools Wiki](https://github.com/matyalatte/UE4-DDS-tools/wiki/Advanced-Usage)

## Batch files
- `1_copy_uasset*.bat`<br>
    Make or clear `./workspace`.<br>
    Then, copy an asset to workspace.

- `2_inject_dds*.bat`<br>
    Inject dds into the asset copied to workspace.<br>
    A new asset will be generated in `./injected`.

- `_export_as_dds*.bat`<br>
    Export texture assets as dds.<br>

- `_parse*.bat`<br>
    Parse files.<br>
    You can check the format with this batch file.

## FAQ

### I got the `UE4 requires BC6H(unsigned)...` warning. What should I do?
There are two types of BC6H: `signed` and `unsigned`.<br>
And you should use the `unsigned` format.<br>
See here for the details.<br>
[How to Inject .HDR textures · matyalatte/UE4-DDS-tools Wiki](https://github.com/matyalatte/UE4-DDS-tools/wiki/How-to-Inject-.HDR-textures)

### I got the `Mipmaps should have power of 2 as...` warning. What should I do?
Change its width and height to power of 2.<br>
Or export dds without mipmaps.
