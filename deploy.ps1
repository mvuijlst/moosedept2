param(
    [switch]$Force = $false,
    [switch]$VPSOnly = $false,
    [switch]$UGentOnly = $false,
    [switch]$SkipNews = $false,
    [switch]$Verbose,
    [switch]$Interactive,
    [switch]$Quiet = $false
)

# Set defaults
if (-not $PSBoundParameters.ContainsKey('Verbose')) { $Verbose = $true }
if (-not $PSBoundParameters.ContainsKey('Interactive')) { $Interactive = $true }

# Configuration
$sourceDir = "public"
$ugentDestDir = "\\files\mvuijlst\www\users"
$vpsHost = "yusupov"
$vpsPath = "/home/django/moosedept"
$hashFile = "file-hashes.json"

# Override verbose setting if Quiet is specified
if ($Quiet) {
    $Verbose = $false
    $Interactive = $false
}

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
        [string]$Type = "Info",
        [switch]$NoNewline
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
    
    if ($NoNewline) {
        Write-Host $fullMessage -ForegroundColor $colors[$Type] -NoNewline
    } else {
        Write-Host $fullMessage -ForegroundColor $colors[$Type]
    }
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

# Enhanced file hash calculation
function Get-CustomFileHash {
    param(
        [string]$FilePath
    )
    
    try {
        $md5 = [System.Security.Cryptography.MD5]::Create()
        $stream = [System.IO.File]::OpenRead($FilePath)
        $hashBytes = $md5.ComputeHash($stream)
        $stream.Close()
        $md5.Dispose()
        
        $hashString = [System.BitConverter]::ToString($hashBytes).Replace("-", "")
        return $hashString
    }
    catch {
        if ($Verbose -and -not $Quiet) {
            Write-Log "Error calculating hash for $FilePath : $_" -Type "Error"
        }
        return "ERROR"
    }
}

