"""
fetch_news_slice.py
Developer 플랜(100 결과 제한) 대응: 하루 단위로 잘라 반복 수집
"""
import os, requests, pandas as pd, time
from datetime import datetime, timedelta

KEY   = os.getenv("NEWSAPI_KEY")
BASE  = "https://newsapi.org/v2/everything"
START = datetime(2025, 5, 12)            # 수집 시작 (UTC 00:00)
END   = datetime(2025, 5, 15)            # 수집 끝   (UTC 00:00 미포함)

def fetch_day(day: datetime, query: str) -> pd.DataFrame:
    params = {
        "q"       : query,
        "from"    : day.date().isoformat(),
        "to"      : (day + timedelta(days=1)).date().isoformat(),
        "page"    : 1,          # **절대 2 이상 주지 않음**
        "pageSize": 100,        # 0~100 사이
        "language": "en",
        "sortBy"  : "publishedAt",
        "apiKey"  : KEY,
    }
    r = requests.get(BASE, params=params, timeout=10)
    if r.status_code == 426:
        raise RuntimeError("100개 초과 요청 → 426 Upgrade Required (무료 키)")
    r.raise_for_status()
    return pd.json_normalize(r.json()["articles"])

all_rows = []
cur = START
while cur < END:
    df = fetch_day(cur, "AAPL OR Apple")
    all_rows.append(df)
    # 일일 100 request 한도 안전 장치
    time.sleep(1)
    cur += timedelta(days=1)

final = pd.concat(all_rows, ignore_index=True)
final.to_csv("aapl_news_20250512_14.csv", index=False)
print(f"완료: {len(final):,}건 저장")


