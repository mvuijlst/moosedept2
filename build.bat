..\hugo.exe --baseURL "https://moosedept.org" 
cd public 
call firebase deploy
cd ..
..\hugo.exe --baseURL "http://users.ugent.be/~mvuijlst/" 
git add *
git commit -m "build"
git push
xcopy public \\files\mvuijlst\www\users /s /y
REM robocopy public \\files\mvuijlst\www\users /MIR /Z /W:5 /COPY:DT /XC
