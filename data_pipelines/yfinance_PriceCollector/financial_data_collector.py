import os
import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
import sys
from datetime import datetime, date
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

def safe_float(value, default=None):
    """안전하게 float로 변환"""
    try:
        if pd.isna(value) or value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=None):
    """안전하게 int로 변환"""
    try:
        if pd.isna(value) or value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

def get_comprehensive_financial_data(ticker_symbol):
    """
    yfinance에서 포괄적인 재무 데이터 가져오기
    
    Args:
        ticker_symbol (str): 주식 티커 심볼
        
    Returns:
        dict: 모든 재무 데이터
    """
    try:
        print(f"[INFO] {ticker_symbol}의 포괄적인 재무 데이터를 가져오는 중...")
        ticker = yf.Ticker(ticker_symbol)
        
        # API 요청 전 잠시 대기 (API 제한 방지)
        time.sleep(1)
        
        # 기본 회사 정보
        info = ticker.info
        time.sleep(1)
        
        # 손익계산서 데이터 가져오기
        income_stmt_annual = ticker.income_stmt
        time.sleep(1)
        
        income_stmt_quarterly = ticker.quarterly_income_stmt
        time.sleep(1)
        
        # 대차대조표 데이터 가져오기
        balance_sheet_annual = ticker.balance_sheet
        time.sleep(1)
        
        balance_sheet_quarterly = ticker.quarterly_balance_sheet
        time.sleep(1)
        
        # 현금흐름표 데이터 가져오기
        cashflow_annual = ticker.cashflow
        time.sleep(1)
        
        cashflow_quarterly = ticker.quarterly_cashflow
        time.sleep(1)
        
        # 최근 가격 데이터 가져오기
        history = ticker.history(period="5d")
        
        return {
            'info': info,
            'annual': {
                'income_stmt': income_stmt_annual,
                'balance_sheet': balance_sheet_annual,
                'cashflow': cashflow_annual
            },
            'quarterly': {
                'income_stmt': income_stmt_quarterly,
                'balance_sheet': balance_sheet_quarterly,
                'cashflow': cashflow_quarterly
            },
            'history': history
        }
    except Exception as e:
        print(f"[ERROR] {ticker_symbol}의 재무 데이터를 가져오는 중 오류 발생: {e}")
        return None

def save_stock_info(ticker_symbol, info_data):
    """
    stocks 테이블에 회사 기본 정보 저장
    """
    session = SessionLocal()
    try:
        # 기본 회사 정보 추출
        company_name = info_data.get('longName', info_data.get('shortName', ticker_symbol))
        industry = info_data.get('industry', None)
        sector = info_data.get('sector', None)
        business_summary = info_data.get('longBusinessSummary', None)
        financial_info = f"Market Cap: {info_data.get('marketCap', 'N/A')}, Employees: {info_data.get('fullTimeEmployees', 'N/A')}"
        report_url = info_data.get('website', None)
        
        # 기존 레코드 확인
        check_query = text("SELECT code FROM stocks WHERE code = :code")
        result = session.execute(check_query, {'code': ticker_symbol}).fetchone()
        
        if result:
            # 업데이트
            update_query = text("""
                UPDATE stocks 
                SET company_name = :company_name,
                    financial_info = :financial_info,
                    report_url = :report_url,
                    industry = :industry,
                    sector = :sector,
                    business_summary = :business_summary
                WHERE code = :code
            """)
            
            session.execute(update_query, {
                'code': ticker_symbol,
                'company_name': company_name,
                'financial_info': financial_info,
                'report_url': report_url,
                'industry': industry,
                'sector': sector,
                'business_summary': business_summary
            })
            print(f"[INFO] {ticker_symbol}의 주식 정보 업데이트 완료")
        else:
            # 삽입
            insert_query = text("""
                INSERT INTO stocks (code, company_name, financial_info, report_url, industry, sector, business_summary)
                VALUES (:code, :company_name, :financial_info, :report_url, :industry, :sector, :business_summary)
            """)
            
            session.execute(insert_query, {
                'code': ticker_symbol,
                'company_name': company_name,
                'financial_info': financial_info,
                'report_url': report_url,
                'industry': industry,
                'sector': sector,
                'business_summary': business_summary
            })
            print(f"[INFO] {ticker_symbol}의 주식 정보 추가 완료")
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[ERROR] {ticker_symbol}의 주식 정보 저장 중 오류 발생: {e}")
    finally:
        session.close()

