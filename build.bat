..\hugo.exe --baseURL "https://moosedept.org" 
cd public 
call firebase deploy
cd ..
..\hugo.exe --baseURL "http://users.ugent.be/~mvuijlst/" 
powershell -ExecutionPolicy Bypass -File smart-copy.ps1
git add *
git commit -m "build"
git push
