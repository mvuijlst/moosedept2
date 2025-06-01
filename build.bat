@echo off
REM Build script for Moose Department website
REM Usage: build.bat [/force]
REM   /force - Force copy all files (not just changed ones)

REM get the latest news
python getnews.py

REM Build the website
..\hugo.exe --baseURL "https://moosedept.org" 
cd public 
call firebase deploy
cd ..
..\hugo.exe --baseURL "http://users.ugent.be/~mvuijlst/" 

REM Always copy files to network share
echo Copying files to network share...
IF "%1"=="/force" (
    echo Force copying all files...
    powershell -ExecutionPolicy Bypass -File smart-copy.ps1 -Force
) ELSE (
    echo Copying only changed files...
    powershell -ExecutionPolicy Bypass -File smart-copy.ps1
)

git add *
git commit -m "build"

REM --- Push to GitHub Enterprise (UGent) ---
echo Pushing to origin (GitHub UGent)...
git push origin

REM --- Push to public GitHub ---
REM Check if the 'github_public' remote exists and add it if not
git remote get-url github_public >nul 2>&1
IF ERRORLEVEL 1 (
    echo Adding new remote 'github_public' for public GitHub...
    git remote add github_public https://github.com/mvuijlst/moosedept2.git
) ELSE (
    echo Remote 'github_public' already exists.
    REM Optionally, ensure the URL is correct if it might change
    git remote set-url github_public https://github.com/mvuijlst/moosedept2.git
)

echo Pushing to github_public (Public GitHub)...
git push github_public
