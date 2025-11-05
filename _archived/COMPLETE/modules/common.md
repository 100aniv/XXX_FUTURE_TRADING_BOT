# 🔧 Common 모듈

**공통 유틸리티** - 모든 모듈에서 사용

**경로**: `common/`

---

## 파일 구조

```
common/
├── database.py      # PostgreSQL 연결
├── logger.py        # 로깅
├── config.py        # 설정 관리
├── calculations.py  # 계산 함수
├── messaging.py     # 텔레그램
└── utils.py         # 유틸리티
```

---

## database.py

### get_db_connection()
```python
from common.database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM monitoring.signals")
        results = cur.fetchall()
```

---

## logger.py

```python
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="trading")
logger.info("✅ 메시지")
```

---

## config.py

```python
from common.config import load_config

config = load_config()
print(config['strategy_selector'])  # 'ensemble'
```

---

## calculations.py

```python
from common.calculations import position_size, tp_from_rr

qty, risk = position_size(entry, sl, equity, risk_frac)
tp = tp_from_rr(signal, rr=2.0)
```

---

## messaging.py

```python
from common.messaging import tg

tg("🚀 시작!", config)
```

---

## utils.py

```python
from common.utils import buffer_to_df

df = buffer_to_df("BTCUSDT", buffers)
```

---

**최종 업데이트**: 2025-10-19
