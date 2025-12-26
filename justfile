# PHASE36-1 S3: SSOT Workflow Gates
# ===================================

# Default recipe (list all)
default:
    @just --list

# Gate 0: Environment + Dependencies Check
doctor:
    @echo "🔍 SSOT Gate 0: Doctor (환경/의존성 검증)"
    @python --version
    @echo "✅ Python version OK"
    @python -c "import psutil, redis, sqlalchemy, pandas, numpy, yaml; print('✅ Core dependencies OK')"
    @echo "✅ Doctor PASS"

# Gate 1: Fast Tests (unit tests, 빠른 검증)
fast:
    @echo "🚀 SSOT Gate 1: Fast (unit tests)"
    pytest tests/unit --tb=short -v --maxfail=3
    @echo "✅ Fast PASS"

# Gate 2: Regression Tests (통합 테스트)
regression:
    @echo "🔄 SSOT Gate 2: Regression (integration tests)"
    pytest tests/integration --tb=short -v --maxfail=5
    @echo "✅ Regression PASS"

# Gate 3: Full Tests (전체 테스트, 느림)
full:
    @echo "🎯 SSOT Gate 3: Full (all tests)"
    pytest tests/ --tb=short -v
    @echo "✅ Full PASS"

# Convenience: Run all gates in sequence
gates:
    @echo "🚪 Running ALL SSOT Gates (doctor → fast → regression)"
    @just doctor
    @just fast
    @just regression
    @echo "✅ ALL GATES PASS"
