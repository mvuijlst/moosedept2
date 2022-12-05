..\hugo.exe
git add *
git commit -m "build"
git push
xcopy public \\files\mvuijlst\www\users /s /y
cd public 
firebase deploy