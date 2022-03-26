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
