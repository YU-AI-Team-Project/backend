import pandas as pd
import yfinance as yf
from datetime import datetime
from sqlalchemy.sql import text

def fetch_and_store(ticker, engine, logging):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1d")

        if hist.empty:
            logging.warning(f"{ticker}: 가격 데이터 없음")
            return

        close_price = hist['Close'].iloc[-1]
        date = hist.index[-1].date()
        volume = hist['Volume'].iloc[-1]

        row = {
            'stock_code': ticker,
            'date': date,
            'market_cap': info.get('marketCap'),
            'per': info.get('trailingPE'),
            'pbr': info.get('priceToBook'),
            'eps': info.get('trailingEps'),
            'bps': info.get('bookValue'),
            'dividend_yield': info.get('dividendYield'),
            'close_price': close_price,
            'created_at': datetime.now()
        }

        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM market_indicators WHERE stock_code = :code AND date = :date"),
                {"code": ticker, "date": date}
            )
            count = result.scalar()

            df = pd.DataFrame([row])
            if count == 0:
                df.to_sql("market_indicators", con=engine, if_exists="append", index=False)
                logging.info(f"{ticker}: {date} 신규 데이터 추가")
            else:
                conn.execute(
                    text("""
                        UPDATE market_indicators
                        SET market_cap = :market_cap, per = :per, pbr = :pbr,
                            eps = :eps, bps = :bps, dividend_yield = :dividend_yield,
                            close_price = :close_price, created_at = :created_at
                        WHERE stock_code = :stock_code AND date = :date
                    """),
                    row
                )
                logging.info(f"{ticker}: {date} 기존 데이터 갱신")
    except Exception as e:
        logging.error(f"{ticker}: 수집 실패 - {e}")