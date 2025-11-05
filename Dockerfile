# ============================================
# 통합 트레이딩 시스템 v2.0 Dockerfile
# ============================================

FROM python:3.11-slim

WORKDIR /app

# 시간대 및 로케일 설정 (한국)
ENV TZ=Asia/Seoul
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 시스템 패키지 업데이트
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY collectors/ collectors/
COPY indicators/ indicators/
COPY signals/ signals/
COPY strategies/ strategies/
COPY execution/ execution/
COPY common/ common/
COPY core/ core/
COPY metrics/ metrics/
COPY monitoring/ monitoring/
COPY analytics/ analytics/
COPY database/ database/
COPY tests/ tests/
COPY reports/ reports/
COPY scripts/ scripts/

# 데이터 및 설정
COPY data/ data/
COPY config.yml .

# 메인 파일
COPY main.py .

# 로그 디렉토리
RUN mkdir -p logs

# 기본 명령어
CMD ["python", "-u", "main.py"]
