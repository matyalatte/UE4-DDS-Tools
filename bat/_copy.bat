@echo off
REM Copy texture assets to ./copied (ignore non-texture assets)

@if "%~1"=="" goto skip

@pushd %~dp0
python\python.exe -E src\main.py "%~1" --mode=copy --save_folder=copied
@popd

pause

:skip
