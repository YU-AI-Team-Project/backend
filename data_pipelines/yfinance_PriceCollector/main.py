from db_config import get_db_engine
from collector.fetcher import fetch_and_store
import pandas as pd
import os
import sys

if __name__ == "__main__":
    #logging = setup_logger()
    engine = get_db_engine()
    print("실행중")
    
    # S&P 500 티커 파일 경로
    ticker_file = 'sp500_tickers.csv'
    
    # CSV 파일이 존재하는지 확인
    if not os.path.exists(ticker_file):
        print(f"파일을 찾을 수 없습니다: {ticker_file}")
        exit(1)
    
    try:
        # CSV 파일 읽기 - S&P 500 티커는 헤더가 없는 단일 컬럼 파일
        tickers = pd.read_csv(ticker_file, header=None)[0].tolist()
        
        print(f"총 {len(tickers)}개 S&P 500 종목 처리 시작")
        
        # 종목 데이터 수집
        for i, ticker in enumerate(tickers):

            # 진행 상황 표시
            if (i+1) % 10 == 0:
                print(f"진행 중: {i+1}/{len(tickers)} ({ticker})")
                
            try:
                fetch_and_store(ticker, engine)
            except Exception as e:
                print(f"종목 {ticker} 처리 중 오류 발생: {str(e)}")
        
        print("모든 S&P 500 종목 처리 완료")
    
    except KeyboardInterrupt:
        print("\n프로그램이 사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"오류 발생: {str(e)}")
