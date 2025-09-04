param(
    [switch]$Force = $false,
    [switch]$VPSOnly = $false,
    [switch]$UGentOnly = $false,
    [switch]$Quiet = $false
)

# Configuration
$sourceDir = "public"
$ugentDestDir = "\\files\mvuijlst\www\users"
$vpsHost = "yusupov"
$vpsPath = "/home/django/moosedept"
$hashFile = "file-hashes.json"

# Set verbose as default
$Verbose = -not $Quiet

# Color scheme
$colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
    Header = "Magenta"
    Detail = "Gray"
}

# Enhanced logging function
function Write-Log {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    $prefix = switch ($Type) {
        "Success" { "[OK]" }
        "Warning" { "[WARN]" }
        "Error" { "[ERR]" }
        "Info" { "[INFO]" }
        default { "[*]" }
    }
    
    $fullMessage = "[$timestamp] $prefix $Message"
    Write-Host $fullMessage -ForegroundColor $colors[$Type]
}

# Function to test network connectivity
function Test-NetworkConnectivity {
    param(
        [string]$Target,
        [string]$Description
    )
    
    Write-Log "Testing connectivity to $Description..." -Type "Info"
    
    try {
        if ($Target.StartsWith("\\")) {
            $result = Test-Path $Target -ErrorAction Stop
        } else {
            # Test SSH connectivity
            $result = (ssh -o ConnectTimeout=5 -o BatchMode=yes $Target "echo 'connected'" 2>$null) -eq "connected"
        }
        
        if ($result) {
            Write-Log "$Description is accessible" -Type "Success"
            return $true
        } else {
            Write-Log "$Description is not accessible" -Type "Warning"
            return $false
        }
    }
    catch {
        Write-Log "$Description test failed: $($_.Exception.Message)" -Type "Error"
        return $false
    }
}

# File hash calculation
function Get-CustomFileHash {
    param([string]$FilePath)
    
    try {
        $md5 = [System.Security.Cryptography.MD5]::Create()
        $stream = [System.IO.File]::OpenRead($FilePath)
        $hashBytes = $md5.ComputeHash($stream)
        $stream.Close()
        $md5.Dispose()
        return [System.BitConverter]::ToString($hashBytes).Replace("-", "")
    }
    catch {
        return "ERROR"
    }
}

# Git operations
function Invoke-GitCommitAndPush {
    param(
        [string]$CommitMessage = "Auto-deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm')",
        [switch]$SkipCommit = $false
    )
    
    Write-Log "Starting Git operations..." -Type "Header"
    
    try {
        # Check git status
        $status = git status --porcelain 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Git status check failed: $status" -Type "Error"
            return $false
        }
        
        # Check if there are changes to commit
        if (-not $SkipCommit -and $status) {
            Write-Log "Adding all changes to git..." -Type "Info"
            git add . 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Log "Git add failed" -Type "Error"
                return $false
            }
            
            Write-Log "Committing changes: $CommitMessage" -Type "Info"
            git commit -m $CommitMessage 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Log "Git commit failed" -Type "Error"
                return $false
            }
            Write-Log "Changes committed successfully" -Type "Success"
        } elseif (-not $SkipCommit) {
            Write-Log "No changes to commit" -Type "Info"
        }
        
        # Check if we're ahead of origin
        $ahead = git rev-list --count origin/master..master 2>&1
        if ($LASTEXITCODE -eq 0 -and [int]$ahead -gt 0) {
            Write-Log "Pushing $ahead commit(s) to GitHub..." -Type "Info"
            git push origin master 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Successfully pushed to GitHub" -Type "Success"
                return $true
            } else {
                Write-Log "Git push failed" -Type "Error"
                return $false
            }
        } else {
            Write-Log "No commits to push to GitHub" -Type "Info"
            return $true
        }
    }
    catch {
        Write-Log "Git operation failed: $($_.Exception.Message)" -Type "Error"
        return $false
    }
}

