-- ============================================
-- decisions 테이블에 entry/sl/tp 컬럼 추가
-- ============================================

ALTER TABLE trading.decisions 
ADD COLUMN IF NOT EXISTS entry_price NUMERIC,
ADD COLUMN IF NOT EXISTS sl_price NUMERIC,
ADD COLUMN IF NOT EXISTS tp_price NUMERIC;

-- 확인
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'trading' 
  AND table_name = 'decisions'
ORDER BY ordinal_position;
