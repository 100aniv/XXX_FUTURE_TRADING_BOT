$files = @("IMPLEMENTATION_IMPROVEMENTS.md", "IMPLEMENTATION_TIPS_VERIFICATION.md")

foreach ($f in $files) {
    if (Test-Path $f) {
        Move-Item $f -Destination "_archived_md\" -Force
        Write-Host "Moved: $f"
    } else {
        Write-Host "Not found: $f"
    }
}

Write-Host ""
Write-Host "Current MD files:"
Get-ChildItem "*.md" | Select-Object Name