# Interactive menu function
function Show-InteractiveMenu {
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host "        Hugo Deployment Options            " -ForegroundColor Cyan
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host "  1. Deploy to both VPS and UGent + Git   " -ForegroundColor Green
    Write-Host "  2. Deploy to VPS only                   " -ForegroundColor White
    Write-Host "  3. Deploy to UGent only                 " -ForegroundColor White
    Write-Host "  4. Force deploy all files to both + Git " -ForegroundColor Yellow
    Write-Host "  5. Force deploy all files to VPS only   " -ForegroundColor Yellow
    Write-Host "  6. Force deploy all files to UGent only " -ForegroundColor Yellow
    Write-Host "  7. Test connectivity only               " -ForegroundColor Gray
    Write-Host "  8. Show deployment status               " -ForegroundColor Gray
    Write-Host "  9. Git commit and push only             " -ForegroundColor Magenta
    Write-Host "  q. Quit                                 " -ForegroundColor Red
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host ""
}

# Function to get user choice
function Get-UserChoice {
    do {
        Show-InteractiveMenu
        $choice = Read-Host "Please select an option (1-9 or q)"
        
        switch ($choice.ToLower()) {
            "1" { 
                Write-Log "Selected: Deploy to both VPS and UGent + Git" -Type "Info"
                return @{ VPSOnly = $false; UGentOnly = $false; Force = $false; TestOnly = $false; StatusOnly = $false; GitOnly = $false; IncludeGit = $true }
            }
            "2" { 
                Write-Log "Selected: Deploy to VPS only" -Type "Info"
                return @{ VPSOnly = $true; UGentOnly = $false; Force = $false; TestOnly = $false; StatusOnly = $false; GitOnly = $false; IncludeGit = $false }
            }
            "3" { 
                Write-Log "Selected: Deploy to UGent only" -Type "Info"
                return @{ VPSOnly = $false; UGentOnly = $true; Force = $false; TestOnly = $false; StatusOnly = $false; GitOnly = $false; IncludeGit = $false }
            }
            "4" { 
                Write-Log "Selected: Force deploy all files to both + Git" -Type "Warning"
                return @{ VPSOnly = $false; UGentOnly = $false; Force = $true; TestOnly = $false; StatusOnly = $false; GitOnly = $false; IncludeGit = $true }
            }
            "5" { 
                Write-Log "Selected: Force deploy all files to VPS only" -Type "Warning"
                return @{ VPSOnly = $true; UGentOnly = $false; Force = $true; TestOnly = $false; StatusOnly = $false; GitOnly = $false; IncludeGit = $false }
            }
            "6" { 
                Write-Log "Selected: Force deploy all files to UGent only" -Type "Warning"
                return @{ VPSOnly = $false; UGentOnly = $true; Force = $true; TestOnly = $false; StatusOnly = $false; GitOnly = $false; IncludeGit = $false }
            }
            "7" { 
                Write-Log "Selected: Test connectivity only" -Type "Info"
                return @{ VPSOnly = $false; UGentOnly = $false; Force = $false; TestOnly = $true; StatusOnly = $false; GitOnly = $false; IncludeGit = $false }
            }
            "8" { 
                Write-Log "Selected: Show deployment status" -Type "Info"
                return @{ VPSOnly = $false; UGentOnly = $false; Force = $false; TestOnly = $false; StatusOnly = $true; GitOnly = $false; IncludeGit = $false }
            }
            "9" { 
                Write-Log "Selected: Git commit and push only" -Type "Info"
                return @{ VPSOnly = $false; UGentOnly = $false; Force = $false; TestOnly = $false; StatusOnly = $false; GitOnly = $true; IncludeGit = $true }
            }
            "q" { 
                Write-Log "Exiting..." -Type "Info"
                exit 0
            }
            default { 
                Write-Log "Invalid choice. Please select 1-8 or q." -Type "Error"
            }
        }
    } while ($true)
}