# Interactive menu function
function Show-InteractiveMenu {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║           Hugo Deployment Options             ║" -ForegroundColor Cyan
    Write-Host "╠═══════════════════════════════════════════════╣" -ForegroundColor Cyan
    Write-Host "║  1. Deploy to both VPS and UGent              ║" -ForegroundColor White
    Write-Host "║  2. Deploy to VPS only                        ║" -ForegroundColor White
    Write-Host "║  3. Deploy to UGent only                      ║" -ForegroundColor White
    Write-Host "║  4. Force deploy all files to both            ║" -ForegroundColor Yellow
    Write-Host "║  5. Force deploy all files to VPS only        ║" -ForegroundColor Yellow
    Write-Host "║  6. Force deploy all files to UGent only      ║" -ForegroundColor Yellow
    Write-Host "║  7. Test connectivity only                    ║" -ForegroundColor Gray
    Write-Host "║  8. Show deployment status                    ║" -ForegroundColor Gray
    Write-Host "║  q. Quit                                      ║" -ForegroundColor Red
    Write-Host "╚═══════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

# Function to get user choice
function Get-UserChoice {
    do {
        Show-InteractiveMenu
        $choice = Read-Host "Please select an option (1-8 or q)"
        
        switch ($choice.ToLower()) {
            "1" { 
                Write-Log "Selected: Deploy to both VPS and UGent" -Type "Info"
                return @{ VPSOnly = $false; UGentOnly = $false; Force = $false; TestOnly = $false; StatusOnly = $false }
            }
            "2" { 
                Write-Log "Selected: Deploy to VPS only" -Type "Info"
                return @{ VPSOnly = $true; UGentOnly = $false; Force = $false; TestOnly = $false; StatusOnly = $false }
            }
            "3" { 
                Write-Log "Selected: Deploy to UGent only" -Type "Info"
                return @{ VPSOnly = $false; UGentOnly = $true; Force = $false; TestOnly = $false; StatusOnly = $false }
            }
            "4" { 
                Write-Log "Selected: Force deploy all files to both" -Type "Warning"
                return @{ VPSOnly = $false; UGentOnly = $false; Force = $true; TestOnly = $false; StatusOnly = $false }
            }
            "5" { 
                Write-Log "Selected: Force deploy all files to VPS only" -Type "Warning"
                return @{ VPSOnly = $true; UGentOnly = $false; Force = $true; TestOnly = $false; StatusOnly = $false }
            }
            "6" { 
                Write-Log "Selected: Force deploy all files to UGent only" -Type "Warning"
                return @{ VPSOnly = $false; UGentOnly = $true; Force = $true; TestOnly = $false; StatusOnly = $false }
            }
            "7" { 
                Write-Log "Selected: Test connectivity only" -Type "Info"
                return @{ VPSOnly = $false; UGentOnly = $false; Force = $false; TestOnly = $true; StatusOnly = $false }
            }
            "8" { 
                Write-Log "Selected: Show deployment status" -Type "Info"
                return @{ VPSOnly = $false; UGentOnly = $false; Force = $false; TestOnly = $false; StatusOnly = $true }
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
    if (-not $Quiet) {
        Read-Host "Press Enter to continue"
    }
}

# Function to show deployment status
function Show-DeploymentStatus {
    Write-Host ""
    Write-Log "Deployment Status Analysis" -Type "Header"
    
    # Validate source directory
    if (-not (Test-Path $sourceDir)) {
        Write-Log "Source directory '$sourceDir' not found!" -Type "Error"
        return
    }
    
    # Get current files and calculate changes
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
            Write-Log "Warning: Could not load hash file: $($_.Exception.Message)" -Type "Warning"
        }
    }
    
    # Calculate current hashes and detect changes
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
    
    # Display detailed status
    Write-Host ""
    Write-Log "File Status Summary:" -Type "Header"
    Write-Log "Total files: $($files.Count)" -Type "Info"
    Write-Log "New files: $($newFiles.Count)" -Type "Info"
    Write-Log "Changed files: $($changedFiles.Count)" -Type "Info"
    Write-Log "Deleted files: $($deletedFiles.Count)" -Type "Info"
    
    if ($newFiles.Count -gt 0) {
        Write-Host ""
        Write-Log "New files:" -Type "Header"
        foreach ($file in $newFiles | Select-Object -First 10) {
            Write-Log "  + $file" -Type "Success"
        }
        if ($newFiles.Count -gt 10) {
            Write-Log "  ... and $($newFiles.Count - 10) more" -Type "Info"
        }
    }
    
    if ($changedFiles.Count -gt 0) {
        Write-Host ""
        Write-Log "Changed files:" -Type "Header"
        foreach ($file in $changedFiles | Select-Object -First 10) {
            Write-Log "  ~ $file" -Type "Warning"
        }
        if ($changedFiles.Count -gt 10) {
            Write-Log "  ... and $($changedFiles.Count - 10) more" -Type "Info"
        }
    }
    
    if ($deletedFiles.Count -gt 0) {
        Write-Host ""
        Write-Log "Deleted files:" -Type "Header"
        foreach ($file in $deletedFiles | Select-Object -First 10) {
            Write-Log "  - $file" -Type "Error"
        }
        if ($deletedFiles.Count -gt 10) {
            Write-Log "  ... and $($deletedFiles.Count - 10) more" -Type "Info"
        }
    }
    
    # Check connectivity
    Write-Host ""
    Write-Log "Connectivity Status:" -Type "Header"
    $vpsConnected = Test-NetworkConnectivity -Target $vpsHost -Description "VPS ($vpsHost)"
    $ugentConnected = Test-NetworkConnectivity -Target $ugentDestDir -Description "UGent Share"
    
    Write-Host ""
    if ($newFiles.Count -eq 0 -and $changedFiles.Count -eq 0 -and $deletedFiles.Count -eq 0) {
        Write-Log "All files are up to date! No deployment needed." -Type "Success"
    } else {
        Write-Log "Files need to be deployed." -Type "Info"
    }
    
    Write-Host ""
    if (-not $Quiet) {
        Read-Host "Press Enter to continue"
    }
}

# Function to deploy to VPS
function Deploy-ToVPS {
    param(
        [array]$FilesToDeploy,
        [bool]$CleanFirst = $true
    )
    
    Write-Log "Starting VPS Deployment" -Type "Header"
    
    if (-not (Test-NetworkConnectivity -Target $vpsHost -Description "VPS ($vpsHost)")) {
        Write-Log "Cannot connect to VPS. Deployment skipped." -Type "Warning"
        return $false
    }
    
    try {
        if ($CleanFirst) {
            Write-Log "Cleaning destination directory on VPS..." -Type "Info"
            $cleanResult = ssh $vpsHost "rm -rf $vpsPath/* $vpsPath/.*[^.]*" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Log "VPS directory cleaned successfully" -Type "Success"
            } else {
                Write-Log "Warning: VPS clean command had issues: $cleanResult" -Type "Warning"
            }
        }
        
        Write-Log "Uploading files to VPS..." -Type "Info"
        Push-Location $sourceDir
        
        $scpResult = scp -r * "${vpsHost}:${vpsPath}/" 2>&1
        $scpSuccess = $LASTEXITCODE -eq 0
        
        Pop-Location
        
        if ($scpSuccess) {
            Write-Log "VPS deployment completed successfully!" -Type "Success"
            return $true
        } else {
            Write-Log "VPS deployment failed: $scpResult" -Type "Error"
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
        $fullSourceDir = (Resolve-Path $sourceDir).Path
        $filesToCopy = if ($ForceAll) { Get-ChildItem -Path $sourceDir -Recurse -File } else { $ChangedFiles + $NewFiles }
        $copiedCount = 0
        $deletedCount = 0
        
        # Copy new and changed files
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
                
                # Create directory structure
                $destDirForFile = Split-Path -Path $destPath -Parent
                if (-not (Test-Path $destDirForFile)) {
                    New-Item -ItemType Directory -Path $destDirForFile -Force | Out-Null
                }
                
                # Copy the file
                try {
                    Copy-Item -Path $sourcePath -Destination $destPath -Force
                    $copiedCount++
                    if ($Verbose -and -not $Quiet) {
                        Write-Log "Copied: $relativePath" -Type "Detail"
                    }
                }
                catch {
                    Write-Log "Failed to copy $relativePath : $($_.Exception.Message)" -Type "Error"
                }
            }
        }
        
        # Delete removed files
        if (-not $ForceAll -and $DeletedFiles.Count -gt 0) {
            Write-Log "Removing $($DeletedFiles.Count) deleted files..." -Type "Info"
            
            foreach ($file in $DeletedFiles) {
                $destPath = Join-Path -Path $ugentDestDir -ChildPath $file
                if (Test-Path $destPath) {
                    try {
                        Remove-Item -Path $destPath -Force
                        $deletedCount++
                        if ($Verbose -and -not $Quiet) {
                            Write-Log "Deleted: $file" -Type "Detail"
                        }
                    }
                    catch {
                        Write-Log "Failed to delete $file : $($_.Exception.Message)" -Type "Error"
                    }
                }
            }
        }
        
        Write-Log "UGent deployment completed! Copied: $copiedCount, Deleted: $deletedCount" -Type "Success"
        return $true
    }
    catch {
        Write-Log "UGent deployment error: $($_.Exception.Message)" -Type "Error"
        return $false
    }
}

