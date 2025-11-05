-- DB Migration: Remove bot_id column
-- Date: 2025-10-19
-- Reason: 옛날 3봇 시스템 → 통합 시스템

-- ============================================
-- 1. bot_id 컬럼 제거
-- ============================================
ALTER TABLE monitoring.signals DROP COLUMN IF EXISTS bot_id;

-- ============================================
-- 2. 확인
-- ============================================
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'monitoring' 
  AND table_name = 'signals'
ORDER BY ordinal_position;

-- ============================================
-- 완료!
-- ============================================
-- bot_id 컬럼이 사라졌습니다.
-- 이제 strategy_id만으로 구분합니다.