# Function to test connectivity only
function Test-ConnectivityOnly {
    Write-Host ""
    Write-Log "Testing Connectivity" -Type "Header"
    
    $vpsConnected = Test-NetworkConnectivity -Target $vpsHost -Description "VPS ($vpsHost)"
    $ugentConnected = Test-NetworkConnectivity -Target $ugentDestDir -Description "UGent Share"
    
    Write-Host ""
    Write-Log "Connectivity Summary:" -Type "Header"
    $vpsStatus = if ($vpsConnected) { "[OK] Connected" } else { "[ERR] Not Connected" }
    $ugentStatus = if ($ugentConnected) { "[OK] Connected" } else { "[ERR] Not Connected" }
    
    Write-Log "VPS: $vpsStatus" -Type $(if ($vpsConnected) { "Success" } else { "Error" })
    Write-Log "UGent: $ugentStatus" -Type $(if ($ugentConnected) { "Success" } else { "Error" })
    
    if (-not $ugentConnected) {
        Write-Log "Tip: UGent share requires VPN connection" -Type "Info"
    }
    
    Write-Host ""
    Read-Host "Press Enter to continue"
}

# Function to show deployment status
function Show-DeploymentStatus {
    Write-Host ""
    Write-Log "Deployment Status Analysis" -Type "Header"
    
    if (-not (Test-Path $sourceDir)) {
        Write-Log "Source directory '$sourceDir' not found!" -Type "Error"
        return
    }
    
    # Get files and analyze changes
    $fullSourceDir = (Resolve-Path $sourceDir).Path
    $files = Get-ChildItem -Path $sourceDir -Recurse -File
    $currentHashes = @{}
    $changedFiles = @()
    $newFiles = @()
    $deletedFiles = @()
    
    # Load previous hashes
    $previousHashes = @{}
    if (Test-Path $hashFile) {
        try {
            $jsonContent = Get-Content $hashFile | ConvertFrom-Json
            if ($jsonContent) {
                $jsonContent.PSObject.Properties | ForEach-Object {
                    $previousHashes[$_.Name] = $_.Value
                }
            }
        }
        catch {
            Write-Log "Warning: Could not load hash file" -Type "Warning"
        }
    }
    
    # Calculate hashes and detect changes
    Write-Log "Analyzing files..." -Type "Info"
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($fullSourceDir.Length + 1)
        $hash = Get-CustomFileHash -FilePath $file.FullName
        $currentHashes[$relativePath] = $hash
        
        if ($previousHashes.ContainsKey($relativePath)) {
            if ($previousHashes[$relativePath] -ne $hash) {
                $changedFiles += $relativePath
            }
        } else {
            $newFiles += $relativePath
        }
    }
    
    # Find deleted files
    foreach ($oldFile in $previousHashes.Keys) {
        if (-not $currentHashes.ContainsKey($oldFile)) {
            $deletedFiles += $oldFile
        }
    }
    
    # Display status
    Write-Host ""
    Write-Log "File Status Summary:" -Type "Header"
    Write-Log "Total files: $($files.Count)" -Type "Info"
    Write-Log "New files: $($newFiles.Count)" -Type "Info"
    Write-Log "Changed files: $($changedFiles.Count)" -Type "Info"
    Write-Log "Deleted files: $($deletedFiles.Count)" -Type "Info"
    
    # Show recent changes
    if ($newFiles.Count -gt 0) {
        Write-Host ""
        Write-Log "Recent new files:" -Type "Header"
        foreach ($file in $newFiles | Select-Object -First 5) {
            Write-Log "  + $file" -Type "Success"
        }
        if ($newFiles.Count -gt 5) {
            Write-Log "  ... and $($newFiles.Count - 5) more" -Type "Info"
        }
    }
    
    if ($changedFiles.Count -gt 0) {
        Write-Host ""
        Write-Log "Recently changed files:" -Type "Header"
        foreach ($file in $changedFiles | Select-Object -First 5) {
            Write-Log "  ~ $file" -Type "Warning"
        }
        if ($changedFiles.Count -gt 5) {
            Write-Log "  ... and $($changedFiles.Count - 5) more" -Type "Info"
        }
    }
    
    # Check connectivity
    Write-Host ""
    Write-Log "Connectivity Status:" -Type "Header"
    Test-NetworkConnectivity -Target $vpsHost -Description "VPS ($vpsHost)" | Out-Null
    Test-NetworkConnectivity -Target $ugentDestDir -Description "UGent Share" | Out-Null
    
    Write-Host ""
    if ($newFiles.Count -eq 0 -and $changedFiles.Count -eq 0 -and $deletedFiles.Count -eq 0) {
        Write-Log "All files are up to date! No deployment needed." -Type "Success"
    } else {
        Write-Log "Files need to be deployed." -Type "Info"
    }
    
    Write-Host ""
    Read-Host "Press Enter to continue"
}

