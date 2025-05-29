..\hugo.exe --baseURL "https://moosedept.org" 
cd public 
call firebase deploy
cd ..
..\hugo.exe --baseURL "http://users.ugent.be/~mvuijlst/" 
git add *
git commit -m "build"
git push
REM xcopy public \\files\mvuijlst\www\users /s /y
powershell -ExecutionPolicy Bypass -File smart-copy.ps1
