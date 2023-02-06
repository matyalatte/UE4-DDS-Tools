@echo off

@if "%~1"=="" goto skip

@pushd %~dp0
python\python.exe src\main.py src\_file_path_.txt "%~1" --save_folder=injected
@popd

pause

:skip