# Function to deploy to VPS
function Deploy-ToVPS {
    Write-Log "Starting VPS Deployment" -Type "Header"
    
    if (-not (Test-NetworkConnectivity -Target $vpsHost -Description "VPS ($vpsHost)")) {
        Write-Log "Cannot connect to VPS. Deployment skipped." -Type "Warning"
        return $false
    }
    
    try {
        # Build for VPS first
        Write-Log "Building Hugo site for moosedept.org..." -Type "Info"
        $buildResult = & "..\hugo.exe" --baseURL "https://moosedept.org" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Hugo build failed: $buildResult" -Type "Error"
            return $false
        }
        Write-Log "Hugo build completed successfully" -Type "Success"
        
        Write-Log "Cleaning destination directory on VPS..." -Type "Info"
        ssh $vpsHost "rm -rf $vpsPath/* $vpsPath/.*[^.]*" 2>$null
        
        Write-Log "Uploading files to VPS..." -Type "Info"
        Push-Location $sourceDir
        scp -r * "${vpsHost}:${vpsPath}/" 2>$null
        $scpSuccess = $LASTEXITCODE -eq 0
        Pop-Location
        
        if ($scpSuccess) {
            Write-Log "VPS deployment completed successfully!" -Type "Success"
            return $true
        } else {
            Write-Log "VPS deployment failed" -Type "Error"
            return $false
        }
    }
    catch {
        Write-Log "VPS deployment error: $($_.Exception.Message)" -Type "Error"
        return $false
    }
}

# Function to deploy to UGent share
function Deploy-ToUGent {
    param(
        [array]$ChangedFiles,
        [array]$NewFiles,
        [array]$DeletedFiles,
        [switch]$ForceAll = $false
    )
    
    Write-Log "Starting UGent Deployment" -Type "Header"
    
    if (-not (Test-NetworkConnectivity -Target $ugentDestDir -Description "UGent Share")) {
        Write-Log "Cannot access UGent share. Is VPN connected?" -Type "Warning"
        return $false
    }
    
    try {
        # Build for UGent first
        Write-Log "Building Hugo site for UGent..." -Type "Info"
        $buildResult = & "..\hugo.exe" --baseURL "http://users.ugent.be/~mvuijlst/" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Hugo build failed: $buildResult" -Type "Error"
            return $false
        }
        Write-Log "Hugo build completed successfully" -Type "Success"
        
        $fullSourceDir = (Resolve-Path $sourceDir).Path
        $filesToCopy = if ($ForceAll) { Get-ChildItem -Path $sourceDir -Recurse -File } else { $ChangedFiles + $NewFiles }
        $copiedCount = 0
        
        if ($filesToCopy.Count -gt 0) {
            Write-Log "Copying $($filesToCopy.Count) files to UGent share..." -Type "Info"
            
            foreach ($file in $filesToCopy) {
                if ($ForceAll) {
                    $relativePath = $file.FullName.Substring($fullSourceDir.Length + 1)
                    $sourcePath = $file.FullName
                } else {
                    $relativePath = $file
                    $sourcePath = Join-Path -Path $fullSourceDir -ChildPath $relativePath
                }
                
                $destPath = Join-Path -Path $ugentDestDir -ChildPath $relativePath
                $destDirForFile = Split-Path -Path $destPath -Parent
                
                if (-not (Test-Path $destDirForFile)) {
                    New-Item -ItemType Directory -Path $destDirForFile -Force | Out-Null
                }
                
                try {
                    Copy-Item -Path $sourcePath -Destination $destPath -Force
                    $copiedCount++
                    if ($Verbose) {
                        Write-Log "Copied: $relativePath" -Type "Detail"
                    }
                }
                catch {
                    Write-Log "Failed to copy $relativePath" -Type "Error"
                }
            }
        }
        
        Write-Log "UGent deployment completed! Copied: $copiedCount files" -Type "Success"
        return $true
    }
    catch {
        Write-Log "UGent deployment error: $($_.Exception.Message)" -Type "Error"
        return $false
    }
}

