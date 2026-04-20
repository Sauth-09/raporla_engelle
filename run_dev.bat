@echo off
TITLE NetKalkan Dev Runner
SETLOCAL EnableDelayedExpansion

echo ====================================================
echo   NetKalkan - Debug Mode Starter
echo ====================================================

:: 0. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python bulunamadi! Lutfen Python'un yuklu ve PATH'e ekli oldugundan emin olun.
        pause
        exit /b
    ) else (
        set "PYTHON_EXE=py"
    )
) else (
    set "PYTHON_EXE=python"
)
echo Found Python: %PYTHON_EXE%

:: 1. Update extension to use localhost
echo [1/4] Configuring extension for local testing...
set "API_FILE=extension\lib\api-client.js"
if not exist "%API_FILE%" (
    echo [ERROR] %API_FILE% bulunamadi!
    pause
    exit /b
)
powershell -Command "(gc '%API_FILE%') -replace 'http://192.168.1.100:5000/api', 'http://localhost:5000/api' | Out-File -encoding utf8 '%API_FILE%'"
echo      Done.

:: 2. Setup Server
echo [2/4] Setting up Flask server...
if not exist "server" (
    echo [ERROR] 'server' klasoru bulunamadi!
    pause
    exit /b
)

if not exist server\venv (
    echo      Creating virtual environment...
    %PYTHON_EXE% -m venv server\venv
)

echo [3/4] Installing/Updating dependencies...
call server\venv\Scripts\activate
pip install -r server\requirements.txt

:: 3. Start Server from ROOT as a module
echo [4/4] Starting server as a module...
:: We set PYTHONPATH to current directory to ensure 'server' package is found
set "PYTHONPATH=%CD%"
start "NetKalkan Backend" cmd /k "title NetKalkan Server && set PYTHONPATH=%CD% && call server\venv\Scripts\activate && python -m server.app"

:: 4. Open browser
echo ====================================================
echo   SUCCESS: Server is starting!
echo   Opening Admin Panel: http://localhost:5000
echo ====================================================
timeout /t 5 >nul
start http://localhost:5000

echo.
echo Server window is open. Check it for any startup errors.
echo.
pause
