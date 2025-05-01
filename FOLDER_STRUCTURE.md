# 📁 프로젝트 폴더 구조 및 역할 설명

이 문서는 `stock-portfolio-app` 프로젝트의 3-모듈 구조에 대해 설명합니다.

---

## 1. `backend/` – 웹 API 서버

FastAPI 기반 웹 서버로 사용자 요청을 처리하고, DB 및 AI 모듈과 연동합니다.

**포함 구성:**

- `main.py`  
  → FastAPI 앱 실행 및 라우터 등록

- `api/v1/endpoints/portfolio.py`  
  → 포트폴리오, 종목 관련 API 정의

- `api/v1/schemas/portfolio.py`  
  → 요청/응답 Pydantic 모델 정의

- `db/models/*.py`, `db/session.py`  
  → SQLModel 기반 ORM, 세션 관리

- `services/portfolio_service.py`  
  → DB 및 외부 API 호출 처리

- `core/config.py`  
  → `.env` 파일 기반 설정 불러오기

- `core/security.py`  
  → JWT 인증 및 보안 로직

- `tests/`  
  → API 및 서비스 테스트 (pytest)

---

## 2. `data_pipelines/` – ETL & 스케줄러

실시간 금융 데이터, 뉴스 등을 수집·정제하여 RDB 및 벡터 DB에 저장합니다. APScheduler 또는 Celery 기반 백엔드 파이프라인입니다.

**포함 구성:**

- `scheduler/schedule.py`  
  → 작업 스케줄 등록

- `workers/fetch_market_data.py`  
  → Alpha Vantage 또는 뉴스 크롤링

- `workers/rebalance_batch.py`  
  → 분기별 포트폴리오 자동 리밸런싱

- `helpers/db_writer.py`  
  → 수집 데이터 DB 적재 처리

- `utils/logger.py`, `utils/retry_utils.py`  
  → 로그 기록, 실패 재시도 처리

- `config.py`  
  → 환경 변수 및 설정 로드

- `tests/`  
  → mock 기반 단위 테스트

**입력:** 외부 API, 뉴스 사이트  
**출력:** mysql 저장 (→ backend에서 조회), 또는 벡터 DB로 전달 (→ ai_components)

---

## 3. `ai_components/` – AI 분석 & 추천

RAG, GPT Agent, 추천 알고리즘 등 AI 관련 로직을 담당합니다.

**포함 구성:**

- `services/rag_engine.py`  
  → RAG 파이프라인 구성 (검색 → 생성)

- `vector_store/client.py`  
  → PGVector 또는 Chroma 연결

- `vector_store/embedder.py`  
  → 텍스트 → 임베딩 벡터 생성

- `services/recommendation.py`  
  → 종목 추천 및 점수 계산

- `services/optimization.py`  
  → 포트폴리오 최적화 알고리즘 (예: MPT)

- `api_interface/`  
  → 외부에서 이 모듈을 호출할 REST 클라이언트 등

- `tests/`  
  → AI 분석 및 임베딩 관련 테스트

**입력:** 뉴스 본문, 재무정보, 사용자 질의  
**출력:** 자연어 보고서, 종목 추천, 포트폴리오 조정안

---

## ✅ 요약

이 구조는 모듈화·병렬 개발·배포 분리를 고려하여 구성되었습니다.  
- 로컬에서는 Docker Compose로 전체 실행 가능  
- AWS 등 클라우드 환경에서는 각 모듈을 독립적으로 배포 가능
