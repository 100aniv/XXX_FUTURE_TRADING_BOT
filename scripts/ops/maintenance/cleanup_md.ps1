# MD 문서 정리 스크립트
# 불필요한 MD 파일을 _archived_md로 이동

# 디렉토리 생성
New-Item -ItemType Directory -Path "_archived_md" -Force | Out-Null

# 이동할 파일 목록
$files_to_archive = @(
    "ARCHITECTURE_CHECKLIST.md",
    "ARCHITECTURE_FIX.md",
    "CHECKLIST_SUMMARY.md",
    "COLLECTOR_STANDARDIZATION.md",
    "CORRECT_ARCHITECTURE.md",
    "FINAL_CHECKLIST_REPORT.md",
    "FINAL_SUMMARY.md",
    "IMPLEMENTATION_IMPROVEMENTS.md",
    "IMPLEMENTATION_TIPS_VERIFICATION.md",
    "INTEGRATION_STATUS.md",
    "MIGRATION_GUIDE.md",
    "MODULE_STATUS.md",
    "MTF_CACHE_OPTIMIZATION.md",
    "PROGRESS.md",
    "PROGRESS_REPORT.md",
    "QUICK_TEST_GUIDE.md",
    "SIGNALS_MODULE_INTEGRATION.md",
    "SYSTEM_ARCHITECTURE.md",
    "TODO_URGENT.md",
    "UNIFIED_FLOW.md",
    "USAGE_GUIDE.md",
    "ANALYSIS.md"
)

# 파일 이동
$moved = 0
foreach ($file in $files_to_archive) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "_archived_md" -Force
        Write-Host "✅ $file 이동"
        $moved++
    }
}

Write-Host ""
Write-Host "🎉 총 $moved 개 파일을 _archived_md로 이동 완료!"
Write-Host ""
Write-Host "📄 남은 핵심 문서:"
Write-Host "   - README.md (프로젝트 소개)"
Write-Host "   - ARCHITECTURE_AND_IMPROVEMENTS.md (통합 문서)"
Write-Host "   - USAGE.md (사용 가이드)"
Write-Host "   - DOCKER_GUIDE.md (Docker 가이드)"
Write-Host "   - BACKTEST_GUIDE.md (백테스트 가이드)"
Write-Host "   - DATA_FILES.md (데이터 가이드)"