# Main deployment logic
function Start-Deployment {
    param(
        [hashtable]$Options = @{}
    )
    
    # Override global variables with options if provided
    if ($Options.ContainsKey("Force")) { $script:Force = $Options.Force }
    if ($Options.ContainsKey("VPSOnly")) { $script:VPSOnly = $Options.VPSOnly }
    if ($Options.ContainsKey("UGentOnly")) { $script:UGentOnly = $Options.UGentOnly }
    if ($Options.ContainsKey("TestOnly") -and $Options.TestOnly) { 
        Test-ConnectivityOnly
        return $true
    }
    if ($Options.ContainsKey("StatusOnly") -and $Options.StatusOnly) { 
        Show-DeploymentStatus
        return $true
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
    
    # Validate source directory
    if (-not (Test-Path $sourceDir)) {
        Write-Log "Source directory '$sourceDir' not found!" -Type "Error"
        exit 1
    }
    
    # Get current files and calculate changes
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
            Write-Log "Warning: Could not load hash file: $($_.Exception.Message)" -Type "Warning"
        }
    }
    
    # Calculate current hashes and detect changes
    if (-not $Quiet) {
        Write-Log "Analyzing file changes..." -Type "Info"
    }
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
    if (-not $Quiet) {
        Write-Host ""
        Write-Log "Change Summary:" -Type "Header"
        Write-Log "Total files: $($files.Count)" -Type "Info"
        Write-Log "New files: $($newFiles.Count)" -Type "Info"
        Write-Log "Changed files: $($changedFiles.Count)" -Type "Info"
        Write-Log "Deleted files: $($deletedFiles.Count)" -Type "Info"
        Write-Host ""
        
        if ($Force) {
            Write-Log "Force mode enabled - deploying all files" -Type "Warning"
        }
    }
    
    # Deployment logic
    $vpsSuccess = $true
    $ugentSuccess = $true
    
    if (-not $UGentOnly) {
        $vpsSuccess = Deploy-ToVPS -FilesToDeploy $files -CleanFirst (-not $Force)
    }
    
    if (-not $VPSOnly) {
        $ugentSuccess = Deploy-ToUGent -ChangedFiles $changedFiles -NewFiles $newFiles -DeletedFiles $deletedFiles -ForceAll:$Force
    }
    
    # Save updated hashes
    try {
        $currentHashes | ConvertTo-Json | Set-Content -Path $hashFile
        if (-not $Quiet) {
            Write-Log "Hash file updated successfully" -Type "Success"
        }
    }
    catch {
        Write-Log "Warning: Could not save hash file: $($_.Exception.Message)" -Type "Warning"
    }
    
    # Final summary
    if (-not $Quiet) {
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
        Write-Host ""
    }
    
    return ($vpsSuccess -and $ugentSuccess)
}

