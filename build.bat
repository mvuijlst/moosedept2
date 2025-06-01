@echo off
REM Build script for Moose Department website
REM Usage: build.bat [/copy]
REM   /copy - Optional parameter to copy files to network share

..\hugo.exe --baseURL "https://moosedept.org" 
cd public 
call firebase deploy
cd ..
..\hugo.exe --baseURL "http://users.ugent.be/~mvuijlst/" 

REM Check if /copy parameter was provided
IF "%1"=="/copy" (
    echo Copying files to network share...
    powershell -ExecutionPolicy Bypass -File smart-copy.ps1
) ELSE (
    echo Skipping network copy. Use /copy parameter to copy files to network share.
)

git add *
git commit -m "build"
git push
