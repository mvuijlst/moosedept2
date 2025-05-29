$sourceDir = "public"
$destDir = "\\files\mvuijlst\www\users"
$hashFile = "file-hashes.json"

# Create directories if they don't exist
if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force
}

# Load previous hashes if the file exists
$previousHashes = @{}
if (Test-Path $hashFile) {
    $previousHashes = Get-Content $hashFile | ConvertFrom-Json -AsHashtable
    if ($null -eq $previousHashes) { $previousHashes = @{} }
}

# Get current file hashes
$currentHashes = @{}
$changedFiles = @()
$newFiles = @()
$files = Get-ChildItem -Path $sourceDir -Recurse -File

# Calculate hashes and identify changed/new files
foreach ($file in $files) {
    $relativePath = $file.FullName.Substring($sourceDir.Length + 1)
    $hash = (Get-FileHash -Path $file.FullName -Algorithm MD5).Hash
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
    $sourcePath = Join-Path -Path $sourceDir -ChildPath $file
    $destPath = Join-Path -Path $destDir -ChildPath $file
    
    # Create directory structure if it doesn't exist
    $destDir = Split-Path -Path $destPath -Parent
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
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
