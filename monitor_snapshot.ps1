# 모니터링 스냅샷 함수
function Write-MonitorSnapshot {
  param ([string]$label)

  $startText = Get-Content "test_12h_start_time.txt" -Raw
  $start = [datetime]::ParseExact($startText.Trim(), "yyyy-MM-dd HH:mm:ss", $null)
  $now = Get-Date
  $elapsed = $now - $start

  # Redis DBSIZE
  $dbsize = docker exec trading_redis redis-cli DBSIZE

  # 로그에서 이번 12h 구간만 필터링
  if (Test-Path "logs\application.log") {
    $logs = @(Get-Content logs\application.log | Where-Object {
      $_.Length -ge 19 -and
      ($ts = $_.Substring(0, 19)) -and
      ([datetime]::TryParse($ts, [ref]([datetime]::MinValue))) -and
      ([datetime]::ParseExact($ts, "yyyy-MM-dd HH:mm:ss", $null) -ge $start)
    })
  } else {
    $logs = @()
  }

  $entryCount  = ($logs | Select-String "ENTRY OPEN" | Measure-Object).Count
  $closedCount = ($logs | Select-String "TP1:|SL:" | Measure-Object).Count
  $errors = $logs | Select-String "ERROR|Traceback|Guard" | Select-Object -Last 20

  $lines = @()
  $lines += "`n=== [$label] 체크포인트 ==="
  $lines += ("현재 시각: {0}" -f $now.ToString("yyyy-MM-dd HH:mm:ss"))
  $lines += ("경과 시간: {0:hh\:mm\:ss}" -f $elapsed)
  $lines += ("Redis DBSIZE: {0}" -f $dbsize)
  $lines += ("ENTRY OPEN 누적(이번 12h): {0}" -f $entryCount)
  $lines += ("CLOSED(TP/SL) 누적(이번 12h): {0}" -f $closedCount)
  $lines += "최근 ERROR/Traceback/Guard 로그 (이번 12h 기준 최대 20줄):"
  if ($errors) {
    $lines += $errors
  } else {
    $lines += "  (없음)"
  }

  $monitorLog = "logs\phase16_real_paper_12h_monitoring.log"
  $lines | Out-File -FilePath $monitorLog -Append -Encoding utf8
  $lines | ForEach-Object { Write-Host $_ }
}
