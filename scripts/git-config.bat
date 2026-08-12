@echo off
cd /d "%~dp0.."

REM Check for uncommitted changes
for /f %%i in ('git status --porcelain') do (
    echo Warning: You have uncommitted changes. Please commit or stash them first.
    pause
    exit /b 1
)

git config core.autocrlf false
git config core.eol lf
git add --renormalize .

echo Git line ending configuration updated. Files have been renormalized.
echo Review the changes with 'git status' and commit when ready.
pause