def get_financial_metrics_from_info(info_data):
    """
    yfinance info에서 이미 계산된 재무 지표들을 가져오기
    """
    return {
        # 이미 계산된 재무 지표들
        'gross_profits': safe_int(info_data.get('grossProfits')),
        'ebitda': safe_int(info_data.get('ebitda')),
        'operating_cashflow': safe_int(info_data.get('operatingCashflow')),
        'free_cashflow': safe_int(info_data.get('freeCashflow')),
        'revenue_per_share': safe_float(info_data.get('revenuePerShare')),
        'gross_margins': safe_float(info_data.get('grossMargins')),
        'ebitda_margins': safe_float(info_data.get('ebitdaMargins')),
        'operating_margins': safe_float(info_data.get('operatingMargins')),
        'return_on_assets': safe_float(info_data.get('returnOnAssets')),
        'return_on_equity': safe_float(info_data.get('returnOnEquity')),
        'debt_to_equity': safe_float(info_data.get('debtToEquity')),
        'quick_ratio': safe_float(info_data.get('quickRatio')),
        'current_ratio': safe_float(info_data.get('currentRatio')),
        'earnings_growth': safe_float(info_data.get('earningsGrowth')),
        'revenue_growth': safe_float(info_data.get('revenueGrowth')),
        'enterprise_value': safe_int(info_data.get('enterpriseValue')),
        'enterprise_to_revenue': safe_float(info_data.get('enterpriseToRevenue')),
        'enterprise_to_ebitda': safe_float(info_data.get('enterpriseToEbitda'))
    }

def process_comprehensive_financial_data(ticker_symbol, financial_data):
    """
    포괄적인 재무 데이터를 처리
    """
    result = []
    info_data = financial_data.get('info', {})
    
    # yfinance에서 이미 계산된 재무 지표들 가져오기
    financial_metrics = get_financial_metrics_from_info(info_data)
    
    for period_type, data in [('annual', financial_data['annual']), ('quarterly', financial_data['quarterly'])]:
        income_stmt = data['income_stmt']
        balance_sheet = data['balance_sheet']
        cashflow_stmt = data['cashflow']
        
        if income_stmt is None or balance_sheet is None or income_stmt.empty or balance_sheet.empty:
            print(f"[WARNING] {ticker_symbol}의 {period_type} 재무제표에 데이터가 없습니다.")
            continue
            
        # 공통 날짜 가져오기
        income_dates = income_stmt.columns if hasattr(income_stmt, 'columns') else []
        balance_dates = balance_sheet.columns if hasattr(balance_sheet, 'columns') else []
        common_dates = list(set(income_dates).intersection(set(balance_dates)))
        
        for date in common_dates:
            period_date = date.strftime('%Y-%m')
            
            try:
                # 기본 재무 데이터 추출
                revenue = income_stmt.loc['Total Revenue', date] if 'Total Revenue' in income_stmt.index else None
                operating_income = income_stmt.loc['Operating Income', date] if 'Operating Income' in income_stmt.index else None
                net_income = income_stmt.loc['Net Income', date] if 'Net Income' in income_stmt.index else None
                
                assets = balance_sheet.loc['Total Assets', date] if 'Total Assets' in balance_sheet.index else None
                liabilities = balance_sheet.loc['Total Liabilities', date] if 'Total Liabilities' in balance_sheet.index else None
                equity = balance_sheet.loc['Total Stockholder Equity', date] if 'Total Stockholder Equity' in balance_sheet.index else None
                
                # 수익이 없거나 NaN인 경우 건너뛰기
                if revenue is None or pd.isna(revenue):
                    print(f"[WARNING] {ticker_symbol}의 {period_date} 수익 데이터가 없습니다. 건너뜁니다.")
                    continue
                
                # 재무제표 레코드 생성 (yfinance에서 가져온 지표들 사용)
                financial_statement = {
                    'stock_code': ticker_symbol,
                    'report_period': period_date,
                    'report_type': period_type,
                    'revenue': safe_int(revenue),
                    'operating_income': safe_int(operating_income),
                    'net_income': safe_int(net_income),
                    'assets': safe_int(assets),
                    'liabilities': safe_int(liabilities),
                    'equity': safe_int(equity),
                    **financial_metrics  # yfinance에서 가져온 이미 계산된 지표들
                }
                
                result.append(financial_statement)
                print(f"[INFO] {ticker_symbol}의 {period_date} {period_type} 포괄적 재무제표 처리 완료")
                
            except Exception as e:
                print(f"[ERROR] {ticker_symbol}의 {period_date} 기간 재무 데이터 처리 중 오류 발생: {e}")
                continue
    
    return result

