@echo off
REM Inject texture files to assets.
REM You can specify the asset path with _export_as_tga.bat or _set_asset_path.bat

@if "%~1"=="" goto skip

@pushd %~dp0
python\python.exe -E src\main.py src\_file_path_.txt "%~1" --save_folder=injected --skip_non_texture --image_filter=cubic
@popd

pause

:skip
