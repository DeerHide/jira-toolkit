@echo off
cd ..

REM Check for uncommitted changes
git status --porcelain >nul 2>&1
if %errorlevel% neq 0 (
    echo Warning: You have uncommitted changes. Please commit or stash them first.
    pause
    exit /b 1
)

REM Set core.autocrlf to false
git config core.autocrlf false

REM Set core.eol to lf
git config core.eol lf

REM Normalize all files in the repository
git add --renormalize .

echo Git line ending configuration updated. Files have been renormalized.
echo Review the changes with 'git status' and commit when ready.
pause