# Main deployment logic
function Start-Deployment {
    param([hashtable]$Options = @{})
    
    # Apply options
    $script:Force = $Options.Force -eq $true
    $script:VPSOnly = $Options.VPSOnly -eq $true
    $script:UGentOnly = $Options.UGentOnly -eq $true
    $gitOnly = $Options.GitOnly -eq $true
    $includeGit = $Options.IncludeGit -eq $true
    
    if ($Options.TestOnly -eq $true) { 
        Test-ConnectivityOnly
        return $true
    }
    if ($Options.StatusOnly -eq $true) { 
        Show-DeploymentStatus
        return $true
    }
    
    # Handle Git-only operations
    if ($gitOnly) {
        return Invoke-GitCommitAndPush
    }
    
    Write-Host ""
    Write-Log "Enhanced Hugo Deployment Script" -Type "Header"
    Write-Log "Source: $sourceDir" -Type "Info"
    if ($Force) {
        Write-Log "Mode: Force deployment (all files)" -Type "Warning"
    } else {
        Write-Log "Mode: Smart deployment (changed files only)" -Type "Info"
    }
    Write-Host ""
    
    if (-not (Test-Path $sourceDir)) {
        Write-Log "Source directory '$sourceDir' not found!" -Type "Error"
        return $false
    }
    
    # Analyze files
    $fullSourceDir = (Resolve-Path $sourceDir).Path
    $files = Get-ChildItem -Path $sourceDir -Recurse -File
    $currentHashes = @{}
    $changedFiles = @()
    $newFiles = @()
    $deletedFiles = @()
    
    # Load previous hashes
    $previousHashes = @{}
    if (Test-Path $hashFile) {
        try {
            $jsonContent = Get-Content $hashFile | ConvertFrom-Json
            if ($jsonContent) {
                $jsonContent.PSObject.Properties | ForEach-Object {
                    $previousHashes[$_.Name] = $_.Value
                }
            }
        }
        catch {
            Write-Log "Warning: Could not load hash file" -Type "Warning"
        }
    }
    
    # Calculate changes
    Write-Log "Analyzing file changes..." -Type "Info"
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($fullSourceDir.Length + 1)
        $hash = Get-CustomFileHash -FilePath $file.FullName
        $currentHashes[$relativePath] = $hash
        
        if ($previousHashes.ContainsKey($relativePath)) {
            if ($previousHashes[$relativePath] -ne $hash) {
                $changedFiles += $relativePath
            }
        } else {
            $newFiles += $relativePath
        }
    }
    
    # Find deleted files
    foreach ($oldFile in $previousHashes.Keys) {
        if (-not $currentHashes.ContainsKey($oldFile)) {
            $deletedFiles += $oldFile
        }
    }
    
    # Display summary
    Write-Host ""
    Write-Log "Change Summary:" -Type "Header"
    Write-Log "Total files: $($files.Count)" -Type "Info"
    Write-Log "New files: $($newFiles.Count)" -Type "Info"
    Write-Log "Changed files: $($changedFiles.Count)" -Type "Info"
    Write-Log "Deleted files: $($deletedFiles.Count)" -Type "Info"
    Write-Host ""
    
    # Deploy
    $vpsSuccess = $true
    $ugentSuccess = $true
    
    if (-not $UGentOnly) {
        $vpsSuccess = Deploy-ToVPS
    }
    
    if (-not $VPSOnly) {
        $ugentSuccess = Deploy-ToUGent -ChangedFiles $changedFiles -NewFiles $newFiles -DeletedFiles $deletedFiles -ForceAll:$Force
    }
    
    # Save hashes
    try {
        $currentHashes | ConvertTo-Json | Set-Content -Path $hashFile
        Write-Log "Hash file updated successfully" -Type "Success"
    }
    catch {
        Write-Log "Warning: Could not save hash file" -Type "Warning"
    }
    
    # Git operations (if requested)
    $gitSuccess = $true
    if ($includeGit) {
        Write-Host ""
        $gitSuccess = Invoke-GitCommitAndPush
    }

    # Final summary
    Write-Host ""
    Write-Log "Deployment Summary:" -Type "Header"
    if (-not $UGentOnly) {
        $vpsStatus = if ($vpsSuccess) { "[OK] SUCCESS" } else { "[ERR] FAILED" }
        $vpsColor = if ($vpsSuccess) { "Success" } else { "Error" }
        Write-Log "VPS Deployment: $vpsStatus" -Type $vpsColor
    }
    if (-not $VPSOnly) {
        $ugentStatus = if ($ugentSuccess) { "[OK] SUCCESS" } else { "[ERR] FAILED" }
        $ugentColor = if ($ugentSuccess) { "Success" } else { "Error" }
        Write-Log "UGent Deployment: $ugentStatus" -Type $ugentColor
    }
    if ($includeGit) {
        $gitStatus = if ($gitSuccess) { "[OK] SUCCESS" } else { "[ERR] FAILED" }
        $gitColor = if ($gitSuccess) { "Success" } else { "Error" }
        Write-Log "Git Operations: $gitStatus" -Type $gitColor
    }
    Write-Host ""

    if ($includeGit) {
        Write-Log "All deployments completed successfully!" -Type "Success"
        return ($vpsSuccess -and $ugentSuccess -and $gitSuccess)
    } else {
        return ($vpsSuccess -and $ugentSuccess)
    }
}

