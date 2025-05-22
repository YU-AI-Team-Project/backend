import os
import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
import sys
from datetime import datetime
import time
import random
import numpy as np

# 상위 디렉토리를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결 설정
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# 데이터베이스 연결 생성
DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
engine = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_financial_data(ticker_symbol):
    """
    yfinance에서 재무 데이터 가져오기
    
    Args:
        ticker_symbol (str): 주식 티커 심볼
        
    Returns:
        tuple: 연간 및 분기별 재무 데이터
    """
    try:
        print(f"[INFO] {ticker_symbol}의 재무 데이터를 가져오는 중...")
        ticker = yf.Ticker(ticker_symbol)
        
        # API 요청 전 잠시 대기 (API 제한 방지)
        time.sleep(1)
        
        # 손익계산서 데이터 가져오기
        income_stmt_annual = ticker.income_stmt
        
        # API 요청 사이에 대기 시간 추가
        time.sleep(1)
        
        income_stmt_quarterly = ticker.quarterly_income_stmt
        
        # API 요청 사이에 대기 시간 추가
        time.sleep(1)
        
        # 대차대조표 데이터 가져오기
        balance_sheet_annual = ticker.balance_sheet
        
        # API 요청 사이에 대기 시간 추가
        time.sleep(1)
        
        balance_sheet_quarterly = ticker.quarterly_balance_sheet
        
        return {
            'annual': {
                'income_stmt': income_stmt_annual,
                'balance_sheet': balance_sheet_annual
            },
            'quarterly': {
                'income_stmt': income_stmt_quarterly,
                'balance_sheet': balance_sheet_quarterly
            }
        }
    except Exception as e:
        print(f"[ERROR] {ticker_symbol}의 재무 데이터를 가져오는 중 오류 발생: {e}")
        return None

def process_financial_data(ticker_symbol, financial_data):
    """
    yfinance에서 가져온 재무 데이터를 데이터베이스에 필요한 형식으로 처리
    
    Args:
        ticker_symbol (str): 주식 티커 심볼
        financial_data (dict): yfinance에서 가져온 재무 데이터
        
    Returns:
        list: 처리된 재무 데이터 딕셔너리 리스트
    """
    result = []
    
    for period_type, data in financial_data.items():
        income_stmt = data['income_stmt']
        balance_sheet = data['balance_sheet']
        
        # NaN 값이 있는지 확인하기 위해 데이터프레임이 비어있는지 확인
        if income_stmt is None or balance_sheet is None or income_stmt.empty or balance_sheet.empty:
            print(f"[WARNING] {ticker_symbol}의 {period_type} 재무제표에 데이터가 없습니다.")
            continue
            
        # 손익계산서와 대차대조표 사이의 공통 날짜 가져오기
        income_dates = income_stmt.columns if hasattr(income_stmt, 'columns') else []
        balance_dates = balance_sheet.columns if hasattr(balance_sheet, 'columns') else []
        common_dates = list(set(income_dates).intersection(set(balance_dates)))
        
        for date in common_dates:
            period_date = date.strftime('%Y-%m')
            
            # 재무 데이터 추출
            try:
                # 주요 재무 지표 추출
                revenue = income_stmt.loc['Total Revenue', date] if 'Total Revenue' in income_stmt.index else None
                operating_income = income_stmt.loc['Operating Income', date] if 'Operating Income' in income_stmt.index else None
                net_income = income_stmt.loc['Net Income', date] if 'Net Income' in income_stmt.index else None
                
                assets = balance_sheet.loc['Total Assets', date] if 'Total Assets' in balance_sheet.index else None
                liabilities = balance_sheet.loc['Total Liabilities', date] if 'Total Liabilities' in balance_sheet.index else None
                equity = balance_sheet.loc['Total Stockholder Equity', date] if 'Total Stockholder Equity' in balance_sheet.index else None
                
                # 모든 주요 지표가 NaN인지 확인
                main_metrics = [revenue, operating_income, net_income, assets, liabilities, equity]
                if all(pd.isna(metric) for metric in main_metrics if metric is not None):
                    print(f"[WARNING] {ticker_symbol}의 {period_date} 데이터가 모두 NaN입니다. 건너뜁니다.")
                    continue
                
                # 수익이 없거나 NaN인 경우 건너뛰기 (핵심 지표이므로)
                if revenue is None or pd.isna(revenue):
                    print(f"[WARNING] {ticker_symbol}의 {period_date} 수익 데이터가 없습니다. 건너뜁니다.")
                    continue
                    
                # NaN 값을 None으로 변환 (SQL에서 NULL로 저장하기 위함)
                revenue = None if pd.isna(revenue) else revenue
                operating_income = None if pd.isna(operating_income) else operating_income
                net_income = None if pd.isna(net_income) else net_income
                assets = None if pd.isna(assets) else assets
                liabilities = None if pd.isna(liabilities) else liabilities
                equity = None if pd.isna(equity) else equity
                
                # 재무제표 레코드 생성
                financial_statement = {
                    'stock_code': ticker_symbol,
                    'report_period': period_date,
                    'report_type': period_type,
                    'revenue': revenue,
                    'operating_income': operating_income,
                    'net_income': net_income,
                    'assets': assets,
                    'liabilities': liabilities,
                    'equity': equity
                }
                
                result.append(financial_statement)
                print(f"[INFO] {ticker_symbol}의 {period_date} {period_type} 재무제표 처리 완료")
            except Exception as e:
                print(f"[ERROR] {ticker_symbol}의 {period_date} 기간 재무 데이터 처리 중 오류 발생: {e}")
                continue
    
    return result

