-- 오래된 decisions 삭제 (entry/sl/tp 없는 것들)
DELETE FROM trading.decisions WHERE entry_price IS NULL;

-- 확인
SELECT COUNT(*) as remaining_decisions FROM trading.decisions;
