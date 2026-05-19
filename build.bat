@echo off
REM Build script for Grammar AI on Windows
REM Requires: Python 3.12+, PyInstaller installed (uv sync --extra dev)
REM Output: build\grammar-ai\  (standalone dir, bundled by installer.iss)

if "%1"=="debug" goto debug_build

echo Building Grammar AI executable...
python build.py
goto check_result

:debug_build
echo Building Grammar AI executable (debug mode with console)...
python build.py --debug

:check_result
if %errorlevel% equ 0 (
    echo.
    echo Build successful! Standalone distribution is in build\grammar-ai\
    if "%1"=="debug" echo Debug executable will show console window for error messages.
) else (
    echo Build failed with error code %errorlevel%
    exit /b %errorlevel%
)
