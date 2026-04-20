@echo off
TITLE NetKalkan GitHub Push
SETLOCAL EnableDelayedExpansion

echo ====================================================
echo   NetKalkan - GitHub Push Script (Safe Mode)
echo ====================================================

:: 1. Initialize Git if not already
if not exist .git (
    echo [1/3] Initializing Git repository...
    git init
)

:: 2. Check for Remote
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Remote 'origin' not found. Checking Readme.md...
    
    :: Attempt to find github URL in Readme.md
    for /f "tokens=2 delims=: " %%a in ('findstr "https://github.com/" Readme.md') do (
        set "FOUND_URL=%%a"
        :: Remove trailing .git if it was part of a larger string
        echo [INFO] Found potential URL: !FOUND_URL!
        git remote add origin !FOUND_URL!
        goto :remote_done
    )

    echo [WARNING] Could not auto-detect repo URL.
    set /p REPO_URL="Enter GitHub Repo URL (or press Enter to skip): "
    if not "!REPO_URL!"=="" (
        git remote add origin !REPO_URL!
    )
)
:remote_done

:: 3. Commit and Push
echo [2/3] Adding files and committing...
:: .gitignore will handle excluding sensitive data like .db and venv
git add .
set /p COMMIT_MSG="Enter commit message (default: Update NetKalkan): "
if "!COMMIT_MSG!"=="" set "COMMIT_MSG=Update NetKalkan"

git commit -m "!COMMIT_MSG!"

echo [3/3] Pushing to GitHub...
:: Try to push to main or master
git push origin main || git push origin master

if %errorlevel% equ 0 (
    echo ====================================================
    echo   SUCCESS: Changes pushed to GitHub!
    echo ====================================================
) else (
    echo ====================================================
    echo   ERROR: Push failed. Check your internet or repo permissions.
    echo ====================================================
)

pause
