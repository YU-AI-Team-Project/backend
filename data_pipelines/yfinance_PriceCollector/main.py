from db_config import get_db_engine
#from logger.logger import setup_logger
from collector.fetcher import fetch_and_store

if __name__ == "__main__":
    #logging = setup_logger()
    engine = get_db_engine()
    print("실행중")

    tickers = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN']

    #logging.info("시세 수집기 실행 시작")

    # 스케줄러 실행
    #start_scheduler(tickers, fetch_and_store, engine, logging)

    # 수동 실행 (테스트용, 스케쥴 기다리지 않고 바로 데이터를 수집)
    for ticker in tickers:
        fetch_and_store(ticker, engine)
