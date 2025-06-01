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
git push