def save_market_indicators(ticker_symbol, info_data, history_data):
    """
    market_indicators 테이블에 시장 지표 저장
    """
    session = SessionLocal()
    try:
        print(f"[DEBUG] {ticker_symbol}의 시장 지표 저장 시작")
        
        # history_data 체크
        if history_data is None or history_data.empty:
            print(f"[WARNING] {ticker_symbol}의 가격 히스토리 데이터가 없습니다.")
            return
        
        print(f"[DEBUG] {ticker_symbol}의 히스토리 데이터 길이: {len(history_data)}")
        
        # 최근 데이터 가져오기
        latest_data = history_data.iloc[-1]
        today = date.today()
        
        print(f"[DEBUG] {ticker_symbol}의 최근 데이터: Close={latest_data.get('Close', 'N/A')}")
        print(f"[DEBUG] {ticker_symbol}의 info 데이터 주요 키들: {list(info_data.keys())[:10]}")
        
        # 날짜 처리 개선
        dividend_date = None
        ex_dividend_date = None
        
        if info_data.get('dividendDate'):
            try:
                # Unix timestamp를 date로 변환
                dividend_date = pd.to_datetime(info_data.get('dividendDate'), unit='s').date()
            except:
                dividend_date = None
                
        if info_data.get('exDividendDate'):
            try:
                # Unix timestamp를 date로 변환
                ex_dividend_date = pd.to_datetime(info_data.get('exDividendDate'), unit='s').date()
            except:
                ex_dividend_date = None
        
        # 시장 지표 데이터 구성
        market_data = {
            'stock_code': ticker_symbol,
            'date': today,
            'market_cap': safe_int(info_data.get('marketCap')),
            'per': safe_float(info_data.get('trailingPE')),
            'pbr': safe_float(info_data.get('priceToBook')),
            'eps': safe_float(info_data.get('trailingEps')),
            'bps': safe_float(info_data.get('bookValue')),
            'dividend_yield': safe_float(info_data.get('dividendYield')),
            'close_price': safe_float(latest_data.get('Close')),
            'market': info_data.get('market', 'us'),
            'exchange': info_data.get('exchange', 'NASDAQ'),
            'currency': info_data.get('currency', 'USD'),
            'previous_close': safe_float(info_data.get('previousClose')),
            'open': safe_float(latest_data.get('Open')),
            'current_price': safe_float(info_data.get('currentPrice', latest_data.get('Close'))),
            'day_low': safe_float(latest_data.get('Low')),
            'day_high': safe_float(latest_data.get('High')),
            'volume': safe_int(latest_data.get('Volume')),
            'average_volume': safe_int(info_data.get('averageVolume')),
            'pe_ratio_trailing': safe_float(info_data.get('trailingPE')),
            'pe_ratio_forward': safe_float(info_data.get('forwardPE')),
            'eps_forward': safe_float(info_data.get('forwardEps')),
            'eps_current_year': safe_float(info_data.get('trailingEps')),
            'price_eps_current_year': safe_float(info_data.get('priceEpsCurrentYear')),
            'beta': safe_float(info_data.get('beta')),
            'dividend_rate': safe_float(info_data.get('dividendRate')),
            'dividend_date': dividend_date,
            'ex_dividend_date': ex_dividend_date,
            'payout_ratio': safe_float(info_data.get('payoutRatio')),
            'book_value': safe_float(info_data.get('bookValue')),
            'fifty_two_week_low': safe_float(info_data.get('fiftyTwoWeekLow')),
            'fifty_two_week_high': safe_float(info_data.get('fiftyTwoWeekHigh')),
            'fifty_two_week_change_percent': safe_float(info_data.get('52WeekChange'))
        }
        
        print(f"[DEBUG] {ticker_symbol}의 시장 데이터 구성 완료. close_price: {market_data['close_price']}")
        
        # 기존 데이터 확인 (stock_code만으로)
        check_query = text("""
            SELECT id FROM market_indicators 
            WHERE stock_code = :stock_code
        """)
        result = session.execute(check_query, {
            'stock_code': ticker_symbol
        }).fetchone()
        
        if result:
            print(f"[DEBUG] {ticker_symbol}의 기존 시장 지표 데이터 발견, 업데이트 진행")
            # 업데이트
            update_query = text("""
                UPDATE market_indicators 
                SET market_cap = :market_cap, per = :per, pbr = :pbr, eps = :eps, bps = :bps,
                    dividend_yield = :dividend_yield, close_price = :close_price, market = :market,
                    exchange = :exchange, currency = :currency, previous_close = :previous_close,
                    open = :open, current_price = :current_price, day_low = :day_low, day_high = :day_high,
                    volume = :volume, average_volume = :average_volume, pe_ratio_trailing = :pe_ratio_trailing,
                    pe_ratio_forward = :pe_ratio_forward, eps_forward = :eps_forward, eps_current_year = :eps_current_year,
                    price_eps_current_year = :price_eps_current_year, beta = :beta, dividend_rate = :dividend_rate,
                    dividend_date = :dividend_date, ex_dividend_date = :ex_dividend_date, payout_ratio = :payout_ratio,
                    book_value = :book_value, fifty_two_week_low = :fifty_two_week_low, fifty_two_week_high = :fifty_two_week_high,
                    fifty_two_week_change_percent = :fifty_two_week_change_percent, date = :date, created_at = NOW()
                WHERE stock_code = :stock_code
            """)
            session.execute(update_query, market_data)
            print(f"[INFO] {ticker_symbol}의 시장 지표 업데이트 완료")
        else:
            print(f"[DEBUG] {ticker_symbol}의 새로운 시장 지표 데이터 삽입 진행")
            # 삽입
            insert_query = text("""
                INSERT INTO market_indicators 
                (stock_code, date, market_cap, per, pbr, eps, bps, dividend_yield, close_price, 
                 market, exchange, currency, previous_close, open, current_price, day_low, day_high,
                 volume, average_volume, pe_ratio_trailing, pe_ratio_forward, eps_forward, eps_current_year,
                 price_eps_current_year, beta, dividend_rate, dividend_date, ex_dividend_date, payout_ratio,
                 book_value, fifty_two_week_low, fifty_two_week_high, fifty_two_week_change_percent, created_at)
                VALUES 
                (:stock_code, :date, :market_cap, :per, :pbr, :eps, :bps, :dividend_yield, :close_price,
                 :market, :exchange, :currency, :previous_close, :open, :current_price, :day_low, :day_high,
                 :volume, :average_volume, :pe_ratio_trailing, :pe_ratio_forward, :eps_forward, :eps_current_year,
                 :price_eps_current_year, :beta, :dividend_rate, :dividend_date, :ex_dividend_date, :payout_ratio,
                 :book_value, :fifty_two_week_low, :fifty_two_week_high, :fifty_two_week_change_percent, NOW())
            """)
            session.execute(insert_query, market_data)
            print(f"[INFO] {ticker_symbol}의 시장 지표 추가 완료")
        
        session.commit()
        print(f"[DEBUG] {ticker_symbol}의 시장 지표 저장 성공적으로 커밋됨")
        
    except Exception as e:
        session.rollback()
        print(f"[ERROR] {ticker_symbol}의 시장 지표 저장 중 오류 발생: {e}")
        print(f"[ERROR] 상세 오류: {str(e)}")
        import traceback
        print(f"[ERROR] 트레이스백: {traceback.format_exc()}")
    finally:
        session.close()

