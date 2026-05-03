@echo off
REM Build script for Grammar AI on Windows
REM Requires: Python 3.12+, nuitka installed

echo Building Grammar AI executable...
python build.py

if %errorlevel% equ 0 (
    echo.
    echo Build successful! Executable is in the dist\ folder.
) else (
    echo Build failed with error code %errorlevel%
    exit /b %errorlevel%
)
