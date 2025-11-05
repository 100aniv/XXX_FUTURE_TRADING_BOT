# Step 1: Restore all files
Write-Host "Step 1: Restoring all MD files..."
Get-ChildItem -Path "_archived_md" -Filter "*.md" | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination "." -Force
    Write-Host "  Restored: $($_.Name)"
}

Write-Host ""
Write-Host "Step 2: Moving less important files back to archive..."

# Step 2: Move less important files back
$lessImportant = @(
    "ANALYSIS.md",
    "ARCHITECTURE_FIX.md",
    "CHECKLIST_SUMMARY.md",
    "COLLECTOR_STANDARDIZATION.md",
    "CORRECT_ARCHITECTURE.md",
    "FINAL_SUMMARY.md",
    "INTEGRATION_STATUS.md",
    "MIGRATION_GUIDE.md",
    "MODULE_STATUS.md",
    "PROGRESS.md",
    "PROGRESS_REPORT.md",
    "UNIFIED_FLOW.md",
    "USAGE_GUIDE.md"
)

foreach ($file in $lessImportant) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "_archived_md" -Force
        Write-Host "  Archived: $file"
    }
}

Write-Host ""
Write-Host "Done! Important MD files in root:"
Get-ChildItem -Path "." -Filter "*.md" | Where-Object { $_.Name -ne "README.md" } | ForEach-Object {
    Write-Host "  - $($_.Name)"
}
