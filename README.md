# 영수증 OCR 자동 추출 시스템

> 영수증 이미지나 PDF를 올리면 → 글자를 읽고 → AI가 학습해서 → 가게 이름, 날짜, 금액 같은 정보를 자동으로 뽑아주는 백엔드 서버

---

## 이게 뭔가요? (쉬운 설명)

예를 들어 편의점 영수증 사진을 찍어서 이 서버에 보내면:

```
입력:  영수증 사진 (jpg, png, pdf)

출력:
{
  "store_name":   "GS25 강남점",
  "date":         "2024-01-15",
  "total_amount": "15000",
  "items": [
    { "name": "삼각김밥", "price": "1200" },
    { "name": "음료수",   "price": "2000" }
  ]
}
```

이런 식으로 영수증 안의 정보를 자동으로 JSON 형태로 정리해서 돌려줍니다.

---

## 전체 흐름 (파이프라인)

```
[사용자]
    |
    | 1. 영수증 이미지/PDF 업로드
    v
[API 서버 - FastAPI]
    |
    | 2. 파일 저장 + 타입 판별 (이미지? PDF?)
    v
[전처리]
    ├── 이미지 → 필요한 부분만 잘라서 여러 이미지 경로 반환
    └── PDF   → 그대로 PDF 경로 반환
    |
    | 3. 즉시 job_id 반환 ("접수됐어요" 응답)
    v
[작업 큐 - Celery + Redis]  ← 줄 세워서 순서대로 처리
    |
    | 4. OCR (글자 읽기)
    |    EasyOCR로 이미지에서 텍스트 추출
    v
[AI 필드 추출]
    |
    | 5. 뽑은 텍스트에서 필요한 필드만 구조화
    |    (처음엔 Claude AI 사용 → 나중엔 직접 학습한 모델로 교체)
    v
[결과 저장 - Redis / DB]
    |
    | 6. job_id로 결과 조회 가능
    v
[사용자에게 JSON 결과 반환]
```

---

## 현재 완성된 것 / 앞으로 할 것

| 구분 | 항목 | 상태 |
|------|------|------|
| ✅ 완료 | FastAPI 서버 기본 구조 | 완성 |
| ✅ 완료 | 파일 업로드 + 타입 판별 | 완성 |
| ✅ 완료 | EasyOCR 연동 | 완성 |
| ✅ 완료 | STR(Deep Text Recognition) 연동 | 완성 |
| ✅ 완료 | 이미지 전처리 연결 (코드 보유 중) | 연결 필요 |
| ✅ 완료 | PDF 전처리 연결 (코드 보유 중) | 연결 필요 |
| ✅ 완료 | Celery + Redis 작업 큐 | 구현 필요 |
| ⬜ 예정 | LLM 기반 필드 추출 (1단계) | 구현 필요 |
| ⬜ 예정 | LayoutLMv3 파인튜닝 (2단계) | 학습 필요 |
| ⬜ 예정 | 결과 조회 API | 구현 필요 |

---

## 프로젝트 폴더 구조

```
document-project/
├── app/
│   ├── main.py                    # 서버 시작점
│   ├── core/
│   │   ├── config.py              # 전체 설정 (경로, DB 주소 등)
│   │   └── logging.py             # 로그 설정
│   ├── api/
│   │   └── v1/
│   │       └── file_api.py        # API 라우터 (엔드포인트 정의)
│   ├── models/
│   │   ├── request_models.py      # 요청 데이터 형식 정의
│   │   ├── response_models.py     # 응답 데이터 형식 정의
│   │   └── db_models.py           # DB 테이블 구조 정의
│   ├── services/
│   │   ├── file_service.py        # 파일 저장/분기 처리
│   │   ├── img_preprocess_service.py   # 이미지 전처리
│   │   ├── pdf_preprocess_service.py   # PDF 전처리
│   │   ├── ocr_service.py         # OCR (STR 모델)
│   │   ├── ocr_service_easyocr.py # OCR (EasyOCR)
│   │   ├── extraction_service.py  # 필드 추출 (ML) ← 핵심 구현 예정
│   │   └── db_service.py          # DB 저장
│   ├── repositories/
│   │   └── document_repository.py # DB 쿼리 모음
│   ├── ml/
│   │   ├── EAST-master/           # 텍스트 영역 검출 모델
│   │   └── easyocr_predictor.py   # EasyOCR 래퍼
│   ├── storage/
│   │   ├── uploads/               # 업로드된 원본 파일 저장
│   │   └── processed/             # 전처리된 파일 저장
│   ├── tests/
│   │   ├── test_file_upload.py
│   │   └── test_services/
│   │       ├── test_file_services.py
│   │       └── test_ocr_services.py
│   └── utils/
│       └── file_utils.py          # 파일 이름 처리 유틸
├── requirements.txt               # 설치할 패키지 목록
├── run.sh                         # 서버 실행 스크립트
└── README.md                      # 지금 읽고 있는 파일
```

