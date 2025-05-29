"""
과거 데이터 기반 간략 통계 분석기 설정 파일
"""
import os
import csv
import random
from datetime import date

def load_sp500_tickers():
    """SP500 티커 목록을 CSV 파일에서 로드"""
    try:
        # yfinance_PriceCollector 폴더의 sp500_tickers.csv 파일 경로
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, "..", "yfinance_PriceCollector", "sp500_tickers.csv")
        
        tickers = []
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                if row and row[0].strip():  # 빈 행 제외
                    tickers.append(row[0].strip())
        
        print(f"SP500 티커 {len(tickers)}개 로드 완료")
        return tickers
        
    except Exception as e:
        print(f"SP500 티커 로드 실패: {e}")
        # 로드 실패시 기본 한국 주식 코드 반환
        return [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "035420",  # NAVER
            "005380",  # 현대차
            "012330",  # 현대모비스
        ]

def get_random_sp500_tickers(count: int = 50):
    """SP500 티커에서 랜덤하게 선택"""
    all_tickers = load_sp500_tickers()
    if count >= len(all_tickers):
        print(f"요청된 개수({count})가 전체 티커 수({len(all_tickers)})보다 많습니다. 전체를 반환합니다.")
        return all_tickers
    
    random_tickers = random.sample(all_tickers, count)
    print(f"SP500에서 랜덤 {count}개 선택: {random_tickers[:5]}... (총 {len(random_tickers)}개)")
    return random_tickers

# 기본 설정
DEFAULT_CONFIG = {
    # 데이터 기준일 (2024년 이전 데이터만 사용)
    "CUTOFF_DATE": date(2024, 1, 1),
    
    # 출력 디렉토리 (현재 파일과 같은 위치)
    "OUTPUT_DIR": "./data/historical_reports",
    
    # 검색 설정
    "NEWS_LIMIT": 50,                    # 뉴스 개수 원래대로
    "FINANCIAL_STATEMENTS_LIMIT": 8,     # 재무제표 기간 원래대로
    
    # OpenAI 설정
    "EMBEDDING_MODEL": "text-embedding-3-small",
    "CHAT_MODEL": "gpt-4o",
    "MAX_TOKENS": 12000,                 # 원래 토큰 수로 복구
    "TEMPERATURE": 0.7,                  # 원래 temperature로 복구
    "TIMEOUT": 60.0,
    
    # CSV 설정
    "CSV_ENCODING": "utf-8",
    
    # SP500 티커들을 기본 종목 코드로 사용
    "DEFAULT_STOCK_CODES": load_sp500_tickers(),
}

def get_config():
    """설정값 반환"""
    config = DEFAULT_CONFIG.copy()
    
    # 환경변수로 설정 덮어쓰기
    if os.getenv("OUTPUT_DIR"):
        config["OUTPUT_DIR"] = os.getenv("OUTPUT_DIR")
    
    if os.getenv("NEWS_LIMIT"):
        config["NEWS_LIMIT"] = int(os.getenv("NEWS_LIMIT"))
    
    if os.getenv("MAX_TOKENS"):
        config["MAX_TOKENS"] = int(os.getenv("MAX_TOKENS"))
    
    return config

def get_database_url():
    """데이터베이스 URL 반환"""
    return os.getenv(
        "DATABASE_URL", 
        "postgresql://user:password@localhost:5432/dbname"
    )

def validate_config():
    """설정값 유효성 검사"""
    errors = []
    
    if not os.getenv("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
    
    # MySQL DB 환경변수 확인 (주식/재무 데이터)
    mysql_vars = ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]
    missing_mysql_vars = [var for var in mysql_vars if not os.getenv(var)]
    
    if missing_mysql_vars:
        errors.append(f"MySQL 연결 정보가 부족합니다: {missing_mysql_vars}")
    
    # PostgreSQL DB 환경변수 확인 (뉴스 데이터)
    pg_vars = ["NEWS_DB_USER", "NEWS_DB_PASSWORD", "NEWS_DB_HOST", "NEWS_DB_PORT", "NEWS_DB_NAME"]
    missing_pg_vars = [var for var in pg_vars if not os.getenv(var)]
    
    if missing_pg_vars and not os.getenv("DATABASE_URL"):
        errors.append(f"PostgreSQL 뉴스 DB 연결 정보가 부족합니다: {missing_pg_vars}")
        errors.append("또는 DATABASE_URL 환경변수를 설정해주세요.")
    
    return errors 