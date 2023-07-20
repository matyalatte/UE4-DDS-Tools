@echo off
REM Parse asset files.

@if "%~1"=="" goto skip

@pushd %~dp0
python\python.exe -E src\main.py "%~1" --mode=parse
@popd

pause

:skip