---

## 시작하기 전에 설치해야 하는 것들

### 1. Python 3.8 이상
```bash
python --version   # 3.8 이상인지 확인
```

### 2. Redis (작업 큐용)


**Windows (WSL 환경):**
```bash
sudo apt update
sudo apt install redis-server
sudo service redis-server start

# 잘 켜졌는지 확인 (PONG이 나오면 성공)
redis-cli ping
```

**Mac:**
```bash
brew install redis
brew services start redis
redis-cli ping
```

### 3. Python 패키지 설치
```bash
# 가상환경 만들기 (선택사항이지만 강력 권장)
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows

# 패키지 설치
pip install -r requirements.txt

# Celery + Redis 연동 패키지 추가 설치 (아직 requirements에 없음)
pip install celery redis anthropic
```

---

## 환경 변수 설정 (.env 파일)

프로젝트 루트에 `.env` 파일을 만들고 아래 내용을 채워야 합니다.

```
# Redis 주소 (로컬에서 실행하면 아래 그대로 사용 가능)
REDIS_URL=redis://localhost:6379/0

# Claude API 키 (필드 추출 1단계에서 사용)
# https://console.anthropic.com 에서 발급
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx

# DB 연결 주소 (MySQL 사용 시)
# DB 저장 기능을 쓰지 않으면 비워도 됨
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/document_db(예시)
```

> `.env` 파일은 절대 git에 올리면 안 됩니다. `.gitignore`에 추가되어 있는지 꼭 확인하세요.

---

## 서버 실행 방법

**스크립트 사용 시**
```bash
bash run.sh
```

터미널을 **3개** 열어야 합니다.

**터미널 1: FastAPI 서버**
```bash
cd document-project
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**터미널 2: Celery Worker (비동기 작업 처리기)**
```bash
cd document-project
celery -A app.worker worker --loglevel=info
```

**터미널 3: Celery Flower (큐 상태 모니터링 - 선택사항)**
```bash
cd document-project
celery -A app.worker flower --port=5555
# 브라우저에서 http://localhost:5555 접속하면 큐 현황 볼 수 있음
```



---

## API 사용 방법

### 파일 처리 요청 (업로드 + 분석 시작)
```bash
curl -X POST http://localhost:8000/api/v1/documents/process \
  -F "file=@영수증.jpg"
```

응답 예시:
```json
{
  "job_id": "abc123",
  "status": "queued",
  "message": "접수됐습니다. job_id로 결과를 조회하세요."
}
```

### 결과 조회
```bash
curl http://localhost:8000/api/v1/documents/abc123/result
```

처리 중일 때:
```json
{ "status": "processing" }
```

완료됐을 때:
```json
{
  "job_id": "abc123",
  "status": "done",
  "document_type": "receipt",
  "fields": {
    "store_name":   { "value": "GS25 강남점",  "confidence": 0.95 },
    "date":         { "value": "2024-01-15",   "confidence": 0.98 },
    "total_amount": { "value": "15000",         "confidence": 0.91 },
    "items": [
      { "name": "삼각김밥", "price": "1200" }
    ]
  },
  "ocr_raw": "GS25 강남점\n2024-01-15\n삼각김밥 1200...",
  "processed_at": "2024-01-15T10:30:00"
}
```

### 서버 상태 확인
```bash
curl http://localhost:8000/health
```

---

## AI 필드 추출 - 2단계 계획

### 1단계: Claude API 사용 (지금 바로 가능)

OCR로 뽑은 텍스트를 Claude에게 보내서 구조화된 JSON으로 받습니다.
`app/services/extraction_service.py`의 `extract_fields` 함수 안에 구현합니다.

- 별도 학습 데이터 불필요
- 바로 동작 가능
- 추후 학습 데이터로도 활용 가능 (Claude 결과를 정답으로 사용)

### 2단계: LayoutLMv3 파인튜닝 (직접 학습)

Microsoft가 만든 문서 이해 AI 모델입니다.
텍스트 내용뿐 아니라 **텍스트가 이미지 어디에 있는지(좌표)** 도 함께 학습합니다.

```
예시: "10,000"이라는 숫자가
  → 영수증 오른쪽 하단에 있으면 → "총액"
  → 가운데에 있으면             → "단가"
