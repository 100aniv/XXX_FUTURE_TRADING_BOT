# MD 파일 재정리 스크립트
# 중요한 파일은 루트에, 덜 중요한 파일은 _archived_md로

Write-Host "=" * 80
Write-Host "📋 MD 파일 재정리"
Write-Host "=" * 80
Write-Host ""

# 덜 중요한 파일들만 archived로 이동
$to_archive = @(
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

Write-Host "📦 덜 중요한 파일 archived로 이동:"
$moved = 0
foreach ($file in $to_archive) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "_archived_md" -Force
        Write-Host "   → $file"
        $moved++
    }
}

Write-Host ""
Write-Host "✅ $moved 개 파일 archived로 이동"
Write-Host ""
Write-Host "=" * 80
Write-Host "📄 루트에 남은 중요한 MD 파일:"
Write-Host "=" * 80

$important_files = Get-ChildItem -Path . -Filter "*.md" | Where-Object { $_.Name -ne "README.md" } | Select-Object -ExpandProperty Name | Sort-Object

foreach ($file in $important_files) {
    Write-Host "   ✅ $file"
}

Write-Host ""
Write-Host "🎉 재정리 완료!"
