@echo off
REM Export texture assets as tga or hdr. And save the asset path for injection

@if "%~1"=="" goto skip

@pushd %~dp0
python\python.exe -E src\main.py "%~1" --save_folder=exported --mode=export --export_as=tga --skip_non_texture
echo %~1> src\_file_path_.txt
@popd

pause

:skip