@echo off
REM Save asset path for injection

@if "%~1"=="" goto skip

echo Set "%~1" as an asset path.

@pushd %~dp0
echo %~1> src\_file_path_.txt
@popd

pause

:skip