```

이를 위해 필요한 것:
1. 라벨링된 영수증 데이터 (최소 200~500장 권장)
2. HuggingFace 계정 + 모델 허브 사용법
3. GPU 환경 (Google Colab 무료 GPU로도 시작 가능)

---

## 직접 해야 하는 설정 목록

아래 항목들은 자동으로 되지 않으니 직접 설정해야 합니다.

### 필수
- [ ] Redis 설치 및 실행 (위 설치 방법 참고)
- [ ] `.env` 파일 생성 및 `ANTHROPIC_API_KEY` 입력
- [ ] `celery`, `redis`, `anthropic` 패키지 pip 설치
- [ ] 이미지 전처리 코드를 `app/services/img_preprocess_service.py`에 연결
- [ ] PDF 전처리 코드를 `app/services/pdf_preprocess_service.py`에 연결

### ML 학습 시 (2단계)
- [ ] 영수증 이미지 수집 (최소 200장 이상)
- [ ] LabelStudio 설치 + 필드 라벨링 작업
- [ ] Google Colab 또는 GPU 서버에서 LayoutLMv3 파인튜닝 실행
- [ ] 학습된 모델 가중치를 `app/ml/` 폴더에 저장
- [ ] `extraction_service.py`를 Claude API → 학습 모델로 교체

---

## 공부해야 할 기술들

### 이미 쓰고 있는 것 (기본 이해 있으면 됨)
| 기술 | 역할 | 공식 문서 |
|------|------|-----------|
| FastAPI | API 서버 프레임워크 | https://fastapi.tiangolo.com |
| EasyOCR | 이미지에서 글자 읽기 | https://github.com/JaidedAI/EasyOCR |

### 이번에 새로 배울 것
| 기술 | 역할 | 공부 방법 |
|------|------|-----------|
| Celery | 비동기 작업 큐 | 공식 문서 + "Celery FastAPI 예제" 검색 |
| Redis | 빠른 임시 저장소 / 큐 브로커 | "Redis 입문" 유튜브 |
| Anthropic API | Claude로 텍스트 구조화 | https://docs.anthropic.com |
| HuggingFace Transformers | AI 모델 학습/사용 | https://huggingface.co/docs |
| LayoutLMv3 | 문서 이해 AI 모델 | HuggingFace 모델 카드 참고 |

### 선택적으로 배울 것
| 기술 | 역할 |
|------|------|
| Docker | 서버 + Redis + Worker를 한 번에 실행 |
| MySQL | 결과 영구 저장 (현재 DB 저장은 stub 상태) |
| pytest | 자동화 테스트 작성 |

---

## 추천 구현 순서

```
1단계  Redis 설치 + Celery 연동
       목표: 파일 업로드 시 job_id 반환, 비동기로 처리되는 구조 만들기

2단계  전처리 서비스 연결
       목표: 이미지/PDF 전처리 코드를 각 service 파일에 붙이기

3단계  Claude API로 extraction_service 완성
       목표: OCR 결과 텍스트 → Claude → JSON 필드 추출 동작

4단계  결과 조회 API 추가
       목표: GET /api/v1/documents/{job_id}/result 엔드포인트 구현

5단계  영수증 데이터 수집 + 라벨링
       목표: 200장 이상 수집, LabelStudio로 필드 라벨 작업

6단계  LayoutLMv3 파인튜닝
       목표: Google Colab에서 학습 → 모델 저장 → 서버에 연결

7단계  Claude 추출 → 학습 모델로 교체
       목표: extraction_service.py에서 모델 직접 추론으로 전환
```

---

## 자주 발생하는 문제

**Q: `redis-cli ping` 했는데 응답이 없어요**
```bash
sudo service redis-server start   # Redis 먼저 실행
redis-cli ping                    # 다시 시도
```

**Q: Celery worker가 바로 죽어요**
- `.env` 파일에 `REDIS_URL`이 올바르게 입력됐는지 확인
- Redis가 실행 중인지 확인 (`redis-cli ping`)

**Q: OCR 결과가 이상하게 나와요**
- 이미지 해상도가 너무 낮으면 OCR 정확도가 떨어집니다
- 전처리(밝기 조정, 기울기 보정)가 적용됐는지 확인하세요

**Q: LayoutLMv3 학습에 GPU가 없어요**
- Google Colab 무료 버전(T4 GPU)으로 시작 가능합니다
- 데이터가 적으면 CPU로도 가능하지만 매우 느립니다

**Q: OCR실행중에 종료가 안되요**
- Celery 사용과 EasyOCR Pytorch가 충돌되면서 데드락(deadlock)이 발생했습니다.
- Celery를 실행할때 단일로 실행하도록 처리해줬어요 
```bash
celery -A app.worker worker --loglevel=info --pool=solo 
```
---

## 기술 스택 요약

```
언어:      Python 3.8
API 서버:  FastAPI + Uvicorn
OCR:       EasyOCR
작업 큐:   Celery + Redis
AI 추출:   Claude API (1단계) → LayoutLMv3 파인튜닝 (2단계)(진행중)
DB:        MySQL (선택)
테스트:    pytest
```
