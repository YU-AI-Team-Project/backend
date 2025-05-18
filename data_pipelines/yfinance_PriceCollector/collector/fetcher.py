import pandas as pd
import yfinance as yf
from datetime import datetime
from sqlalchemy.sql import text
from time import sleep

def fetch_and_store(ticker, engine):
    try:
        sleep(1.0)
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1d")

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

        print(info.get('longName', 'N/A'))

        print(row)

        print("🔌 연결 시도 중...")
        with engine.begin() as conn:
            print("✅ 연결 성공")

            exists = conn.execute(
                text("SELECT 1 FROM stocks WHERE code = :code"),
                {"code": ticker}
            ).fetchone()

            if not exists:
                conn.execute(
                    text("INSERT INTO stocks (code, company_name) VALUES (:code, :company_name)"),
                    {"code": ticker, "company_name": info.get('longName', 'N/A')}
                )

            result = conn.execute(
                text("SELECT COUNT(*) FROM market_indicators WHERE stock_code = :code AND date = :date"),
                {"code": ticker, "date": date}
            )
            count = result.scalar()

            df = pd.DataFrame([row])

            if count == 0:
                df.to_sql("market_indicators", con=engine, if_exists="append", index=False)
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
            print(f"{ticker}: 수집 완료")
            
    except Exception as e:
        print(f"{ticker}: 수집 실패 - {e}")