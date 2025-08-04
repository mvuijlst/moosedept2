param(
    [switch]$Force = $false,
    [switch]$VPSOnly = $false,
    [switch]$UGentOnly = $false,
    [switch]$SkipNews = $false,
    [switch]$Verbose = $false
)

# Configuration
$sourceDir = "public"
$ugentDestDir = "\\files\mvuijlst\www\users"
$vpsHost = "yusupov"
$vpsPath = "/home/django/moosedept"
$hashFile = "file-hashes.json"

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
        if ($Verbose) {
            Write-Log "Error calculating hash for $FilePath : $_" -Type "Error"
        }
        return "ERROR"
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
                    if ($Verbose) {
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
                        if ($Verbose) {
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
    Write-Host ""
    Write-Log "Enhanced Hugo Deployment Script" -Type "Header"
    Write-Log "Source: $sourceDir" -Type "Info"
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
    
    if ($Force) {
        Write-Log "Force mode enabled - deploying all files" -Type "Warning"
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
        Write-Log "Hash file updated successfully" -Type "Success"
    }
    catch {
        Write-Log "Warning: Could not save hash file: $($_.Exception.Message)" -Type "Warning"
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
    Write-Host ""
    
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
    -Verbose        Show detailed file operations
    -h, --help      Show this help message

EXAMPLES:
    .\enhanced-deploy.ps1                    # Normal deployment to both targets
    .\enhanced-deploy.ps1 -Force             # Force deploy all files
    .\enhanced-deploy.ps1 -VPSOnly           # Deploy only to VPS
    .\enhanced-deploy.ps1 -UGentOnly -Force  # Force deploy only to UGent

"@ -ForegroundColor Cyan
    exit 0
}

# Run the deployment
$success = Start-Deployment

# Exit with appropriate code
if ($success) {
    Write-Log "All deployments completed successfully!" -Type "Success"
    exit 0
} else {
    Write-Log "Some deployments failed. Check the output above." -Type "Error"
    exit 1
}