# Help
if ($args -contains "-h" -or $args -contains "--help") {
    Write-Host @"
Enhanced Hugo Deployment Script with Git Integration

USAGE:
    .\interactive-deploy.ps1 [OPTIONS]

OPTIONS:
    -Force          Deploy all files regardless of changes
    -VPSOnly        Deploy only to VPS (skip UGent)
    -UGentOnly      Deploy only to UGent share (skip VPS)
    -Quiet          Suppress verbose output and run non-interactively
    -h, --help      Show this help message

INTERACTIVE FEATURES:
    1. Deploy to both VPS and UGent + Git commit/push
    2. Deploy to VPS only
    3. Deploy to UGent only  
    4. Force deploy all files to both + Git commit/push
    5. Force deploy all files to VPS only
    6. Force deploy all files to UGent only
    7. Test connectivity only
    8. Show deployment status
    9. Git commit and push only

EXAMPLES:
    .\interactive-deploy.ps1                    # Interactive mode with menu
    .\interactive-deploy.ps1 -Quiet -Force     # Force deploy all files silently (no git)
    .\interactive-deploy.ps1 -VPSOnly          # Interactive VPS deployment
    .\interactive-deploy.ps1 -Quiet -UGentOnly # Deploy to UGent silently

"@ -ForegroundColor Cyan
    exit 0
}

# Main execution
if (-not $Quiet) {
    # Interactive mode
    do {
        $userChoice = Get-UserChoice
        $success = Start-Deployment -Options $userChoice
        
        if (-not $success) {
            Write-Host ""
            Write-Log "Deployment had some issues. Check the output above." -Type "Warning"
        }
        
        Write-Host ""
        $continue = Read-Host "Would you like to perform another deployment? (y/N)"
        if ($continue.ToLower() -ne "y" -and $continue.ToLower() -ne "yes") {
            break
        }
        
        Clear-Host
    } while ($true)
    
    Write-Log "Thank you for using the Enhanced Hugo Deployment Script!" -Type "Success"
} else {
    # Non-interactive mode
    $success = Start-Deployment
    
    if ($success) {
        Write-Log "All deployments completed successfully!" -Type "Success"
        exit 0
    } else {
        Write-Log "Some deployments failed. Check the output above." -Type "Error"
        exit 1
    }
}