def save_comprehensive_financial_data(financial_statements):
    """
    포괄적인 재무제표 데이터를 데이터베이스에 저장
    """
    session = SessionLocal()
    try:
        for statement in financial_statements:
            # 기존 레코드 확인
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
                    SET revenue = :revenue, operating_income = :operating_income, net_income = :net_income,
                        assets = :assets, liabilities = :liabilities, equity = :equity,
                        gross_profits = :gross_profits, ebitda = :ebitda, operating_cashflow = :operating_cashflow,
                        free_cashflow = :free_cashflow, revenue_per_share = :revenue_per_share,
                        gross_margins = :gross_margins, ebitda_margins = :ebitda_margins, operating_margins = :operating_margins,
                        return_on_assets = :return_on_assets, return_on_equity = :return_on_equity,
                        debt_to_equity = :debt_to_equity, quick_ratio = :quick_ratio, current_ratio = :current_ratio,
                        earnings_growth = :earnings_growth, revenue_growth = :revenue_growth,
                        enterprise_value = :enterprise_value, enterprise_to_revenue = :enterprise_to_revenue,
                        enterprise_to_ebitda = :enterprise_to_ebitda
                    WHERE stock_code = :stock_code AND report_period = :report_period AND report_type = :report_type
                """)
                
                session.execute(update_query, statement)
                print(f"[INFO] {statement['stock_code']}의 포괄적 재무제표 업데이트 완료 ({statement['report_period']}, {statement['report_type']})")
            else:
                # 새 레코드 삽입
                insert_query = text("""
                    INSERT INTO financial_statements 
                    (stock_code, report_period, report_type, revenue, operating_income, net_income, assets, liabilities, equity,
                     gross_profits, ebitda, operating_cashflow, free_cashflow, revenue_per_share,
                     gross_margins, ebitda_margins, operating_margins, return_on_assets, return_on_equity,
                     debt_to_equity, quick_ratio, current_ratio, earnings_growth, revenue_growth,
                     enterprise_value, enterprise_to_revenue, enterprise_to_ebitda)
                    VALUES 
                    (:stock_code, :report_period, :report_type, :revenue, :operating_income, :net_income, :assets, :liabilities, :equity,
                     :gross_profits, :ebitda, :operating_cashflow, :free_cashflow, :revenue_per_share,
                     :gross_margins, :ebitda_margins, :operating_margins, :return_on_assets, :return_on_equity,
                     :debt_to_equity, :quick_ratio, :current_ratio, :earnings_growth, :revenue_growth,
                     :enterprise_value, :enterprise_to_revenue, :enterprise_to_ebitda)
                """)
                
                session.execute(insert_query, statement)
                print(f"[INFO] {statement['stock_code']}의 포괄적 재무제표 추가 완료 ({statement['report_period']}, {statement['report_type']})")
        
        session.commit()
        print("[INFO] 포괄적 재무 데이터가 성공적으로 데이터베이스에 저장되었습니다.")
    except Exception as e:
        session.rollback()
        print(f"[ERROR] 포괄적 재무 데이터를 데이터베이스에 저장하는 중 오류 발생: {e}")
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
    """포괄적인 재무 데이터를 가져오고 처리하는 메인 함수"""
    # S&P 500 티커 가져오기
    stock_tickers = get_sp500_tickers()
    
    if not stock_tickers:
        print("[WARNING] CSV 파일에서 티커를 찾을 수 없습니다.")
        return
    
    print(f"[INFO] 처리할 주식 티커 {len(stock_tickers)}개를 찾았습니다.")
    
    # 모든 주식 티커에 대해 처리
    for ticker in stock_tickers:
        try:
            # 포괄적인 재무 데이터 가져오기
            financial_data = get_comprehensive_financial_data(ticker)
            
            if not financial_data:
                print(f"[WARNING] {ticker}에 대한 재무 데이터를 찾을 수 없습니다.")
                continue
            
            # 1. 주식 기본 정보 저장
            if financial_data.get('info'):
                save_stock_info(ticker, financial_data['info'])
            
            # 2. 포괄적인 재무제표 데이터 처리 및 저장
            financial_statements = process_comprehensive_financial_data(ticker, financial_data)
            if financial_statements:
                save_comprehensive_financial_data(financial_statements)
            
            # 3. 시장 지표 데이터 저장
            if financial_data.get('info') and not financial_data.get('history', pd.DataFrame()).empty:
                save_market_indicators(ticker, financial_data['info'], financial_data['history'])
            
            print(f"[INFO] {ticker}의 모든 데이터 처리가 성공적으로 완료되었습니다.")
                
            # 다음 티커 처리 전 랜덤한 시간(3-6초) 대기하여 API 제한 방지
            wait_time = 3 + random.random() * 3
            print(f"[INFO] 다음 티커 처리 전 {wait_time:.2f}초 대기 중...")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"[ERROR] {ticker} 처리 중 오류 발생: {e}")
            # 오류 발생 시 좀 더 오래 대기
            time.sleep(5)

if __name__ == "__main__":
    print("[INFO] 포괄적인 재무 데이터 수집을 시작합니다...")
    main()
    print("[INFO] 포괄적인 재무 데이터 수집이 완료되었습니다.") 