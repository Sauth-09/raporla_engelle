@echo off
TITLE NetKalkan Portable Builder
SETLOCAL EnableDelayedExpansion

echo ====================================================
echo   NetKalkan - Portable (Folder) Build Script
echo ====================================================

:: 1. Setup Environment
echo [1/4] Preparing environment...
if not exist server\venv (
    echo      Creating virtual environment...
    python -m venv server\venv
)
call server\venv\Scripts\activate
echo      Installing/Updating dependencies...
pip install -q -r server\requirements.txt

:: 2. Clean previous builds
if exist dist\NetKalkanServer (
    echo      Cleaning old build...
    rd /s /q dist\NetKalkanServer
)

:: 3. Build with PyInstaller
echo [2/4] Building portable directory (this may take a few minutes)...
:: --onedir: Create a folder containing the EXE and DLLs (fastest startup)
:: --add-data: Include Flask templates and static files
:: --name: Name of the output folder/EXE
set "PYTHONPATH=%CD%"
python -m PyInstaller --onedir --noconsole ^
    --name NetKalkanServer ^
    --icon="logo (3).ico" ^
    --add-data "logo (3).ico;." ^
    --add-data "server/templates;server/templates" ^
    --add-data "server/static;server/static" ^
    --collect-all server ^
    --hidden-import server.config ^
    --hidden-import server.models ^
    --hidden-import server.services ^
    --hidden-import server.routes ^
    server/tray_app.py

:: 4. Finalize
if %errorlevel% equ 0 (
    echo ====================================================
    echo   SUCCESS: Portable folder created!
    echo   Location: dist\NetKalkanServer
    echo   Run: dist\NetKalkanServer\NetKalkanServer.exe
    echo ====================================================
    
    :: Copy Readme to dist folder
    copy README.md dist\NetKalkanServer\README_SYSTEM.md >nul
    
    start explorer dist\NetKalkanServer
) else (
    echo ====================================================
    echo   ERROR: Build failed. Check the logs above.
    echo ====================================================
)

pause