# Display help if requested
if ($args -contains "-h" -or $args -contains "--help") {
    Write-Host @"
Enhanced Hugo Deployment Script

USAGE:
    .\enhanced-deploy.ps1 [OPTIONS]

OPTIONS:
    -Force          Deploy all files regardless of changes
    -VPSOnly        Deploy only to VPS (skip UGent)
    -UGentOnly      Deploy only to UGent share (skip VPS)
    -SkipNews       Skip news fetching (not implemented yet)
    -Verbose        Show detailed file operations (default: true)
    -Quiet          Suppress verbose output and run non-interactively
    -Interactive    Show interactive menu (default: true)
    -h, --help      Show this help message

EXAMPLES:
    .\enhanced-deploy.ps1                    # Interactive mode with menu
    .\enhanced-deploy.ps1 -Quiet -Force     # Force deploy all files silently
    .\enhanced-deploy.ps1 -VPSOnly          # Interactive menu for VPS deployment
    .\enhanced-deploy.ps1 -Quiet -UGentOnly # Deploy to UGent silently

"@ -ForegroundColor Cyan
    exit 0
}

# Main execution logic
if ($Interactive -and -not $Quiet) {
    # Interactive mode - show menu and get user choice
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
        
        # Clear screen for next iteration
        Clear-Host
    } while ($true)
    
    Write-Log "Done." -Type "Success"
} else {
    # Non-interactive mode - use command line parameters
    $success = Start-Deployment
    
    # Exit with appropriate code
    if ($success) {
        if (-not $Quiet) {
            Write-Log "All deployments completed successfully!" -Type "Success"
        }
        exit 0
    } else {
        if (-not $Quiet) {
            Write-Log "Some deployments failed. Check the output above." -Type "Error"
        }
        exit 1
    }
}
