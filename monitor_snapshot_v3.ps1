# 모니터링 스냅샷 함수 (v3)
function Write-MonitorSnapshot {
  param([string]$label)

  $startText = Get-Content "test_12h_start_time.txt" -Raw
  $startTime = [datetime]::ParseExact($startText.Trim(), "yyyy-MM-dd HH:mm:ss", $null)
  $now = Get-Date
  $elapsed = $now - $startTime

  # Redis 상태
  $db = docker exec trading_redis redis-cli DBSIZE

  # 시작 이후 로그만 필터링
  if (Test-Path "logs\application.log") {
    $logs = @(Get-Content logs\application.log | Where-Object {
      $_.Length -ge 19 -and
      ($tsStr = $_.Substring(0, 19)) -and
      ([datetime]::TryParse($tsStr, [ref]([datetime]::MinValue))) -and
      ([datetime]::ParseExact($tsStr, "yyyy-MM-dd HH:mm:ss", $null) -ge $startTime)
    })
  } else {
    $logs = @()
  }

  $entry  = ($logs | Select-String "ENTRY OPEN" | Measure-Object).Count
  $closed = ($logs | Select-String "TP1:|SL:" | Measure-Object).Count
  $errors = $logs | Select-String "ERROR|Traceback|Guard" | Select-Object -Last 20

  Write-Host ""
  Write-Host "=== [$label] 체크포인트 ===" -ForegroundColor Cyan
  Write-Host "현재 시각: $($now.ToString("yyyy-MM-dd HH:mm:ss"))"
  Write-Host ("경과 시간: {0:hh\:mm\:ss}" -f $elapsed)
  Write-Host "Redis DBSIZE: $db"
  Write-Host "ENTRY OPEN(이 실행 기준): $entry"
  Write-Host "CLOSED(TP/SL)(이 실행 기준): $closed"
  Write-Host "최근 ERROR/Traceback/Guard (최대 20줄):"
  if ($errors) {
    $errors | ForEach-Object { Write-Host "  $_" }
  } else {
    Write-Host "  (없음)"
  }

  # 모니터링 로그 파일에 기록
  $lines = @()
  $lines += ""
  $lines += "=== [$label] 체크포인트 ==="
  $lines += "현재 시각: $($now.ToString("yyyy-MM-dd HH:mm:ss"))"
  $lines += ("경과 시간: {0:hh\:mm\:ss}" -f $elapsed)
  $lines += "Redis DBSIZE: $db"
  $lines += "ENTRY OPEN: $entry"
  $lines += "CLOSED: $closed"
  $lines += "최근 ERROR/Traceback/Guard:"
  if ($errors) {
    $lines += ($errors | ForEach-Object { "  $_" })
  } else {
    $lines += "  (없음)"
  }

  $lines | Out-File "logs\phase16_real_paper_12h_v3_monitoring.log" -Append -Encoding utf8
}
