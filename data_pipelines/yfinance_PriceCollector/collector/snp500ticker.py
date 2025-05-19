import pandas as pd

# 위키피디아의 S&P 500 구성 종목 목록 페이지
url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'

# 표 읽기
tables = pd.read_html(url)
df = tables[0]  # 첫 번째 테이블이 S&P 500 목록

# 티커만 추출
tickers = df['Symbol'].tolist()

# 일부 티커는 `.`이 포함되므로, yfinance 형식으로 변환
tickers = [ticker.replace('.', '-') for ticker in tickers]

# 확인
print(tickers[:10])  # 상위 10개 출력

if __name__ == "__main__":
    print(tickers)
    # CSV 저장
    pd.Series(tickers).to_csv("sp500_tickers.csv", index=False, header=False)

