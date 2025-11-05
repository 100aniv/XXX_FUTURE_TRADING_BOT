# 중요한 MD 파일 복구 스크립트

# 복구할 중요한 파일 목록
$important_files = @(
    "SYSTEM_ARCHITECTURE.md",
    "SIGNALS_MODULE_INTEGRATION.md",
    "BACKTEST_GUIDE.md",
    "USAGE.md",
    "TODO_URGENT.md"
)

# 복구 실행
$restored = 0
foreach ($file in $important_files) {
    $source = "_archived_md\$file"
    if (Test-Path $source) {
        Copy-Item -Path $source -Destination "." -Force
        Write-Host "✅ $file 복구"
        $restored++
    } else {
        Write-Host "⚠️  $file 없음"
    }
}

Write-Host ""
Write-Host "🎉 총 $restored 개 파일 복구 완료!"
Write-Host ""
Write-Host "📄 현재 MD 파일:"
Get-ChildItem -Path . -Filter "*.md" | Where-Object { $_.Name -ne "README.md" } | Select-Object Name | Format-List
