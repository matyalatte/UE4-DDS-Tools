@echo off
REM Check UE version of assets. And save the version for other batch files.

@if "%~1"=="" goto skip

@pushd %~dp0
python\python.exe -E src\main.py "%~1" --mode=check --save_detected_version
@popd

pause

:skip