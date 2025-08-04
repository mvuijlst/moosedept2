@echo off
REM Enhanced Build script for Moose Department website
REM Usage: build.bat [options]
REM Options:
REM   /force      - Force copy all files (not just changed ones)
REM   /vpsonly    - Deploy only to VPS
REM   /ugentonly  - Deploy only to UGent
REM   /skipnews   - Skip news fetching
REM   /verbose    - Show detailed output

setlocal enabledelayedexpansion

REM Parse command line arguments
set FORCE_FLAG=
set DEPLOY_FLAGS=
set SKIP_NEWS=false
set VERBOSE_FLAG=

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="/force" (
    set FORCE_FLAG=-Force
    set DEPLOY_FLAGS=!DEPLOY_FLAGS! -Force
)
if /i "%~1"=="/vpsonly" set DEPLOY_FLAGS=!DEPLOY_FLAGS! -VPSOnly
if /i "%~1"=="/ugentonly" set DEPLOY_FLAGS=!DEPLOY_FLAGS! -UGentOnly
if /i "%~1"=="/skipnews" set SKIP_NEWS=true
if /i "%~1"=="/verbose" set DEPLOY_FLAGS=!DEPLOY_FLAGS! -Verbose
shift
goto parse_args
:args_done

echo.
echo =====================================================
echo    Enhanced Moose Department Build Script
echo =====================================================
echo.

REM Get the latest news (unless skipped)
if "%SKIP_NEWS%"=="false" (
    echo [INFO] Fetching latest news...
    python getnews.py
    if errorlevel 1 (
        echo [WARNING] News fetching failed, continuing anyway...
    ) else (
        echo [SUCCESS] News fetched successfully
    )
    echo.
) else (
    echo [INFO] Skipping news fetch as requested
    echo.
)

REM Build the website for moosedept.org
echo [INFO] Building website for moosedept.org...
..\hugo.exe --baseURL "https://moosedept.org" 
if errorlevel 1 (
    echo [ERROR] Hugo build failed!
    pause
    exit /b 1
)
echo [SUCCESS] Hugo build completed
echo.

REM Deploy using enhanced script
echo [INFO] Starting deployment with options: !DEPLOY_FLAGS!
powershell -ExecutionPolicy Bypass -File enhanced-deploy.ps1 !DEPLOY_FLAGS!
if errorlevel 1 (
    echo [ERROR] Deployment failed!
    pause
    exit /b 1
)
echo.

REM Build for UGent if we're deploying there
if not "!DEPLOY_FLAGS!" == "!DEPLOY_FLAGS:-VPSOnly=!" (
    echo [INFO] VPS-only deployment, skipping UGent build
) else (
    echo [INFO] Building website for UGent...
    ..\hugo.exe --baseURL "http://users.ugent.be/~mvuijlst/" 
    if errorlevel 1 (
        echo [ERROR] UGent Hugo build failed!
        pause
        exit /b 1
    )
    echo [SUCCESS] UGent Hugo build completed
    echo.
    
    REM Deploy to UGent using the enhanced script for UGent-specific deployment
    echo [INFO] Deploying to UGent share...
    powershell -ExecutionPolicy Bypass -File enhanced-deploy.ps1 -UGentOnly !FORCE_FLAG!
    if errorlevel 1 (
        echo [ERROR] UGent deployment failed!
        pause
        exit /b 1
    )
)

REM Git operations
echo [INFO] Committing changes to git...
git add *
git commit -m "build"
if errorlevel 1 (
    echo [WARNING] Git commit failed or no changes to commit
)

REM Push to GitHub Enterprise (UGent)
echo [INFO] Pushing to origin (GitHub UGent)...
git push origin
if errorlevel 1 (
    echo [ERROR] Push to UGent GitHub failed!
    REM Don't exit here, try public GitHub anyway
)

REM Push to public GitHub
echo [INFO] Checking public GitHub remote...
git remote get-url github_public >nul 2>&1
if errorlevel 1 (
    echo [INFO] Adding new remote 'github_public' for public GitHub...
    git remote add github_public https://github.com/mvuijlst/moosedept2.git
) else (
    echo [INFO] Remote 'github_public' already exists, updating URL...
    git remote set-url github_public https://github.com/mvuijlst/moosedept2.git
)

echo [INFO] Pushing to github_public (Public GitHub)...
git push github_public
if errorlevel 1 (
    echo [ERROR] Push to public GitHub failed!
    pause
    exit /b 1
)

echo.
echo =====================================================
echo    Build and deployment completed successfully! 🎉
echo =====================================================
echo.
echo Usage examples for next time:
echo   build.bat                    - Normal full build and deploy
echo   build.bat /force             - Force deploy all files
echo   build.bat /vpsonly           - Deploy only to VPS
echo   build.bat /ugentonly /force  - Force deploy only to UGent
echo   build.bat /skipnews          - Skip news fetching
echo.

pause
