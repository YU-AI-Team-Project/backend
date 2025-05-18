import time, requests, pandas as pd
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, parse_qs, unquote
import random
from urllib.parse import urljoin
import requests
import json, pathlib
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

# ──────────────── 파라미터 ──────────────────────
START_DATE = "2025-01-30"
END_DATE = "2025-05-17"
BASE = "https://n.news.naver.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

#------------------------------헬퍼 함수------------------------------
def daterange(start_date: str, end_date: str):
    d0 = datetime.fromisoformat(start_date)
    d1 = datetime.fromisoformat(end_date)
    delta = timedelta(days=1)
    while d0 <= d1:
        yield d0.strftime("%Y-%m-%d")
        d0 += delta

def news_read_to_mnews(url: str) -> str:
    """
    '/news/news_read.naver?article_id=0001209610&office_id=215&…'
        → 'https://n.news.naver.com/mnews/article/215/0001209610'
    """
    if "/news/news_read" not in url:
        return url                          # 대상이 아니면 그대로

    qs  = parse_qs(urlparse(url).query)     # 쿼리 → dict
    oid = qs.get("office_id", [""])[0]
    aid = qs.get("article_id", [""])[0]
    return f"https://n.news.naver.com/mnews/article/{oid}/{aid}" if oid and aid else url
#------------------------------헬퍼 함수------------------------------

#------------------------------메인 로직------------------------------
all_rows = []

for date in daterange(START_DATE, END_DATE):
    time.sleep(random.uniform(1.5, 3.0))
    file_name = f"naverfinance_mainnews_{date}.csv"
    print(f"📄 {file_name} 수집 시작")

    first_url = f"https://finance.naver.com/news/mainnews.naver?date={date}"
    first_resp = requests.get(first_url, headers=HEADERS, timeout=10)
    soup_first = BeautifulSoup(first_resp.text, "lxml")

    a = soup_first.select_one("td.pgRR a[href]")
    qs = parse_qs(urlparse(a["href"]).query)
    max_page = int(qs.get("page", [1])[0])

    print(f"최대 페이지: {max_page}")

    articles = []

    for page_no in range(1, max_page + 1):
        time.sleep(random.uniform(1.5, 3.0))
        url = f"https://finance.naver.com/news/mainnews.naver?date={date}&page={page_no}"
        response = requests.get(url, headers=HEADERS, timeout = 10)
        if response.status_code != 200:
            print(f"❌ 요청 실패: {url}")
            continue
        soup = BeautifulSoup(response.text, "lxml")
        print(f"\n🔄 [목록] page {page_no} 요청 → {url}")

        for li in soup.select("div.mainNewsList li.block1"):   # 카드 전부 순회
            title_a = li.select_one("dd.articleSubject > a[href]")
            press   = li.select_one("dd.articleSummary span.press")
            wdate   = li.select_one("dd.articleSummary span.wdate")
            if not title_a:
                continue

            url = news_read_to_mnews(title_a["href"])
            articles.append({
                "title": title_a.get_text(strip=True),
                "url":   url,         # 이미 https://n.news.naver.com/…
                "press": press.get_text(strip=True) if press else "",
                "time":  wdate.get_text(strip=True) if wdate else ""
            })
            
        print(f"📄 page {page_no} 수집 완료 (기사 {len(articles)}개)")

    rows = []
    for idx, art in enumerate(articles, start=1):
        time.sleep(random.uniform(1.5, 3.0))        # 딜레이

        res = requests.get(art["url"], headers=HEADERS, timeout=10)
        if res.status_code != 200:
            print("❌ 요청 실패", art["url"])
            continue

        page = BeautifulSoup(res.text, "html.parser")
        body = page.select_one("#dic_area, .go_trans._article_content")
        art["content"] = body.get_text(strip=True) if body else ""
        rows.append(art)

        print(f"✅ page {idx} 본문 저장")
    
        # 💾 STEP 3: 저장
    df = pd.DataFrame(rows)
    df.to_csv(file_name, index=False, encoding="utf-8-sig")
    print(f"\n✅ CSV 저장 완료: {file_name}")

        # 💾 STEP 4: JSONL
    path = pathlib.Path(file_name.replace(".csv", ".jsonl"))
    with path.open("w", encoding="utf-8") as f:
        for art in rows:
            f.write(json.dumps(art, ensure_ascii=False) + "\n")
    print(f"\n✅ JSONL 저장 완료: {path}")

    all_rows.extend(rows)