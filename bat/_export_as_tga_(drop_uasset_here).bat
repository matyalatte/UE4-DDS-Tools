@echo off

@if "%~1"=="" goto skip

@pushd %~dp0
python\python.exe src\main.py "%~1" --save_folder=exported --mode=export --export_as=tga
echo %~1> src\_file_path_.txt
@popd

pause

:skip