def save_to_database(financial_statements):
    """
    재무제표 데이터를 데이터베이스에 저장
    
    Args:
        financial_statements (list): 재무제표 딕셔너리 리스트
    """
    session = SessionLocal()
    try:
        for statement in financial_statements:
            # 이 재무제표가 이미 존재하는지 확인
            query = text("""
                SELECT id FROM financial_statements 
                WHERE stock_code = :stock_code 
                AND report_period = :report_period 
                AND report_type = :report_type
            """)
            
            result = session.execute(
                query,
                {
                    'stock_code': statement['stock_code'],
                    'report_period': statement['report_period'],
                    'report_type': statement['report_type']
                }
            ).fetchone()
            
            if result:
                # 기존 레코드 업데이트
                update_query = text("""
                    UPDATE financial_statements 
                    SET revenue = :revenue,
                        operating_income = :operating_income,
                        net_income = :net_income,
                        assets = :assets,
                        liabilities = :liabilities,
                        equity = :equity
                    WHERE stock_code = :stock_code 
                    AND report_period = :report_period 
                    AND report_type = :report_type
                """)
                
                session.execute(update_query, statement)
                print(f"[INFO] {statement['stock_code']}의 재무제표 업데이트 완료 ({statement['report_period']}, {statement['report_type']})")
            else:
                # 새 레코드 삽입
                insert_query = text("""
                    INSERT INTO financial_statements 
                    (stock_code, report_period, report_type, revenue, operating_income, net_income, assets, liabilities, equity)
                    VALUES 
                    (:stock_code, :report_period, :report_type, :revenue, :operating_income, :net_income, :assets, :liabilities, :equity)
                """)
                
                session.execute(insert_query, statement)
                print(f"[INFO] {statement['stock_code']}의 재무제표 추가 완료 ({statement['report_period']}, {statement['report_type']})")
        
        session.commit()
        print("[INFO] 재무 데이터가 성공적으로 데이터베이스에 저장되었습니다.")
    except Exception as e:
        session.rollback()
        print(f"[ERROR] 재무 데이터를 데이터베이스에 저장하는 중 오류 발생: {e}")
    finally:
        session.close()

def get_sp500_tickers():
    """
    sp500_tickers.csv 파일에서 S&P 500 주식 티커 리스트 가져오기
    
    Returns:
        list: 주식 티커 리스트
    """
    try:
        # 현재 파일과 같은 디렉토리에 있는 sp500_tickers.csv 파일 경로
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sp500_tickers.csv')
        
        # 각 줄이 티커 심볼인 CSV 파일 읽기
        with open(csv_path, 'r') as f:
            tickers = [line.strip() for line in f if line.strip()]
        
        print(f"[INFO] CSV 파일에서 {len(tickers)}개의 티커를 가져왔습니다.")
        return tickers
    except Exception as e:
        print(f"[ERROR] S&P 500 티커를 CSV 파일에서 가져오는 중 오류 발생: {e}")
        return []

def main():
    """재무 데이터를 가져오고 처리하는 메인 함수"""
    # S&P 500 티커 가져오기
    stock_tickers = get_sp500_tickers()
    
    if not stock_tickers:
        print("[WARNING] CSV 파일에서 티커를 찾을 수 없습니다.")
        return
    
    print(f"[INFO] 처리할 주식 티커 {len(stock_tickers)}개를 찾았습니다.")
    
    # 모든 주식 티커에 대해 처리
    for ticker in stock_tickers:
        try:
            # 재무 데이터 가져오기
            financial_data = get_financial_data(ticker)
            
            if not financial_data:
                print(f"[WARNING] {ticker}에 대한 재무 데이터를 찾을 수 없습니다.")
                continue
            
            # 재무 데이터 처리
            financial_statements = process_financial_data(ticker, financial_data)
            
            if financial_statements:
                # 데이터베이스에 저장
                save_to_database(financial_statements)
                print(f"[INFO] {ticker}의 재무 데이터 처리가 성공적으로 완료되었습니다.")
            else:
                print(f"[WARNING] {ticker}에 대한 처리 가능한 재무제표를 찾을 수 없습니다.")
                
            # 다음 티커 처리 전 랜덤한 시간(2-5초) 대기하여 API 제한 방지
            wait_time = 2 + random.random() * 3
            print(f"[INFO] 다음 티커 처리 전 {wait_time:.2f}초 대기 중...")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"[ERROR] {ticker} 처리 중 오류 발생: {e}")
            # 오류 발생 시 좀 더 오래 대기
            time.sleep(5)

if __name__ == "__main__":
    print("[INFO] 재무 데이터 수집을 시작합니다...")
    main()
    print("[INFO] 재무 데이터 수집이 완료되었습니다.") 