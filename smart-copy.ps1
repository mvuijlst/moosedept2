param(
    [switch]$Force = $false
)

$sourceDir = "public"
$destDir = "\\files\mvuijlst\www\users"
$hashFile = "file-hashes.json"

# Function to calculate MD5 hash that works in older PowerShell versions
function Calculate-FileHash {
    param(
        [string]$FilePath
    )
    
    try {
        $md5 = [System.Security.Cryptography.MD5]::Create()
        $stream = [System.IO.File]::OpenRead($FilePath)
        $hashBytes = $md5.ComputeHash($stream)
        $stream.Close()
        $md5.Dispose()
        
        # Convert bytes to hex string
        $hashString = [System.BitConverter]::ToString($hashBytes).Replace("-", "")
        return $hashString
    }
    catch {
        Write-Host "Error calculating hash for $FilePath : $_" -ForegroundColor Red
        return "ERROR"
    }
}

# Create directories if they don't exist
if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force
}

# Get absolute path of the source directory for proper path manipulation
$fullSourceDir = (Resolve-Path $sourceDir).Path

# If Force parameter is used, copy all files
if ($Force) {
    Write-Host "Force parameter detected - copying ALL files regardless of changes..."
    $files = Get-ChildItem -Path $sourceDir -Recurse -File
    
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($fullSourceDir.Length + 1)
        $sourcePath = Join-Path -Path $fullSourceDir -ChildPath $relativePath
        $destPath = Join-Path -Path $destDir -ChildPath $relativePath
        
        # Create directory structure if it doesn't exist
        $destDirForFile = Split-Path -Path $destPath -Parent
        if (-not (Test-Path $destDirForFile)) {
            New-Item -ItemType Directory -Path $destDirForFile -Force | Out-Null
        }
        
        # Copy the file
        Copy-Item -Path $sourcePath -Destination $destPath -Force
    }
    
    Write-Host "Force copied $($files.Count) files"
    
    # Update the hash file for future runs
    $currentHashes = @{}
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($fullSourceDir.Length + 1)
        $hash = Calculate-FileHash -FilePath $file.FullName
        $currentHashes[$relativePath] = $hash
    }
    
    # Save current hashes for next run
    $currentHashes | ConvertTo-Json | Set-Content -Path $hashFile
    
    Write-Host ""
    Write-Host "Summary:"
    Write-Host "  Force copied: $($files.Count)"
} else {
    # Load previous hashes if the file exists
    $previousHashes = @{}
    if (Test-Path $hashFile) {
        # Use a method compatible with older PowerShell versions
        $jsonContent = Get-Content $hashFile | ConvertFrom-Json
        # Convert PSObject to hashtable manually
        if ($jsonContent) {
            $jsonContent.PSObject.Properties | ForEach-Object {
                $previousHashes[$_.Name] = $_.Value
            }
        }
    }
    
    # Get current file hashes
    $currentHashes = @{}
    $changedFiles = @()
    $newFiles = @()
    $files = Get-ChildItem -Path $sourceDir -Recurse -File
    
    # Calculate hashes and identify changed/new files
    foreach ($file in $files) {
        # Extract the relative path correctly
        $relativePath = $file.FullName.Substring($fullSourceDir.Length + 1)
        $hash = Calculate-FileHash -FilePath $file.FullName
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
    $deletedFiles = @()
    foreach ($oldFile in $previousHashes.Keys) {
        if (-not $currentHashes.ContainsKey($oldFile)) {
            $deletedFiles += $oldFile
        }
    }
    
    # Copy new and changed files
    Write-Host "Copying new and changed files..."
    foreach ($file in ($changedFiles + $newFiles)) {
        $sourcePath = Join-Path -Path $fullSourceDir -ChildPath $file
        $destPath = Join-Path -Path $destDir -ChildPath $file
        
        # Create directory structure if it doesn't exist
        $destDirForFile = Split-Path -Path $destPath -Parent
        if (-not (Test-Path $destDirForFile)) {
            New-Item -ItemType Directory -Path $destDirForFile -Force | Out-Null
        }
        
        # Copy the file
        Copy-Item -Path $sourcePath -Destination $destPath -Force
        Write-Host "Copied: $file"
    }
    
    # Delete files that no longer exist
    foreach ($file in $deletedFiles) {
        $destPath = Join-Path -Path $destDir -ChildPath $file
        if (Test-Path $destPath) {
            Remove-Item -Path $destPath -Force
            Write-Host "Deleted: $file"
        }
    }
    
    # Save current hashes for next run
    $currentHashes | ConvertTo-Json | Set-Content -Path $hashFile
    
    # Summary
    Write-Host ""
    Write-Host "Summary:"
    Write-Host "  New files: $($newFiles.Count)"
    Write-Host "  Changed files: $($changedFiles.Count)"
    Write-Host "  Deleted files: $($deletedFiles.Count)"
    Write-Host "  Total files: $($files.Count)"
}
