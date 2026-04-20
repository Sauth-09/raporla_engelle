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

:: 2. Auto-fix/Set Remote from Readme.md
echo [INFO] Syncing remote 'origin' from Readme.md...
for /f "tokens=3" %%a in ('findstr /C:"github repo:" Readme.md') do (
    set "FOUND_URL=%%a"
    echo [INFO] Target Repo: !FOUND_URL!
    git remote remove origin >nul 2>&1
    git remote add origin !FOUND_URL!
    goto :remote_done
)

:: If not found in Readme, check if origin already exists
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Could not auto-detect repo URL from 'github repo:' line.
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
:: Get current branch name
for /f "tokens=*" %%i in ('git branch --show-current') do set "CUR_BRANCH=%%i"
if "!CUR_BRANCH!"=="" set "CUR_BRANCH=master"

git push origin !CUR_BRANCH!

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
