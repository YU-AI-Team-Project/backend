# SP500 과거 데이터 기반 주식 분석 보고서 생성기 (테스트 버전)

이 도구는 2024년 이전의 과거 데이터를 사용하여 SP500 종목들의 종합적인 주식 분석을 수행하고 CSV 파일로 저장합니다.

## 📁 파일 구성

- `historical_report_generator.py`: 메인 분석기 클래스
- `config_historical.py`: 설정 관리 파일 (SP500 티커 자동 로드)
- `run_historical_reports.py`: 실행 스크립트
- `requirements_historical.txt`: 필요한 라이브러리 목록

## 🚀 설치 및 설정

### 1. 의존성 설치
```bash
pip install -r requirements_historical.txt
```

### 2. 환경변수 설정
`.env` 파일을 생성하고 다음 내용을 추가하세요:

```bash
# OpenAI API 키 (필수)
OPENAI_API_KEY=your_openai_api_key_here

# MySQL 연결 정보 (주식/재무 데이터)
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_mysql_db

# PostgreSQL 뉴스 DB 연결 정보
NEWS_DB_USER=your_pg_username
NEWS_DB_PASSWORD=your_pg_password
NEWS_DB_HOST=localhost
NEWS_DB_PORT=5432
NEWS_DB_NAME=your_news_db

# 또는 직접 DATABASE_URL 설정 (PostgreSQL 대체 방식)
# DATABASE_URL=postgresql://username:password@localhost:5432/dbname

# 선택적 설정
OUTPUT_DIR=data/historical_reports
NEWS_LIMIT=50
MAX_TOKENS=12000
```

### 3. 설정 유효성 검사
```bash
python run_historical_reports.py --validate
```

## 💼 사용법

### 기본 실행 (샘플 종목들)
```bash
python run_historical_reports.py
```

### 단일 종목 분석
```bash
python run_historical_reports.py --single AAPL
```

### 여러 종목 분석
```bash
python run_historical_reports.py --stock-codes AAPL MSFT GOOGL
```

### 샘플 종목들로 빠른 테스트 (10개)
```bash
python run_historical_reports.py --sample
```

### 전체 SP500 종목 일괄 처리
```bash
python run_historical_reports.py --batch
```

### 출력 디렉토리 지정
```bash
python run_historical_reports.py --output-dir /path/to/output --sample
```

## 📊 출력 파일

### 개별 분석 CSV
각 종목별로 다음 형태의 CSV 파일이 생성됩니다:
- 파일명: `historical_report_{종목코드}_{타임스탬프}.csv`
- 컬럼:
  - `stock_code`: 종목 코드
  - `analysis_type`: 분석 유형 (historical_analysis)
  - `data_period`: 데이터 기간 (pre_2024)
  - `report`: 생성된 종합 분석 보고서 전문
  - `news_count`: 사용된 뉴스 기사 수
  - `financial_periods`: 분석된 재무 기간 수
  - `generated_at`: 생성 시각
  - `success`: 성공 여부

### 요약 CSV (일괄 처리시)
- 파일명: `historical_reports_summary_{타임스탬프}.csv`
- 모든 종목의 처리 결과 요약

## 🎯 주요 기능

### 1. 2024년 이전 데이터 필터링
- 뉴스 데이터: `published_at < 2024-01-01`
- 재무 데이터: `report_period < 2024-01-01`

### 2. 종합적인 데이터 수집
- **뉴스 데이터**: 종목 관련 과거 뉴스 기사 (50개)
- **재무제표**: 전체 재무 지표 (8개 기간)
- **기업정보**: 전체 사업분야, 업종 정보

### 3. AI 기반 종합 분석
GPT-4를 활용한 상세한 역사적 분석:
- 📊 기업 개요 (과거 기준)
- 📈 재무 성과 통계 (2024년 이전)
- 📰 과거 주요 이벤트 및 뉴스
- 💡 간단한 통계적 인사이트

### 4. CSV 저장
- 개별 종목 분석 CSV
- 일괄 처리 요약 CSV
- UTF-8 인코딩으로 한글 지원

## ⚙️ 설정 커스터마이징

`config_historical.py`에서 다음 설정을 변경할 수 있습니다:

```python
DEFAULT_CONFIG = {
    "CUTOFF_DATE": date(2024, 1, 1),        # 데이터 기준일
    "OUTPUT_DIR": "data/historical_reports", # 출력 디렉토리
    "NEWS_LIMIT": 50,                       # 뉴스 검색 개수
    "FINANCIAL_STATEMENTS_LIMIT": 8,        # 재무제표 기간 수
    "MAX_TOKENS": 12000,                    # GPT 최대 토큰
    "TEMPERATURE": 0.7,                     # GPT 창의성 설정
    # ...
}
```

## 🔍 SP500 종목 자동 로드

`yfinance_PriceCollector/sp500_tickers.csv` 파일에서 SP500 종목들을 자동으로 로드합니다:

### 샘플 종목들 (빠른 테스트용):
- AAPL (Apple)
- MSFT (Microsoft)
- GOOGL (Alphabet)
- AMZN (Amazon)
- TSLA (Tesla)
- META (Meta)
- NVDA (NVIDIA)
- JPM (JPMorgan Chase)
- JNJ (Johnson & Johnson)
- V (Visa)

### 전체 SP500:
- 총 500여개 종목 자동 로드
- CSV 파일 업데이트시 자동 반영

## ⚠️ 주의사항

1. **OpenAI API 키**: 반드시 유효한 OpenAI API 키가 필요합니다.
2. **데이터베이스 연결**: MySQL과 PostgreSQL 두 DB의 연결이 필요합니다.
3. **과거 데이터**: 2024년 이전 데이터만 사용하므로 최신 정보는 포함되지 않습니다.
4. **시장지표 제외**: 시장지표 데이터는 포함되지 않습니다.
5. **API 비용**: OpenAI API 사용에 따른 비용이 발생할 수 있습니다.

## 🛠️ 문제 해결

### 1. 설정 오류
```bash
python run_historical_reports.py --validate
```

### 2. 데이터베이스 연결 오류
- `DATABASE_URL` 환경변수 확인
- 데이터베이스 서버 상태 확인
- 네트워크 연결 상태 확인

### 3. OpenAI API 오류
- `OPENAI_API_KEY` 환경변수 확인
- API 키 유효성 확인
- API 사용량 제한 확인

### 4. SP500 티커 로드 오류
- `yfinance_PriceCollector/sp500_tickers.csv` 파일 존재 확인
- 파일 권한 및 경로 확인

## 📈 결과 활용

생성된 CSV 파일은 다음과 같이 활용할 수 있습니다:

```python
import pandas as pd

# 개별 분석 읽기
df = pd.read_csv('historical_report_AAPL_20241201_120000.csv')
print(df['report'].iloc[0])  # 종합 분석 내용

# 요약 결과 읽기
summary_df = pd.read_csv('historical_reports_summary_20241201_120000.csv')
print(summary_df.groupby('success').size())  # 성공/실패 통계
```

## 📊 분석 결과 예시

종합 분석 보고서는 다음과 같은 형태로 제공됩니다:

- **기업 개요**: 과거 시점 기준 사업 분야 및 위치
- **재무 성과**: 매출, 영업이익, 순이익, ROE, 부채비율 등 전체 지표
- **과거 이벤트**: 주요 뉴스와 시장 반응 분석
- **역사적 트렌드**: 성장 패턴, 수익성, 재무 안정성 분석

---

이 도구를 통해 2024년 이전의 과거 데이터를 기반으로 한 SP500 종목들의 종합적인 역사적 분석을 효율적으로 수행할 수 있습니다. 