FROM python:3.10-slim

# 보안 및 파이썬 라이브러리 설치를 위한 필수 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 패키지 목록 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 소스 코드 복사
COPY . .

# FastAPI uvicorn 서버 실행 (포트 8080)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
